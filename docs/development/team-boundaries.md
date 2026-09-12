# Team boundaries

Clear ownership lets three developers work in parallel without editing the same files. When a change
crosses a boundary, the owner of that area reviews it.

## Ownership

### Person 1: AI / Backend lead

- Backend (`services/api/**`)
- AI pipeline: prompts, structured outputs, model configuration (`services/api/app/ai/**`)
- Ingestion: YouTube transcripts, PDF text extraction and OCR (`services/api/app/ingestion/**`)
- Schemas and contracts (`packages/contracts/**`, `services/api/app/schemas/**`)
- APIs, validation, reliability, error handling
- Integration contract between backend and frontend

### Person 2: Frontend / UX engineer

- Next.js app shell, routes and pages (`apps/web/src/app/**`)
- Student experience: upload flow, loading and error states, lesson page layout
- Text-based section renderers: `concept`, `explanation`, `process`, `comparison`, `timeline`,
  `example`, and the quiz (`apps/web/src/components/lesson/**`)
- Shared UI components, accessibility, responsive design (`apps/web/src/components/**` except
  `visuals/`)
- API client usage (`apps/web/src/lib/**`)

### Person 3: Visualization / integration engineer

- Visual renderers for `concept_map`, `diagram` and `chart` sections
  (`apps/web/src/components/visuals/**`, to be created)
- Choice of rendering libraries for graph layout and charting: free and open-source only, drawing
  visuals with code (SVG/React, Mermaid, Cytoscape.js or D3, Recharts or Chart.js), never
  image-generation APIs
- Visual interaction: zoom, focus, highlighting related nodes, keyboard navigation of visuals
- End-to-end integration testing of web and API
- Deployment and CI support (`.github/**`)

### Person 4: Research / product / presentation

- User and problem research, competitor analysis, evidence (`docs/product/**`, `docs/research/**`)
- Product requirements and acceptance criteria
- Pitch deck, demo script and final presentation
- Testing from the user's perspective, with feedback filed as GitHub issues

## Integration seams

| Seam                  | Contract                                                                                                                          | Rule                                                                                            |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| API ↔ Web             | `packages/contracts/lesson.schema.json`, `/api/v1` endpoints                                                                      | Contract changes go in small, separate PRs reviewed by Person 1 and the affected frontend owner |
| Lesson page ↔ visuals | A renderer component per visual type, taking the typed `content` for its section, e.g. `<ConceptMap content={section.content} />` | Person 2 owns the page and the section switch; Person 3 owns the component internals            |
| Web ↔ API client      | `apps/web/src/lib/api-client.ts`                                                                                                  | Components never call `fetch` directly                                                          |

Until generation endpoints exist, the frontend builds against `photosynthesisExampleLesson` from
`@visual-learning/contracts`.

## Branching strategy

- `main` must always build and pass CI. Nobody commits directly to `main` once the remote exists.
- Each person works on short-lived branches from `main`:
  - `feat/ai-pipeline` (Person 1)
  - `feat/frontend` (Person 2)
  - `feat/visualization` (Person 3)
  - `docs/...` (Person 4)
- For a focused change, prefer a narrower branch such as `feat/pdf-extraction` or `feat/quiz-ui`.
- Merge to `main` through a pull request at least every few hours. In a 36-hour event, long-lived
  branches cause painful late merges.
- Contract changes use their own branch (`contract/...`) and merge first, so everyone rebases onto
  the new contract.
- Pull `main` into your branch often (`git pull --rebase origin main`).
- Squash-merge pull requests to keep `main` readable.

## Working agreements

- Run `python scripts/verify.py` (or the relevant subset) before opening a PR.
- Never commit `.env` files, API keys, or real student data.
- Keep pull requests small and single-purpose.
- If you need something from another area, open an issue or ask. Do not edit another owner's files
  without them knowing.

## GitHub setup to do once the remote exists

- Protect `main`: require a PR and passing CI.
- Fill in real GitHub usernames in `.github/CODEOWNERS` so reviews are requested automatically.
