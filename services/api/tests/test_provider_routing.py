"""Routing between providers: gemini -> openrouter -> groq -> cache -> demo.

Every path runs the real `AILessonGenerator`, so the draft is validated, grounded and assembled the
same way regardless of which provider answered. No network is used: providers are fakes.
"""

import asyncio
import logging
import time
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from app.ai import gemini_provider, groq_provider, openrouter_provider
from app.ai.ai_lesson_generator import AILessonGenerator
from app.ai.drafts import DraftQuizQuestion, DraftSection, DraftSourceReference, LessonDraft
from app.ai.gemini_provider import GeminiProvider
from app.ai.groq_provider import GroqProvider
from app.ai.lesson_cache import FileLessonCache, NullLessonCache, document_cache_key
from app.ai.lesson_generator import LessonGenerationRequest, LessonGenerator
from app.ai.mock_lesson_generator import MockLessonGenerator
from app.ai.openrouter_provider import OpenRouterProvider
from app.ai.provider import AIInvalidResponseError, AIProviderError, AIRateLimitError
from app.ai.routing import RoutingLessonGenerator
from app.core.config import Settings
from app.models.content import ExtractedDocument, ExtractedPage
from app.schemas.lesson import Lesson, Source
from app.services.chunking import chunk_document
from tests.fakes import FakeProvider

PAGES = [
    "Photosynthesis is the process plants use to make glucose from light, water and carbon "
    "dioxide.",
    "Chlorophyll absorbs red and blue light and reflects green light, so leaves look green.",
]
QUOTE = "plants use to make glucose"


def _request(lesson_id: str = "lesson-1") -> LessonGenerationRequest:
    pages = [ExtractedPage(page_number=n, text=text) for n, text in enumerate(PAGES, start=1)]
    document = ExtractedDocument(pages=pages, total_pages=len(pages))
    return LessonGenerationRequest(
        lesson_id=lesson_id,
        source=Source(source_type="pdf", title="notes", filename="notes.pdf"),
        document=document,
        chunks=chunk_document(document, max_chars=10_000),
    )


def _draft() -> LessonDraft:
    return LessonDraft(
        title="Photosynthesis",
        overview="How plants make glucose.",
        sections=[
            DraftSection(
                type="concept",
                title="Photosynthesis",
                term="Photosynthesis",
                definition="How plants make glucose from light.",
                source_references=[DraftSourceReference(page_number=1, excerpt=QUOTE)],
            )
        ],
        quiz=[
            DraftQuizQuestion(
                prompt=f"Question {number}?",
                options=["Glucose", "Salt", "Iron"],
                correct_option_index=0,
                explanation="Page 1 says plants make glucose.",
                section_numbers=[1],
            )
            for number in (1, 2, 3)
        ],
    )


def _generator(*responses: object, name: str = "fake") -> AILessonGenerator:
    provider = FakeProvider(list(responses))
    provider.name = name
    return AILessonGenerator(provider, single_pass_max_chars=10_000, max_chunks=8)


# Distinguishes "caller said nothing" from an explicit `demo=None`, which turns demo content off.
_UNSET = object()


def _router(
    live: list[tuple[str, LessonGenerator]],
    *,
    cache: object | None = None,
    demo: LessonGenerator | object | None = _UNSET,
) -> RoutingLessonGenerator:
    return RoutingLessonGenerator(
        live=live,  # type: ignore[arg-type]
        cache=cache or NullLessonCache(),  # type: ignore[arg-type]
        demo=MockLessonGenerator() if demo is _UNSET else demo,  # type: ignore[arg-type]
    )


def _assert_valid_lesson(lesson: Lesson, request_id: str = "lesson-1") -> None:
    assert lesson.id == request_id
    assert Lesson.model_validate(lesson.model_dump(mode="json", exclude_none=True)) == lesson


def test_primary_provider_success_is_reported_as_live() -> None:
    router = _router([("gemini", _generator(_draft(), name="gemini"))])

    result = asyncio.run(router.generate(_request()))

    assert (result.provider, result.generation_status) == ("gemini", "live")
    assert result.warnings == []
    _assert_valid_lesson(result.lesson)


