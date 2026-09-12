# Visual Learning Accessibility

An AI-powered platform that turns hearing-first educational content (YouTube lectures, PDFs) into
structured, **visual-first lessons** for Deaf and hard-of-hearing students.

The goal is not captions or transcripts. The system reorganises the same academic content into
concepts, processes, relationships, comparisons, diagrams and checkpoints, without simplifying the
substance away.

> **Status:** project foundation. The API, web app and shared contract are in place; ingestion and AI
> lesson generation are not implemented yet.

## Repository layout

```text
apps/web/              Next.js frontend (TypeScript, Tailwind CSS)
services/api/          FastAPI backend: ingestion, AI pipeline, HTTP API
packages/contracts/    Shared Lesson JSON Schema, generated TS types, example lesson
docs/
  architecture/        system design and data flow
  product/             problem, users, MVP scope
  development/         setup and team boundaries
scripts/verify.py      runs every check CI runs
.github/               CI workflow, PR template, CODEOWNERS
```

## Quick start

Prerequisites: Node.js 20.9+, Python 3.11+, Git. No API keys are needed to start.

```bash
# 1. Configuration (every value is optional; see "Zero-Cost Development")
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local

# 2. Backend -> http://localhost:8000/api/v1/health
cd services/api
python -m venv .venv
source .venv/bin/activate                   # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal, repository root) -> http://localhost:3000
npm install
npm run dev:web
```

Full instructions, including Windows specifics: [docs/development/getting-started.md](docs/development/getting-started.md).

## Zero-Cost Development

This prototype is built and run with a **$0 budget**. Nothing in this repository needs a paid plan,
a billing account, a payment method or credits.

### Services and cost

| What                                                                                                                           | Cost                                       | Required?        |
| ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ | ---------------- |
| Next.js, React, Tailwind CSS, FastAPI, Pydantic, pytest, ruff, ESLint, Prettier                                                | Free, open source                          | Yes              |
| Lesson visualizations: SVG and React components, with free libraries such as Mermaid, Cytoscape.js or D3, Recharts or Chart.js | Free, open source, rendered in the browser | Yes              |
| Lesson storage: JSON files on local disk                                                                                       | Free                                       | Yes (built in)   |
| [Google Gemini API](https://ai.google.dev/gemini-api/docs/pricing) free tier                                                   | Free                                       | **No, optional** |
| GitHub repository and GitHub Actions CI                                                                                        | Free for public repositories               | Optional         |

PDF text extraction uses PyMuPDF, which is free and open source under the AGPL-3.0 licence.

No image-generation APIs are used. The AI returns structured data (nodes, edges, data series) and
the frontend draws every visual with code.

### Credentials

- **Required:** none. The app runs end to end with an empty `.env`.
- **Optional:** `GEMINI_API_KEY`, a free key from [Google AI Studio](https://aistudio.google.com/apikey).
  Do not link a billing account to the key's project. New projects start on the free tier; linking
  billing moves a project to the paid tiers.

### What happens without an API key

- The API starts normally and logs `AI provider is not configured; serving deterministic mock lessons`.
- `GET /api/v1/health` returns `"ai_mode": "mock"`, and the web app footer shows _demo mode_.
- Lesson generation uses `MockLessonGenerator`, which returns the hand-written Photosynthesis lesson
  from `packages/contracts/examples/`. It is deterministic, instant and makes no network calls.
- The frontend can import the same lesson directly from `@visual-learning/contracts`, so UI work
  never waits on the AI pipeline.

### Running the demo on mock data

Leave `GEMINI_API_KEY` empty, or set `AI_PROVIDER=mock` to force mock mode even when a key is
present. Then start the API and web app as usual. Use this for rehearsals, for a predictable live
demo, or if free-tier quota runs out on demo day.

### Free-tier limits to plan around

- Rate limits (requests per minute, tokens per minute, requests per day) apply **per Google Cloud
  project, not per key**. Check your project's actual limits in
  [AI Studio](https://aistudio.google.com/rate-limit). Daily quotas reset at midnight Pacific time.
  A request over the limit fails with HTTP 429, which the API reports as an `AIProviderError`.
- Keep AI calls per lesson low, save generated lessons rather than regenerating them, and generate
  demo lessons ahead of time.
- Free-tier prompts and responses may be used to improve Google products and may be read by human
  reviewers. Send only public, non-personal course material.
- The Gemini API terms require users to be 18 or older and do not allow apps directed at people
  under 18.

## Checks

```bash
python scripts/verify.py    # with the API virtualenv active; same checks as CI
```

## Documentation

- [Architecture overview](docs/architecture/overview.md)
- [Product and MVP scope](docs/product/mvp.md)
- [Team boundaries and branching](docs/development/team-boundaries.md)
- [Getting started](docs/development/getting-started.md)
- [Lesson contract](packages/contracts/README.md)

## Principles

- **Structured output only.** The AI produces data validated against the Lesson contract, never HTML,
  React or images. The frontend decides how to render it.
- **Works without AI.** A missing key or an unavailable provider switches to deterministic mock
  lessons instead of breaking the app.
- **Replaceable provider.** All model calls go through `AIProvider`; Gemini is one implementation.
- **One contract.** `packages/contracts/lesson.schema.json` is the source of truth for API and web.
- **Traceable content.** Lesson sections carry references back to source pages or timestamps.
- **Accessible by default.** Plain literal language, strong hierarchy, high contrast, keyboard access,
  text alternatives for visuals.
- **No secrets in git.** Credentials live only in `.env` files, which are ignored.
