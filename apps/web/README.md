# Web app (`apps/web`)

Next.js (App Router, TypeScript, Tailwind CSS) student-facing frontend.
Owners: Person 2 (pages, UX, accessibility) and Person 3 (visual renderers, integration).
See [team boundaries](../../docs/development/team-boundaries.md).

```text
src/
  app/                 routes, root layout, global styles
  components/
    layout/            site header and footer
    upload/            upload workflow (placeholder)
    lesson/            lesson presentation
    status/            API connectivity indicator
  lib/
    config.ts          public environment configuration
    api-client.ts      typed client for the FastAPI service
```

Lesson data types come from `@visual-learning/contracts` (`packages/contracts`). Use
`photosynthesisExampleLesson` to build UI before the API can generate lessons.

Run from the repository root:

| Task                               | Command             |
| ---------------------------------- | ------------------- |
| Dev server (http://localhost:3000) | `npm run dev:web`   |
| Lint                               | `npm run lint:web`  |
| Production build                   | `npm run build:web` |

Configuration: copy `.env.example` to `.env.local`.