@pytest.mark.parametrize(
    "failure",
    [AIRateLimitError("429"), AIProviderError("HTTP 503"), AIInvalidResponseError("bad json")],
    ids=["rate-limited", "server-error", "invalid-output"],
)
def test_recoverable_primary_failure_falls_back_to_openrouter(failure: Exception) -> None:
    router = _router(
        [
            ("gemini", _generator(failure, name="gemini")),
            ("openrouter", _generator(_draft(), name="openrouter")),
        ]
    )

    result = asyncio.run(router.generate(_request()))

    assert (result.provider, result.generation_status) == ("openrouter", "fallback")
    assert "gemini" in result.warnings[0]
    assert type(failure).__name__ in result.warnings[0]
    assert "not by the primary provider" in result.warnings[0]
    _assert_valid_lesson(result.lesson)


def test_second_fallback_is_used_when_openrouter_also_fails() -> None:
    router = _router(
        [
            ("gemini", _generator(AIRateLimitError("429"), name="gemini")),
            ("openrouter", _generator(AIProviderError("HTTP 500"), name="openrouter")),
            ("groq", _generator(_draft(), name="groq")),
        ]
    )

    result = asyncio.run(router.generate(_request()))

    assert (result.provider, result.generation_status) == ("groq", "fallback")
    assert "gemini" in result.warnings[0] and "openrouter" in result.warnings[0]
    _assert_valid_lesson(result.lesson)


def test_successful_generation_is_cached_for_the_same_document(tmp_path: Path) -> None:
    cache = FileLessonCache(tmp_path)
    router = _router([("gemini", _generator(_draft(), name="gemini"))], cache=cache)

    asyncio.run(router.generate(_request()))

    assert cache.get(document_cache_key(_request().document)) is not None


def test_cache_is_used_when_every_provider_fails(tmp_path: Path) -> None:
    cache = FileLessonCache(tmp_path)
    stored = asyncio.run(
        _router([("gemini", _generator(_draft(), name="gemini"))], cache=cache).generate(_request())
    )
    failing = _router(
        [
            ("gemini", _generator(AIRateLimitError("429"), name="gemini")),
            ("openrouter", _generator(AIProviderError("HTTP 500"), name="openrouter")),
        ],
        cache=cache,
    )

    result = asyncio.run(failing.generate(_request("lesson-2")))

    assert (result.provider, result.generation_status) == ("cache", "cached")
    assert result.lesson.title == stored.lesson.title
    assert "served from an earlier successful generation" in result.warnings[0]
    _assert_valid_lesson(result.lesson, "lesson-2")


def test_demo_is_used_when_every_provider_fails_and_nothing_is_cached() -> None:
    router = _router([("gemini", _generator(AIRateLimitError("429"), name="gemini"))])

    result = asyncio.run(router.generate(_request()))

    assert (result.provider, result.generation_status) == ("demo", "demo")
    assert "does not describe the uploaded PDF" in result.warnings[0]
    _assert_valid_lesson(result.lesson)


def test_error_is_raised_when_demo_fallback_is_turned_off() -> None:
    router = _router([("gemini", _generator(AIRateLimitError("429"), name="gemini"))], demo=None)

    with pytest.raises(AIProviderError, match="No AI provider was available"):
        asyncio.run(router.generate(_request()))


def test_fallback_never_claims_to_come_from_the_primary_provider() -> None:
    router = _router(
        [
            ("gemini", _generator(AIRateLimitError("429"), name="gemini")),
            ("openrouter", _generator(_draft(), name="openrouter")),
        ]
    )

    result = asyncio.run(router.generate(_request()))

    assert result.provider != "gemini"
    assert result.generation_status != "live"


