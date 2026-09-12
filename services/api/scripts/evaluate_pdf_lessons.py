"""Evaluate PDF -> lesson generation on local PDFs through the real API code path.

Each PDF is uploaded to an in-process instance of the API (configured from the repository `.env`),
fetched back through GET /api/v1/lessons/{id}, and checked against the shared Lesson JSON Schema.
Results go to `<out>/summary.json` plus one `<name>.lesson.json` record per PDF for quality review.
Document text is never printed.

Usage, from services/api with the virtualenv active:
    python scripts/evaluate_pdf_lessons.py .data/eval/a.pdf .data/eval/b.pdf

With a provider configured each short PDF costs one AI request; longer PDFs cost one per chunk plus
one. The `provider` and `generation_status` fields report which service actually answered.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from app.core.config import CONTRACTS_DIR, get_settings
from app.main import create_app


def evaluate(client: TestClient, validator: Draft202012Validator, pdf: Path) -> dict[str, Any]:
    started = time.perf_counter()
    with pdf.open("rb") as handle:
        response = client.post(
            "/api/v1/lessons/pdf", files={"file": (pdf.name, handle, "application/pdf")}
        )
    wall_ms = round((time.perf_counter() - started) * 1000)
    if response.status_code != 201:
        return {
            "file": pdf.name,
            "status": response.status_code,
            "error": response.json().get("error"),
            "wall_ms": wall_ms,
        }

    created = response.json()
    fetched = client.get(f"/api/v1/lessons/{created['lesson_id']}")
    record = fetched.json()
    lesson, metadata = record["lesson"], record["metadata"]
    return {
        "file": pdf.name,
        "status": response.status_code,
        "lesson_id": record["lesson_id"],
        "generation_mode": metadata["generation_mode"],
        "model": metadata.get("model"),
        "page_count": metadata["page_count"],
        "character_count": metadata["character_count"],
        "chunk_count": metadata["chunk_count"],
        "ai_request_count": metadata["ai_request_count"],
        "timings": metadata["timings"],
        "wall_ms": wall_ms,
        "warnings": metadata["warnings"],
        "section_types": [section["type"] for section in lesson["sections"]],
        "quiz_count": len(lesson["quiz"]),
        "get_status": fetched.status_code,
        "get_matches_post": record == created,
        "contract_errors": [error.message for error in validator.iter_errors(lesson)][:5],
        "record": record,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("pdfs", nargs="+", type=Path, help="local PDF files to evaluate")
    parser.add_argument("--out", type=Path, default=Path(".data/eval/results"))
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=10.0,
        help="wait between PDFs to stay well inside free-tier request-per-minute limits",
    )
    args = parser.parse_args()

    settings = get_settings()
    args.out.mkdir(parents=True, exist_ok=True)
    schema = json.loads((CONTRACTS_DIR / "lesson.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    results: list[dict[str, Any]] = []
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        for position, pdf in enumerate(args.pdfs):
            if position:
                time.sleep(args.pause_seconds)
            result = evaluate(client, validator, pdf)
            record = result.pop("record", None)
            if record is not None:
                (args.out / f"{pdf.stem}.lesson.json").write_text(
                    json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            results.append(result)
            summary = {key: value for key, value in result.items() if key != "warnings"}
            print(json.dumps(summary, ensure_ascii=False))

    (args.out / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    total_requests = sum(result.get("ai_request_count", 0) for result in results)
    providers = sorted({str(result.get("provider", "n/a")) for result in results})
    print(f"Providers used: {', '.join(providers)}. AI requests used: {total_requests}.")
    passed = all(
        result["status"] == 201 and result["get_matches_post"] and not result["contract_errors"]
        for result in results
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
