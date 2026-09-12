# API service (`services/api`)

FastAPI service that owns PDF ingestion, AI lesson generation, validation and the HTTP API.
Owner: Person 1 (AI / Backend). Setup steps: [docs/development/getting-started.md](../../docs/development/getting-started.md).
Design: [docs/architecture/overview.md](../../docs/architecture/overview.md).

```text
app/
  main.py            app factory: settings, AI mode, store and service wiring, middleware, routers
  core/              settings and limits, logging, request ids, upload size limit, error codes
  api/routes/        health.py, lessons.py (POST /api/v1/lessons/pdf, GET /api/v1/lessons/{id})
  schemas/           lesson.py (contract mirror), lessons_api.py (LessonRecord responses)
  models/content.py  ExtractedPage, ExtractedDocument, ContentChunk
  ingestion/         pdf.py (PyMuPDF text extraction), text_cleaning.py
  services/          uploads.py, chunking.py, pdf_lessons.py (orchestration), lesson_store.py
  ai/                provider.py, gemini_provider.py, factory.py, drafts.py, prompts/,
                     ai_lesson_generator.py, lesson_assembly.py, mock_lesson_generator.py
  utils/             safe id validation
tests/               pytest suite; `pytest -m live` runs the optional real Gemini checks
```

Common commands (run from `services/api` with the virtualenv active):

| Task | Command |
| --- | --- |
| Run the API | `uvicorn app.main:app --reload --port 8000` |
| Tests (no network, no API key) | `pytest` |
| Lint | `ruff check .` |
| Format | `ruff format .` |
| Real Gemini checks (uses free-tier quota) | `pytest -m live` |

## AI providers

Lesson generation tries Gemini, then OpenRouter, then Groq, then a cached lesson for the same
document, then fixed demo content. Every provider goes through the same validation and grounding
checks, and the response says which one answered (`metadata.provider` and
`metadata.generation_status`), so a fallback is never presented as a primary result. All three are
free tiers; a provider with no API key is skipped. See
[docs/architecture/overview.md](../../docs/architecture/overview.md) for the models, the routing
rules and every environment variable, and `.env.example` at the repository root for the variables
themselves.

PDF text extraction uses PyMuPDF, licensed under AGPL-3.0. It is imported only in
`app/ingestion/pdf.py`, so another extractor can replace it in one file.