def test_rate_limited_gemini_fails_over_to_openrouter_across_real_clients(tmp_path: Path) -> None:
    """Failover through both real provider clients, over mocked transports and no network.

    Unlike the tests above, which raise our own exceptions directly, this drives the actual
    Gemini SDK and the OpenRouter HTTP client, proving the router receives a real 429 classified
    as `AIRateLimitError` and that no provider retries before the router moves on.
    """
    gemini_requests: list[httpx.Request] = []
    openrouter_requests: list[httpx.Request] = []

    def gemini_handler(request: httpx.Request) -> httpx.Response:
        gemini_requests.append(request)
        return httpx.Response(
            429, json={"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}}
        )

    def openrouter_handler(request: httpx.Request) -> httpx.Response:
        openrouter_requests.append(request)
        content = _draft().model_dump_json()
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    settings = Settings(
        _env_file=None,
        app_env="test",
        gemini_api_key=SecretStr("gemini-test-key"),
        openrouter_api_key=SecretStr("openrouter-test-key"),
        data_dir=tmp_path / "data",
    )
    providers = [
        (
            "gemini",
            GeminiProvider.from_settings(settings, transport=httpx.MockTransport(gemini_handler)),
        ),
        (
            "openrouter",
            OpenRouterProvider.from_settings(
                settings, transport=httpx.MockTransport(openrouter_handler)
            ),
        ),
    ]
    router = _router(
        [
            (name, AILessonGenerator(provider, single_pass_max_chars=10_000, max_chunks=8))
            for name, provider in providers
        ]
    )

    result = asyncio.run(router.generate(_request()))

    assert (result.provider, result.generation_status) == ("openrouter", "fallback")
    assert len(gemini_requests) == 1, "the Gemini SDK retried before the router could fail over"
    assert len(openrouter_requests) == 1
    assert "AIRateLimitError" in result.warnings[0]
    _assert_valid_lesson(result.lesson)


def test_routing_logs_never_contain_provider_secrets(caplog: pytest.LogCaptureFixture) -> None:
    # Not a real credential: a marker value this test asserts never reaches the logs.
    secret = "sk-super-secret-value-00000"  # noqa: S105
    router = _router(
        [
            ("gemini", _generator(AIRateLimitError(f"quota for {secret}"), name="gemini")),
            ("openrouter", _generator(_draft(), name="openrouter")),
        ]
    )

    with caplog.at_level(logging.DEBUG):
        result = asyncio.run(router.generate(_request()))

    assert secret not in caplog.text
    assert all(secret not in warning for warning in result.warnings)


# ---- Timeouts fail over the same way any other recoverable error does --------------------------


def _timeout_handler(request: httpx.Request) -> httpx.Response:
    """A mocked transport that raises the same exception a real timeout deadline would.

    Raising directly (rather than actually waiting out `REQUEST_TIMEOUT_SECONDS`) keeps these
    tests instantaneous while still proving the real classification path.
    """
    raise httpx.ReadTimeout("timed out", request=request)


def _success_handler(request: httpx.Request) -> httpx.Response:
    content = _draft().model_dump_json()
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_gemini_timeout_fails_over_to_openrouter_across_real_clients(tmp_path: Path) -> None:
    """A hung Gemini request must fail over exactly like a 429 does, over the real Gemini SDK."""
    gemini_requests: list[httpx.Request] = []
    openrouter_requests: list[httpx.Request] = []

    def gemini_handler(request: httpx.Request) -> httpx.Response:
        gemini_requests.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    def openrouter_handler(request: httpx.Request) -> httpx.Response:
        openrouter_requests.append(request)
        return _success_handler(request)

    settings = Settings(
        _env_file=None,
        app_env="test",
        gemini_api_key=SecretStr("gemini-test-key"),
        openrouter_api_key=SecretStr("openrouter-test-key"),
        data_dir=tmp_path / "data",
    )
    providers = [
        (
            "gemini",
            GeminiProvider.from_settings(settings, transport=httpx.MockTransport(gemini_handler)),
        ),
        (
            "openrouter",
            OpenRouterProvider.from_settings(
                settings, transport=httpx.MockTransport(openrouter_handler)
            ),
        ),
    ]
    router = _router(
        [
            (name, AILessonGenerator(provider, single_pass_max_chars=10_000, max_chunks=8))
            for name, provider in providers
        ]
    )

    result = asyncio.run(router.generate(_request()))

    assert (result.provider, result.generation_status) == ("openrouter", "fallback")
    assert len(gemini_requests) == 1, (
        "the Gemini SDK retried a timeout before the router failed over"
    )
    assert len(openrouter_requests) == 1
    assert "AIProviderError" in result.warnings[0]
    _assert_valid_lesson(result.lesson)


def test_openrouter_timeout_fails_over_to_groq_across_real_clients(tmp_path: Path) -> None:
    """Same proof one hop later: OpenRouter times out and Groq, the last live provider, answers."""
    openrouter_requests: list[httpx.Request] = []
    groq_requests: list[httpx.Request] = []

    def openrouter_handler(request: httpx.Request) -> httpx.Response:
        openrouter_requests.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    def groq_handler(request: httpx.Request) -> httpx.Response:
        groq_requests.append(request)
        return _success_handler(request)

    settings = Settings(
        _env_file=None,
        app_env="test",
        openrouter_api_key=SecretStr("openrouter-test-key"),
        groq_api_key=SecretStr("groq-test-key"),
        data_dir=tmp_path / "data",
    )
    providers = [
        (
            "openrouter",
            OpenRouterProvider.from_settings(
                settings, transport=httpx.MockTransport(openrouter_handler)
            ),
        ),
        ("groq", GroqProvider.from_settings(settings, transport=httpx.MockTransport(groq_handler))),
    ]
    router = _router(
        [
            (name, AILessonGenerator(provider, single_pass_max_chars=10_000, max_chunks=8))
            for name, provider in providers
        ]
    )

    result = asyncio.run(router.generate(_request()))

    assert (result.provider, result.generation_status) == ("groq", "fallback")
    assert len(openrouter_requests) == 1
    assert len(groq_requests) == 1
    assert "AIProviderError" in result.warnings[0]
    _assert_valid_lesson(result.lesson)


def _all_real_providers_timing_out(settings: Settings) -> list[tuple[str, LessonGenerator]]:
    providers = [
        (
            "gemini",
            GeminiProvider.from_settings(settings, transport=httpx.MockTransport(_timeout_handler)),
        ),
        (
            "openrouter",
            OpenRouterProvider.from_settings(
                settings, transport=httpx.MockTransport(_timeout_handler)
            ),
        ),
        (
            "groq",
            GroqProvider.from_settings(settings, transport=httpx.MockTransport(_timeout_handler)),
        ),
    ]
    return [
        (name, AILessonGenerator(provider, single_pass_max_chars=10_000, max_chunks=8))
        for name, provider in providers
    ]


def test_all_provider_timeouts_fall_through_to_cache(tmp_path: Path) -> None:
    """When every real, live provider hangs, a previously cached lesson is served instead."""
    cache = FileLessonCache(tmp_path)
    settings = Settings(
        _env_file=None,
        app_env="test",
        gemini_api_key=SecretStr("gemini-test-key"),
        openrouter_api_key=SecretStr("openrouter-test-key"),
        groq_api_key=SecretStr("groq-test-key"),
        data_dir=tmp_path / "data",
    )
    stored = asyncio.run(
        _router([("gemini", _generator(_draft(), name="gemini"))], cache=cache).generate(_request())
    )

    router = _router(_all_real_providers_timing_out(settings), cache=cache)

    result = asyncio.run(router.generate(_request("lesson-2")))

    assert (result.provider, result.generation_status) == ("cache", "cached")
    assert result.lesson.title == stored.lesson.title
    assert "served from an earlier successful generation" in result.warnings[0]
    _assert_valid_lesson(result.lesson, "lesson-2")


def test_all_provider_timeouts_fall_through_to_demo_when_nothing_is_cached(
    tmp_path: Path,
) -> None:
    """With no cached lesson either, deterministic demo content is served, not an error."""
    settings = Settings(
        _env_file=None,
        app_env="test",
        gemini_api_key=SecretStr("gemini-test-key"),
        openrouter_api_key=SecretStr("openrouter-test-key"),
        groq_api_key=SecretStr("groq-test-key"),
        data_dir=tmp_path / "data",
    )

    router = _router(_all_real_providers_timing_out(settings))

    result = asyncio.run(router.generate(_request()))

    assert (result.provider, result.generation_status) == ("demo", "demo")
    assert "does not describe the uploaded PDF" in result.warnings[0]
    _assert_valid_lesson(result.lesson)


def test_timeout_failures_do_not_leak_provider_secrets(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Real provider clients built with real-looking credentials must not leak them when a

    request times out, whether through logs or through the warning shown to the client.
    """
    secret = "sk-super-secret-value-00000"  # noqa: S105
    settings = Settings(
        _env_file=None,
        app_env="test",
        gemini_api_key=SecretStr(secret),
        openrouter_api_key=SecretStr("openrouter-test-key"),
        data_dir=tmp_path / "data",
    )
    providers = [
        (
            "gemini",
            GeminiProvider.from_settings(settings, transport=httpx.MockTransport(_timeout_handler)),
        ),
        (
            "openrouter",
            OpenRouterProvider.from_settings(
                settings, transport=httpx.MockTransport(_success_handler)
            ),
        ),
    ]
    router = _router(
        [
            (name, AILessonGenerator(provider, single_pass_max_chars=10_000, max_chunks=8))
            for name, provider in providers
        ]
    )

    with caplog.at_level(logging.DEBUG):
        result = asyncio.run(router.generate(_request()))

    assert secret not in caplog.text
    assert all(secret not in warning for warning in result.warnings)


# ---- Hard wall-clock deadlines fail over the same way ------------------------------------------
#
# These drive the real Gemini SDK and the real OpenRouter/Groq HTTP clients against transports that
# never answer. `MockTransport` ignores httpx's own timeouts, so only the application-level
# deadline can end these requests - which is the point: it proves the router keeps moving even when
# a provider hangs in the way a per-read timeout cannot catch.

_HANG_DEADLINE = 0.25  # short so the suite stays fast; the provider modules lock the real values


async def _hang_forever(request: httpx.Request) -> httpx.Response:
    await asyncio.sleep(3600)
    raise AssertionError("unreachable: the deadline should have fired")


def _shorten_deadlines(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in (gemini_provider, openrouter_provider, groq_provider):
        monkeypatch.setattr(module, "REQUEST_TIMEOUT_SECONDS", _HANG_DEADLINE)


def _all_keys(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        gemini_api_key=SecretStr("gemini-test-key"),
        openrouter_api_key=SecretStr("openrouter-test-key"),
        groq_api_key=SecretStr("groq-test-key"),
        data_dir=tmp_path / "data",
    )


def _wrap(name: str, provider: object) -> tuple[str, LessonGenerator]:
    generator = AILessonGenerator(provider, single_pass_max_chars=10_000, max_chunks=8)  # type: ignore[arg-type]
    return (name, generator)


def _hanging(provider_class: object, settings: Settings) -> object:
    return provider_class.from_settings(  # type: ignore[attr-defined]
        settings, transport=httpx.MockTransport(_hang_forever)
    )


def _all_hanging(settings: Settings) -> list[tuple[str, LessonGenerator]]:
    return [
        _wrap("gemini", _hanging(GeminiProvider, settings)),
        _wrap("openrouter", _hanging(OpenRouterProvider, settings)),
        _wrap("groq", _hanging(GroqProvider, settings)),
    ]


def test_gemini_hard_deadline_fails_over_to_openrouter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _shorten_deadlines(monkeypatch)
    settings = _all_keys(tmp_path)
    openrouter_requests: list[httpx.Request] = []

    def openrouter_handler(request: httpx.Request) -> httpx.Response:
        openrouter_requests.append(request)
        return _success_handler(request)

    router = _router(
        [
            _wrap("gemini", _hanging(GeminiProvider, settings)),
            _wrap(
                "openrouter",
                OpenRouterProvider.from_settings(
                    settings, transport=httpx.MockTransport(openrouter_handler)
                ),
            ),
        ]
    )

    started = time.perf_counter()
    result = asyncio.run(router.generate(_request()))
    elapsed = time.perf_counter() - started

    assert (result.provider, result.generation_status) == ("openrouter", "fallback")
    assert len(openrouter_requests) == 1
    assert "AIProviderError" in result.warnings[0]
    assert elapsed < _HANG_DEADLINE * 6, "a hung Gemini request delayed failover"
    _assert_valid_lesson(result.lesson)


def test_openrouter_hard_deadline_fails_over_to_groq(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _shorten_deadlines(monkeypatch)
    settings = _all_keys(tmp_path)
    groq_requests: list[httpx.Request] = []

    def groq_handler(request: httpx.Request) -> httpx.Response:
        groq_requests.append(request)
        return _success_handler(request)

    router = _router(
        [
            _wrap("openrouter", _hanging(OpenRouterProvider, settings)),
            _wrap(
                "groq",
                GroqProvider.from_settings(settings, transport=httpx.MockTransport(groq_handler)),
            ),
        ]
    )

    started = time.perf_counter()
    result = asyncio.run(router.generate(_request()))
    elapsed = time.perf_counter() - started

    assert (result.provider, result.generation_status) == ("groq", "fallback")
    assert len(groq_requests) == 1
    assert "AIProviderError" in result.warnings[0]
    assert elapsed < _HANG_DEADLINE * 6
    _assert_valid_lesson(result.lesson)


def test_all_hard_deadlines_fall_through_to_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = FileLessonCache(tmp_path / "cache")
    stored = asyncio.run(
        _router([("gemini", _generator(_draft(), name="gemini"))], cache=cache).generate(_request())
    )
    _shorten_deadlines(monkeypatch)
    router = _router(_all_hanging(_all_keys(tmp_path)), cache=cache)

    started = time.perf_counter()
    result = asyncio.run(router.generate(_request("lesson-2")))
    elapsed = time.perf_counter() - started

    assert (result.provider, result.generation_status) == ("cache", "cached")
    assert result.lesson.title == stored.lesson.title
    assert "served from an earlier successful generation" in result.warnings[0]
    # Three hung providers, each bounded: the whole chain stays near three deadlines, not forever.
    assert elapsed < _HANG_DEADLINE * 8
    _assert_valid_lesson(result.lesson, "lesson-2")


def test_all_hard_deadlines_fall_through_to_demo_when_nothing_is_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _shorten_deadlines(monkeypatch)
    router = _router(_all_hanging(_all_keys(tmp_path)))

    result = asyncio.run(router.generate(_request()))

    assert (result.provider, result.generation_status) == ("demo", "demo")
    assert "does not describe the uploaded PDF" in result.warnings[0]
    _assert_valid_lesson(result.lesson)


def test_all_hard_deadlines_raise_when_demo_is_turned_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With demo off the router raises `AIProviderError`, which the API maps to a 503, not a 500."""
    _shorten_deadlines(monkeypatch)
    router = _router(_all_hanging(_all_keys(tmp_path)), demo=None)

    with pytest.raises(AIProviderError, match="No AI provider was available"):
        asyncio.run(router.generate(_request()))


def test_hard_deadline_failures_do_not_leak_provider_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "sk-super-secret-deadline-00000"  # noqa: S105
    _shorten_deadlines(monkeypatch)
    settings = Settings(
        _env_file=None,
        app_env="test",
        gemini_api_key=SecretStr(secret),
        openrouter_api_key=SecretStr(secret),
        groq_api_key=SecretStr(secret),
        data_dir=tmp_path / "data",
    )
    router = _router(_all_hanging(settings))

    with caplog.at_level(logging.DEBUG):
        result = asyncio.run(router.generate(_request()))

    assert secret not in caplog.text
    assert all(secret not in warning for warning in result.warnings)


def test_hard_deadline_leaves_no_pending_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every hung provider must unwind cleanly, leaving nothing running behind the router."""
    _shorten_deadlines(monkeypatch)
    router = _router(_all_hanging(_all_keys(tmp_path)))

    async def run() -> int:
        await router.generate(_request())
        return len(asyncio.all_tasks()) - 1

    assert asyncio.run(run()) == 0
