# VisuaLearn web frontend

This is the student-facing frontend for the Visual Learning Accessibility monorepo.

## Run

From the repository root:

```bash
npm install
npm run dev:web
```

The frontend reads the backend URL from `apps/web/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

The PDF lesson flow connects to the existing contract:

- `POST /api/v1/lessons/pdf`
- `GET /api/v1/lessons/{lesson_id}`

The lesson page renders `@visual-learning/contracts` data through the existing `VisualizationRenderer` + adapters. No backend or contract code is changed by the frontend.

The YouTube input remains present in the UI for the MVP experience, but the checked-in API reference currently exposes PDF lesson creation and lesson retrieval only; the frontend therefore keeps YouTube in demo/staged mode rather than inventing a new endpoint.
