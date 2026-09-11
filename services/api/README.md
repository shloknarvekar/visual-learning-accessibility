# API service (`services/api`)

FastAPI service that owns ingestion, AI lesson generation, validation and the HTTP API.
Owner: Person 1 (AI / Backend). Setup steps: [docs/development/getting-started.md](../../docs/development/getting-started.md).

```text
app/
  main.py          FastAPI app factory (CORS, middleware, error handlers, routers)
  core/            settings, logging, request middleware, error envelope
  api/             HTTP routes; versioned under /api/v1
  schemas/         public API models, including the Lesson contract mirror
  models/          internal data passed between pipeline stages
  ingestion/       stage 1: YouTube / PDF -> ExtractedDocument
  services/        non-AI logic: segmentation, lesson storage
  ai/              AIProvider interface, Gemini provider, mock fallback, prompts, generation stages
  utils/           small shared helpers
tests/             pytest suite (`pytest -m live` for the optional Gemini check)
```

Common commands (run from `services/api` with the virtualenv active):

| Task | Command |
| --- | --- |
| Run the API | `uvicorn app.main:app --reload --port 8000` |
| Tests | `pytest` |
| Lint | `ruff check .` |
| Format | `ruff format .` |
| Gemini connectivity check (uses free-tier quota) | `pytest -m live` |
