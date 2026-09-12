# Getting started

## Prerequisites

| Tool    | Version       | Check              |
| ------- | ------------- | ------------------ |
| Node.js | 20.9 or newer | `node --version`   |
| npm     | 10 or newer   | `npm --version`    |
| Python  | 3.11 or newer | `python --version` |
| Git     | any recent    | `git --version`    |

No paid accounts or API keys are needed. See "Zero-Cost Development" in the [README](../../README.md).

> **Windows and OneDrive:** keep the repository outside OneDrive-synced folders if you can.
> Syncing `node_modules/` and `.venv/` is slow and can cause "file in use" errors during installs and
> builds.

## 1. Clone and configure

```bash
git clone https://github.com/shloknarvekar/visual-learning-accessibility.git
cd visual-learning-accessibility
```

Create local configuration files from the templates. Both are git-ignored.

```bash
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
```

PowerShell:

```powershell
Copy-Item .env.example .env
Copy-Item apps/web/.env.example apps/web/.env.local
```

| File                     | Used by | Variables                                                                                                                                                                                                     |
| ------------------------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.env` (repository root) | API     | `APP_ENV`, `LOG_LEVEL`, `CORS_ALLOWED_ORIGINS`, `AI_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `DATA_DIR`, `MAX_UPLOAD_MB`, `PDF_MAX_PAGES`, `CHUNK_MAX_CHARS`, `AI_SINGLE_PASS_MAX_CHARS`, `AI_MAX_CHUNKS` |
| `apps/web/.env.local`    | Web     | `NEXT_PUBLIC_API_BASE_URL`                                                                                                                                                                                    |

Every backend value is optional. Without `GEMINI_API_KEY` the API runs in **mock mode** and returns a
deterministic example lesson, clearly marked as demo data. To enable AI generation, create a free key
in [Google AI Studio](https://aistudio.google.com/apikey) (do not add billing) and set
`GEMINI_API_KEY` in `.env`.

Never put secrets in `apps/web/.env.local`: `NEXT_PUBLIC_*` values are visible in the browser.

## 2. Backend (`services/api`)

macOS / Linux:

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Windows (PowerShell):

```powershell
cd services/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks `Activate.ps1`, skip activation and call the virtualenv's Python directly,
for example `.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000`.

Check it works:

- http://localhost:8000/api/v1/health returns
  `{"status":"ok","service":"api","version":"0.1.0","ai_mode":"mock"}`
  (`"ai_mode":"gemini"` once a key is configured)
- http://localhost:8000/docs shows interactive API docs (development only)

### Try the PDF endpoint

Use any text-based PDF (scanned PDFs are not supported yet). From a terminal:

macOS / Linux:

```bash
curl -F "file=@notes.pdf" http://localhost:8000/api/v1/lessons/pdf
```

Windows (PowerShell uses `curl.exe`, because `curl` is an alias there):

```powershell
curl.exe -F "file=@notes.pdf" http://localhost:8000/api/v1/lessons/pdf
```

The response contains `lesson_id`, `metadata` and the `lesson`. Fetch it again with:

```bash
curl http://localhost:8000/api/v1/lessons/<lesson_id>
```

You can also use **POST /api/v1/lessons/pdf → Try it out** at http://localhost:8000/docs.

Check `metadata.is_mock`: `true` means demo data (no key configured), `false` means the lesson was
generated from your PDF. `metadata.warnings` lists anything that was removed or corrected when the AI
output was checked.

### Backend checks

From `services/api`, virtualenv active:

```bash
pytest              # unit and API tests; no network, no API key needed
ruff check .        # lint
ruff format .       # format
pytest -m live      # optional: real Gemini requests (free-tier quota); needs GEMINI_API_KEY
```

## 3. Frontend (`apps/web`)

From the repository root, in a second terminal:

```bash
npm install         # installs every workspace (web + contracts)
npm run dev:web     # http://localhost:3000
```

The footer shows "API connected" when the backend is running and CORS is configured correctly, and
"demo mode" when the API has no AI key.

Frontend checks (from the repository root):

```bash
npm run lint:web
npm run build:web
```

## 4. Contracts (`packages/contracts`)

```bash
npm run contracts:validate   # example lessons match the schema
npm run contracts:generate   # regenerate TypeScript types after editing the schema
npm run contracts:check      # fail if generated types are stale
```

## 5. Run everything CI runs

From the repository root, with the API virtualenv active:

```bash
python scripts/verify.py
python scripts/verify.py --skip-web-build   # faster
```

## Troubleshooting

| Problem                                                 | Fix                                                                                                                                                                                                        |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Footer shows "API not reachable"                        | Start the API on port 8000; check `NEXT_PUBLIC_API_BASE_URL` and that `CORS_ALLOWED_ORIGINS` includes `http://localhost:3000`. Restart `npm run dev:web` after changing `.env.local`.                      |
| Footer shows "demo mode" but you set a key              | `.env` must be in the repository root, `AI_PROVIDER` must be `gemini`, and the API must be restarted after editing `.env`.                                                                                 |
| `PDF_HAS_NO_EXTRACTABLE_TEXT`                           | The PDF is scanned or image-only. OCR is planned; use a PDF with selectable text.                                                                                                                          |
| `FILE_TOO_LARGE` or `PDF_TOO_MANY_PAGES`                | Use a shorter PDF, or raise `MAX_UPLOAD_MB` / `PDF_MAX_PAGES` in `.env`.                                                                                                                                   |
| `DOCUMENT_TOO_LONG`                                     | The text needs more AI requests than `AI_MAX_CHUNKS` allows. Upload a single chapter.                                                                                                                      |
| `AI_RATE_LIMITED` (429)                                 | Free-tier quota is exhausted. Wait (daily quota resets at midnight Pacific), try a Flash-Lite model via `GEMINI_MODEL`, or demo with `AI_PROVIDER=mock`.                                                   |
| `Address already in use`                                | Another process uses the port. Use `--port 8001` for the API (and update `NEXT_PUBLIC_API_BASE_URL`), or `npm run dev:web -- --port 3001` for the web app (and add that origin to `CORS_ALLOWED_ORIGINS`). |
| API fails at startup with a settings error              | A value in `.env` is invalid; the error names the variable. Compare with `.env.example`.                                                                                                                   |
| `EPERM` / "file in use" during `npm install` on Windows | Close editors or dev servers using the folder, pause OneDrive sync, and retry.                                                                                                                             |
