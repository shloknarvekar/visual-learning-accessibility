# Contracts (`packages/contracts`)

The shared, technology-neutral contract between the API and the web app.

| File                      | Purpose                                                        |
| ------------------------- | -------------------------------------------------------------- |
| `lesson.schema.json`      | **Source of truth** for the Lesson JSON (JSON Schema 2020-12). |
| `examples/photosynthesis.lesson.json` | Hand-written lesson for building UI without the API. Demonstrates 6 of the 9 section types (`concept`, `explanation`, `process`, `comparison`, `concept_map`, `example`); this is also the fixed lesson served in mock/demo mode. |
| `examples/all-section-types.lesson.json` | Reference fixture covering all 9 section types, including the 3 the file above doesn't (`timeline`, `diagram`, `chart`). Not used by the app at runtime — for backend/frontend integration reference only. See [`docs/architecture/api-reference.md`](../../docs/architecture/api-reference.md). |
| `src/generated/lesson.ts` | TypeScript types generated from the schema. Do not edit.       |
| `src/index.ts`            | Package entry: re-exports the types and the example lesson.    |

The backend mirrors the schema in `services/api/app/schemas/lesson.py` (Pydantic).
`services/api/tests/test_lesson_contract.py` fails if the two drift apart.

## Using it in the web app

```ts
import { photosynthesisExampleLesson, type Lesson, type Section } from "@visual-learning/contracts";
```

Render each section by switching on `section.type`; TypeScript narrows `section.content` to the
matching shape.

## Rules

- All human-readable strings are **plain text**. No HTML or Markdown, so rendering is deterministic
  and safe.
- Arrays are ordered: render `sections`, `steps` and `events` in array order.
- Ids are unique within their parent collection and match `^[A-Za-z0-9_-]{1,64}$`.
- The API guarantees references resolve (graph edges point at existing nodes, quiz answers match an
  option, `section_ids` exist).
- `source_references` carry provenance: `page_number` for PDFs, `start_time_seconds`/`end_time_seconds`
  for video, optional verbatim `excerpt`.
- Charts and diagrams include a `summary` used as their text alternative.

## Changing the contract

Contract changes affect every team member, so keep them small and deliberate.

1. Edit `lesson.schema.json`. For breaking changes, bump `schema_version`.
2. Update `services/api/app/schemas/lesson.py` to match.
3. Update the examples if needed.
4. Run `npm run contracts:generate`, `npm run contracts:validate`, and the API tests.
5. Open a PR that touches only the contract (plus mirror and examples), reviewed by Person 1 and the
   affected frontend owner.
