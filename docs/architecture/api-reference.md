# Lessons API reference

Audience: Person 2 (frontend/UX) and Person 3 (visualization/integration), building against
`services/api` without needing to read its source. For the rationale behind these design choices
(routing, provider fallback, grounding, etc.) see [overview.md](overview.md). For the JSON Schema
itself and the rules every field follows, see
[`packages/contracts/README.md`](../../packages/contracts/README.md).

Base URL in local development: `http://localhost:8000` (`NEXT_PUBLIC_API_BASE_URL` in
`apps/web/.env.local`). All endpoints below are relative to that.

## Endpoints

There is one endpoint per input type rather than a single endpoint with a discriminator field,
because the three requests do not share a shape: a PDF and a video are both `multipart/form-data`
but accept different file types and size limits, while a YouTube lesson is a small JSON body with
no upload at all. All three return the same `LessonRecord` — a client renders one shape and reads
`lesson.source.source_type` when it needs to know where the lesson came from.

### `POST /api/v1/lessons/pdf`

Creates a lesson from an uploaded PDF.

- **Request:** `multipart/form-data` with one field, `file` (a PDF; must start with `%PDF-`).
- **Success:** `201 Created`, body is a [`LessonRecord`](#the-lessonrecord-shape).
- **Errors:** see the [error catalog](#error-catalog) below.

```bash
curl -F "file=@notes.pdf" http://localhost:8000/api/v1/lessons/pdf
```

### `POST /api/v1/lessons/video`

Creates a lesson from an uploaded video.

- **Request:** `multipart/form-data` with one field, `file`. Accepted types: `video/mp4`,
  `video/mpeg`, `video/mpg`, `video/mov` (`video/quicktime` is also accepted and treated the same),
  `video/avi` (`video/x-msvideo` too), `video/x-flv`, `video/webm`, `video/wmv`
  (`video/x-ms-wmv`/`video/x-ms-asf` too), `video/3gpp` (`video/3gp` too). The declared type and the
  file's own leading bytes must agree, or the upload is rejected before anything is sent anywhere.
- **Success:** `201 Created`, body is a [`LessonRecord`](#the-lessonrecord-shape) whose
  `metadata.page_count` is absent (a video has no pages) and whose
  `metadata.chunk_count`/`character_count` are `0`.
- **Errors:** see the [error catalog](#error-catalog) below — in particular `INVALID_FILE_TYPE` for
  an unsupported or mismatched video, and `AI_INPUT_NOT_SUPPORTED` when no configured provider can
  watch video at all.

```bash
curl -F "file=@lecture.mp4" http://localhost:8000/api/v1/lessons/video
```

### `POST /api/v1/lessons/youtube`

Creates a lesson from a public YouTube video. The API never downloads the video; the URL is
rebuilt into a canonical `https://www.youtube.com/watch?v=<id>` form and handed to the AI provider,
which resolves it itself.

- **Request:** `application/json` body: `{"url": "<a link to a single public video>"}`. Watch,
  short (`youtu.be/...`), `shorts`, `embed` and `live` links are all accepted; channel, playlist and
  search links are not, because there is no single video to watch.
- **Success:** `201 Created`, body is a [`LessonRecord`](#the-lessonrecord-shape) shaped exactly
  like the video-upload response, except `metadata.source_filename` is absent (there is no
  uploaded file).
- **Errors:** see the [error catalog](#error-catalog) below — in particular `INVALID_VIDEO_URL` for
  a link that isn't a single public YouTube video.

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' \
  http://localhost:8000/api/v1/lessons/youtube
```

### `GET /api/v1/lessons/{lesson_id}`

Fetches a previously created lesson.

- **Success:** `200 OK`, the same `LessonRecord` returned by the `POST` that created it.
- **Errors:** `404 LESSON_NOT_FOUND` for an unknown or invalid id.

All four endpoints return byte-for-byte the same `LessonRecord` shape — `GET` never returns less
than the `POST` that created the lesson did, so a client can safely refetch a lesson instead of
holding it in memory.

## The `LessonRecord` shape

```json
{
  "lesson_id": "string",
  "metadata": {
    "provider": "gemini | openrouter | groq | cache | demo",
    "generation_status": "live | fallback | cached | demo",
    "is_mock": "boolean",
    "notice": "string, present only for fallback/cached/demo",
    "model": "string, present only when a live AI model produced this lesson",
    "source_filename": "string, present only for an uploaded PDF or video, absent for YouTube",
    "page_count": "integer, present only for a PDF, absent for video and YouTube",
    "chunk_count": "integer",
    "character_count": "integer",
    "ai_request_count": "integer",
    "warnings": ["string", "..."],
    "timings": {
      "extraction_ms": "integer",
      "chunking_ms": "integer",
      "generation_ms": "integer",
      "validation_ms": "integer",
      "total_ms": "integer"
    },
    "created_at": "ISO-8601 datetime"
  },
  "lesson": { "...": "a Lesson, see below" }
}
```

`notice` and `model` are **omitted from the JSON entirely** when not applicable (the API serialises
with `exclude_none`), not sent as `null`. Check for the key's presence, not its value.

### `metadata` field reference

| Field                            | Always present?                                | Notes                                                                                                                                                                                                                                                                                           |
| -------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `provider`                       | yes                                            | Who produced the lesson: an AI provider name, `"cache"`, or `"demo"`. Never used for rendering — see [Contract stability](#contract-stability-what-you-can-rely-on).                                                                                                                            |
| `generation_status`              | yes                                            | One of four states; see the [status matrix](#generation-status-and-degraded-states) below.                                                                                                                                                                                                      |
| `is_mock`                        | yes                                            | `true` only when `provider` is `"demo"` — the lesson is fixed example content, not about the uploaded file.                                                                                                                                                                                     |
| `notice`                         | only for fallback/cached/demo                  | Plain-language, user-safe sentence explaining why this isn't a fresh, live result. Safe to show directly in the UI.                                                                                                                                                                             |
| `model`                          | only when a live/fallback AI provider answered | Absent for `cache` and `demo`.                                                                                                                                                                                                                                                                  |
| `warnings`                       | yes (may be `[]`)                              | Things that were removed or corrected before the lesson was accepted — e.g. an unverifiable quote, or scanned pages with no extractable text. For a video/YouTube lesson, also says when a quote came from what was said in the video and was not checked word for word. Safe to show to users. |
| `timings`                        | yes                                            | Milliseconds per pipeline stage, useful for a loading-progress UI.                                                                                                                                                                                                                              |
| `source_filename`                | only for an uploaded PDF or video              | Absent for a YouTube lesson, which has no uploaded file. Branch on `lesson.source.source_type`, not on this field's presence, if you need to know the input type.                                                                                                                               |
| `page_count`                     | only for a PDF                                 | Absent for video and YouTube lessons, which have no pages.                                                                                                                                                                                                                                      |
| `chunk_count`, `character_count` | yes                                            | Both `0` for a video/YouTube lesson: nothing was extracted or chunked.                                                                                                                                                                                                                          |
| `ai_request_count`, `created_at` | yes                                            | Informational; not needed to render the lesson.                                                                                                                                                                                                                                                 |

## Generation status and degraded states

| `generation_status` | `provider`                       | `is_mock` | `notice` | Meaning                                                                                                 |
| ------------------- | -------------------------------- | --------- | -------- | ------------------------------------------------------------------------------------------------------- |
| `live`              | `gemini` / `openrouter` / `groq` | `false`   | absent   | The primary configured provider answered.                                                               |
| `fallback`          | `gemini` / `openrouter` / `groq` | `false`   | present  | The primary provider failed; a backup provider answered instead.                                        |
| `cached`            | `cache`                          | `false`   | present  | Every provider failed; an earlier lesson for the same document text was reused.                         |
| `demo`              | `demo`                           | `true`    | present  | Every provider failed and nothing was cached; fixed example content is returned so the UI never breaks. |

Example `metadata` for each (fields other than the ones below are the same shape as the full
example further down):

```json
// fallback
{
  "provider": "openrouter",
  "generation_status": "fallback",
  "is_mock": false,
  "notice": "The main AI provider was unavailable, so this lesson was generated by openrouter.",
  "warnings": ["gemini was unavailable: rate limit exceeded"]
}
```

```json
// cached
{
  "provider": "cache",
  "generation_status": "cached",
  "is_mock": false,
  "notice": "No AI provider was available. This lesson comes from an earlier successful generation of the same document."
}
```

```json
// demo
{
  "provider": "demo",
  "generation_status": "demo",
  "is_mock": true,
  "notice": "Demo mode: AI generation is off or has no API key, so this lesson is fixed example data. It does not describe the uploaded PDF."
}
```

If you only render one thing to distinguish "this is real" from "this is a fallback": show
`metadata.notice` whenever it is present, and treat `is_mock: true` as "definitely not about the
uploaded file" (worth a distinct visual treatment, e.g. a banner).

**A request never silently degrades past what the config allows.** With
`AI_FALLBACK_TO_DEMO=false` and no cache hit, exhausting every provider is a `503
AI_PROVIDER_UNAVAILABLE` instead of demo content — see the error catalog.

## Error catalog

Every error response has the same envelope:

```json
{
  "error": {
    "code": "PDF_HAS_NO_EXTRACTABLE_TEXT",
    "message": "This PDF does not contain extractable text. OCR support is planned.",
    "details": null
  }
}
```

`code` is stable and meant to be switched on; `message` is plain language, safe to show to users,
and may change wording over time; `details` is present only for `VALIDATION_ERROR` (a list of
per-field problems) and otherwise omitted.

| `code`                          | HTTP         | When                                                                                                                                                                                                                               |
| ------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `INVALID_FILE_TYPE`             | 415          | The upload doesn't match what the endpoint accepts: for `/pdf`, wrong declared content type or the bytes don't start with `%PDF-`; for `/video`, an unsupported video type or one whose declared type and file signature disagree. |
| `FILE_TOO_LARGE`                | 413          | Upload exceeds `MAX_UPLOAD_MB` (PDF) or `MAX_VIDEO_UPLOAD_MB` (video).                                                                                                                                                             |
| `PDF_EXTRACTION_FAILED`         | 422          | The PDF is damaged, password-protected, or has zero pages.                                                                                                                                                                         |
| `PDF_HAS_NO_EXTRACTABLE_TEXT`   | 422          | Scanned/image-only PDF — no OCR yet.                                                                                                                                                                                               |
| `PDF_TOO_MANY_PAGES`            | 422          | Over `PDF_MAX_PAGES`.                                                                                                                                                                                                              |
| `DOCUMENT_TOO_LONG`             | 422          | The document would need more AI requests than `AI_MAX_CHUNKS` allows.                                                                                                                                                              |
| `INVALID_VIDEO_URL`             | 422          | The `youtube` request body's `url` is not a link to a single public YouTube video.                                                                                                                                                 |
| `VIDEO_PROCESSING_FAILED`       | 502          | The video-capable provider could not process the video (for example, it rejected the file or the link when it tried to watch it).                                                                                                  |
| `AI_RATE_LIMITED`               | 429          | Every configured provider is currently rate-limited.                                                                                                                                                                               |
| `AI_INVALID_RESPONSE`           | 502          | A provider's output didn't match the required schema.                                                                                                                                                                              |
| `LESSON_VALIDATION_FAILED`      | 502          | No valid lesson could be assembled from the AI output.                                                                                                                                                                             |
| `AI_PROVIDER_UNAVAILABLE`       | 503          | **Covers both an unreachable/failing provider and a request timeout** (each provider has its own hard wall-clock deadline; a hang is treated exactly like an outage — never a hung HTTP request on the client).                    |
| `AI_INPUT_NOT_SUPPORTED`        | 503          | No configured provider can read this input at all — for example, a `video`/`youtube` request when only text-capable providers are configured. Retrying will not help; configuring a video-capable provider will.                   |
| `LESSON_NOT_FOUND`              | 404          | Unknown or malformed `lesson_id`.                                                                                                                                                                                                  |
| `VALIDATION_ERROR`              | 422          | Malformed request — e.g. no `file` field in the multipart body, or no `url` field for `/lessons/youtube`.                                                                                                                          |
| `HTTP_ERROR` / `INTERNAL_ERROR` | varies / 500 | Fallback envelopes for routing errors and truly unexpected failures; stack traces are never included.                                                                                                                              |

"Invalid PDF" and "timeout" are not distinct codes — they map onto the rows above
(`INVALID_FILE_TYPE`/`PDF_EXTRACTION_FAILED`/`PDF_HAS_NO_EXTRACTABLE_TEXT` for a bad PDF,
`AI_PROVIDER_UNAVAILABLE` for a timeout), so a client only needs to switch on `error.code`, never
on transport-level signals like "the request took a long time."

## Contract stability: what you can rely on

- **`sections[].type` is the only thing you need to pick a renderer.** Every section's `content`
  shape is fully determined by `type` (a discriminated union in the schema). The API never requires
  branching on `metadata.provider` to decide how to render a section — the same draft, run through
  two different AI providers, produces byte-identical `lesson` JSON (proven by
  `test_lesson_json_is_identical_regardless_of_which_provider_answered` in
  `services/api/tests/test_lessons_api.py`).
- **All 9 section types can appear in one lesson**, and each is exercised end-to-end in
  `test_all_section_types_round_trip_through_the_api_and_match_the_shared_schema`
  (`services/api/tests/test_lessons_api.py`).
- **Every `Lesson` the API returns has already been validated twice**: once during assembly, and
  again from its own serialised JSON, exactly as clients receive it. If you can parse it against
  `packages/contracts/lesson.schema.json`, you can render it without defensive checks.
- **Ids are unique within their parent collection**, and every reference resolves: graph edges
  point at existing nodes, quiz `correct_option_id` matches an option, quiz `section_ids` reference
  existing sections. Sections or quiz questions the API couldn't validate are dropped, never sent
  malformed — check `metadata.warnings` to see what (if anything) was removed.
- **`lesson.subject` is always present** and is one of `biology`, `mathematics`, `physics`,
  `chemistry`, `history`, `computer_science`, `geography` or `general`. It is the model's own guess
  at the lesson's academic subject, normalised server-side; `general` means the subject could not
  be confidently determined, not that the lesson is uncategorised. Use it to pick a visual theme —
  it never affects which section renderer you use, only how it's styled.
- **`lesson.source.source_type` is `pdf`, `video` or `youtube`.** An uploaded PDF or video carries
  `source.filename` (a display name, never a server path); a YouTube video carries `source.url`
  (the canonical watch URL). Use this field, not `metadata.source_filename`'s presence, to tell the
  three input types apart.

### Source references: pages vs. timestamps

Every section and quiz question may carry `source_references`, each pointing back to where its
content came from. Which locator is present depends on `lesson.source.source_type`, not on the
section's own `type`:

- **`pdf`:** `page_number` (1-based), optionally with a verbatim `excerpt` the API confirmed
  appears on that page.
- **`video` / `youtube`:** `start_time_seconds` and optionally `end_time_seconds` (both 0-based
  seconds from the start of the video), optionally with an `excerpt` of what was said at that
  point. There is no transcript to check a quote against, so a video/YouTube lesson's
  `metadata.warnings` says explicitly when quotes come from what was heard and were not checked
  word for word — don't present them with the same confidence as a checked PDF citation.

In practice the API never mixes the two: a reference built from a PDF carries no timestamp fields,
and one built from a video carries no `page_number` — but the schema's own guarantee is only
`minProperties: 1`, so treat `SourceReference` as "whichever of these keys are present," not as a
fixed shape.

## The 9 section types, one example of each

The [`photosynthesis.lesson.json`](../../packages/contracts/examples/photosynthesis.lesson.json)
example only demonstrates 6 of the 9 (`concept`, `explanation`, `process`, `comparison`,
`concept_map`, `example`). A new fixture,
[`all-section-types.lesson.json`](../../packages/contracts/examples/all-section-types.lesson.json),
adds the missing three (`timeline`, `diagram`, `chart`) plus repeats the other six, so all 9 are in
one place. It is schema-validated by `npm run contracts:validate` like every other example.

| `type`        | Renderer needs (`content` shape)                                                                                                     | Owner    |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| `concept`     | `term`, `definition`, `key_points[]`                                                                                                 | Person 2 |
| `explanation` | `body`, `key_points[]`                                                                                                               | Person 2 |
| `process`     | `steps[]` of `{id, title, description}`, ordered                                                                                     | Person 2 |
| `comparison`  | `items[]`, `rows[]` of `{criterion, values[]}` (one value per item, same order)                                                      | Person 2 |
| `timeline`    | `events[]` of `{id, time_label, title, description}`, ordered                                                                        | Person 2 |
| `example`     | `scenario`, `explanation`                                                                                                            | Person 2 |
| `concept_map` | `summary`, `nodes[]` of `{id, label, description?}`, `edges[]` of `{from_id, to_id, label?}`                                         | Person 3 |
| `diagram`     | as `concept_map`, plus `diagram_type`: `"flowchart" \| "cycle" \| "hierarchy"`                                                       | Person 3 |
| `chart`       | `chart_type`: `"bar" \| "line" \| "pie"`, `summary`, optional axis labels/`unit`, `series[]` of `{name, points[] of {label, value}}` | Person 3 |

Below: the three previously-missing types, taken verbatim from `all-section-types.lesson.json`.

**`timeline`**

```json
{
  "id": "sec-timeline",
  "type": "timeline",
  "title": "How photosynthesis was understood",
  "source_references": [
    {
      "page_number": 3,
      "excerpt": "In 1930 Cornelis van Niel proposed the modern equation for photosynthesis."
    }
  ],
  "content": {
    "events": [
      {
        "id": "event-1930-equation",
        "time_label": "1930",
        "title": "Modern equation proposed",
        "description": "Cornelis van Niel proposed the modern equation for photosynthesis, based on studies of bacteria."
      },
      {
        "id": "event-1950-reactions-confirmed",
        "time_label": "1950",
        "title": "Two-stage process confirmed",
        "description": "Researchers confirmed the separate light-dependent and light-independent (Calvin cycle) stages."
      }
    ]
  }
}
```

**`diagram`**

```json
{
  "id": "sec-diagram-cycle",
  "type": "diagram",
  "title": "The Calvin cycle as a loop",
  "source_references": [
    {
      "page_number": 3,
      "excerpt": "The Calvin cycle turns carbon dioxide into glucose in a series of steps."
    }
  ],
  "content": {
    "diagram_type": "cycle",
    "summary": "Carbon dioxide enters the cycle, is fixed and reduced using ATP and NADPH, and glucose precursors leave the cycle while the original 5-carbon molecule is regenerated.",
    "nodes": [
      { "id": "d-co2", "label": "Carbon dioxide enters" },
      {
        "id": "d-fix",
        "label": "Carbon fixation",
        "description": "CO2 attaches to a 5-carbon molecule"
      },
      {
        "id": "d-reduce",
        "label": "Reduction",
        "description": "ATP and NADPH convert it to sugar precursors"
      },
      {
        "id": "d-regenerate",
        "label": "Regeneration",
        "description": "The original 5-carbon molecule is rebuilt"
      }
    ],
    "edges": [
      { "from_id": "d-co2", "to_id": "d-fix" },
      { "from_id": "d-fix", "to_id": "d-reduce" },
      { "from_id": "d-reduce", "to_id": "d-regenerate", "label": "some product" },
      { "from_id": "d-regenerate", "to_id": "d-fix", "label": "regenerated molecule" }
    ]
  }
}
```

**`chart`**

```json
{
  "id": "sec-chart-bubbles",
  "type": "chart",
  "title": "Bubbles per minute vs. distance from the lamp",
  "source_references": [
    {
      "page_number": 3,
      "excerpt": "12 bubbles formed per minute at 10 cm and 30 bubbles formed per minute at 5 cm from the lamp."
    }
  ],
  "content": {
    "chart_type": "bar",
    "summary": "Moving the lamp closer to the pondweed increased the rate of bubble formation, showing that light intensity was limiting the rate of photosynthesis at the greater distance.",
    "x_axis_label": "Distance from lamp",
    "y_axis_label": "Bubbles per minute",
    "unit": "bubbles/min",
    "series": [
      {
        "name": "Pondweed",
        "points": [
          { "label": "10 cm", "value": 12 },
          { "label": "5 cm", "value": 30 }
        ]
      }
    ]
  }
}
```

## A complete `LessonRecord` example

Full response as returned by `POST /api/v1/lessons/pdf`, using the same content as
`all-section-types.lesson.json` (trimmed to 2 of the 9 sections here for length — the fixture file
has all 9, plus the full quiz with `source_references`):

```json
{
  "lesson_id": "3f2b9c7a8e1d4f60b9c2a7e5d3f10abc",
  "metadata": {
    "provider": "gemini",
    "generation_status": "live",
    "is_mock": false,
    "model": "gemini-3.8-flash",
    "source_filename": "biology-notes-chapter-8.pdf",
    "page_count": 6,
    "chunk_count": 1,
    "character_count": 14210,
    "ai_request_count": 1,
    "warnings": [
      "1 quote(s) could not be found on the cited page and were moved to the right page."
    ],
    "timings": {
      "extraction_ms": 40,
      "chunking_ms": 1,
      "generation_ms": 14200,
      "validation_ms": 3,
      "total_ms": 14260
    },
    "created_at": "2026-09-12T10:00:00Z"
  },
  "lesson": {
    "schema_version": "0.1.0",
    "id": "3f2b9c7a8e1d4f60b9c2a7e5d3f10abc",
    "title": "Photosynthesis: A Complete Section-Type Reference",
    "overview": "A reference lesson that exercises every section type in the Lesson contract.",
    "source": {
      "source_type": "pdf",
      "title": "Biology Notes, Chapter 8: Photosynthesis",
      "filename": "biology-notes-chapter-8.pdf"
    },
    "subject": "biology",
    "sections": [
      {
        "id": "sec-definition",
        "type": "concept",
        "title": "What is photosynthesis?",
        "source_references": [
          {
            "page_number": 1,
            "excerpt": "Photosynthesis converts light energy into chemical energy stored in glucose."
          }
        ],
        "content": {
          "term": "Photosynthesis",
          "definition": "The process in which plants, algae and some bacteria use light energy to make glucose from carbon dioxide and water. Oxygen is released.",
          "key_points": [
            "Inputs: carbon dioxide, water and light energy.",
            "Outputs: glucose and oxygen."
          ]
        }
      },
      {
        "id": "sec-chart-bubbles",
        "type": "chart",
        "title": "Bubbles per minute vs. distance from the lamp",
        "source_references": [
          {
            "page_number": 3,
            "excerpt": "12 bubbles formed per minute at 10 cm and 30 bubbles formed per minute at 5 cm from the lamp."
          }
        ],
        "content": {
          "chart_type": "bar",
          "summary": "Moving the lamp closer to the pondweed increased the rate of bubble formation.",
          "x_axis_label": "Distance from lamp",
          "y_axis_label": "Bubbles per minute",
          "unit": "bubbles/min",
          "series": [
            {
              "name": "Pondweed",
              "points": [
                { "label": "10 cm", "value": 12 },
                { "label": "5 cm", "value": 30 }
              ]
            }
          ]
        }
      }
    ],
    "quiz": [
      {
        "id": "q-oxygen",
        "type": "multiple_choice",
        "prompt": "Which gas do plants release during photosynthesis?",
        "options": [
          { "id": "a", "text": "Carbon dioxide" },
          { "id": "b", "text": "Oxygen" },
          { "id": "c", "text": "Nitrogen" }
        ],
        "correct_option_id": "b",
        "explanation": "Water is split during the light-dependent reactions. Oxygen is released as a by-product.",
        "section_ids": ["sec-definition", "sec-calvin-cycle"]
      }
    ]
  }
}
```

(Only 2 of the 9 sections are shown here for length; the full 9-section, 3-question lesson is in
`all-section-types.lesson.json`, wrapped in a `LessonRecord` envelope exactly like this one when
served by the API.)

### A video/YouTube `LessonRecord`, for comparison

Same shape, but from `POST /api/v1/lessons/youtube`. Note what's absent (`page_count`,
`source_filename`), what's `0` (`chunk_count`, `character_count`), and that `source_references`
carry `start_time_seconds`/`end_time_seconds` instead of `page_number`:

```json
{
  "lesson_id": "7a1c4e9b2d3f4a5b8c9d0e1f2a3b4c5d",
  "metadata": {
    "provider": "gemini",
    "generation_status": "live",
    "is_mock": false,
    "model": "gemini-3.8-flash",
    "chunk_count": 0,
    "character_count": 0,
    "ai_request_count": 1,
    "warnings": [
      "2 quote(s) come from what is said in the video. They are placed at the time they were heard but were not checked word for word."
    ],
    "timings": {
      "extraction_ms": 0,
      "chunking_ms": 0,
      "generation_ms": 9800,
      "validation_ms": 2,
      "total_ms": 9810
    },
    "created_at": "2026-09-12T10:00:00Z"
  },
  "lesson": {
    "schema_version": "0.1.0",
    "id": "7a1c4e9b2d3f4a5b8c9d0e1f2a3b4c5d",
    "title": "Photosynthesis, explained",
    "overview": "A recorded lecture on how plants convert light into chemical energy.",
    "source": {
      "source_type": "youtube",
      "title": "YouTube video",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    },
    "subject": "biology",
    "sections": [
      {
        "id": "sec-definition",
        "type": "concept",
        "title": "What is photosynthesis?",
        "source_references": [
          {
            "start_time_seconds": 42,
            "end_time_seconds": 58,
            "excerpt": "Plants take in light, water and carbon dioxide, and turn them into glucose and oxygen."
          }
        ],
        "content": {
          "term": "Photosynthesis",
          "definition": "The process in which plants use light energy to make glucose from carbon dioxide and water. Oxygen is released.",
          "key_points": [
            "Inputs: carbon dioxide, water and light energy.",
            "Outputs: glucose and oxygen."
          ]
        }
      }
    ],
    "quiz": []
  }
}
```

## CORS and local development

The API's CORS policy (`services/api/app/main.py`, configured via `CORS_ALLOWED_ORIGINS` in
`services/api/app/core/config.py`):

- **Default allowed origin:** `http://localhost:3000` — matches `npm run dev:web`'s default port,
  so local frontend development works with zero configuration.
- **Methods:** `GET, POST` only (the only methods the API exposes).
- **Headers:** `Content-Type` (plus the browser-safelisted headers `Accept`,
  `Accept-Language`, `Content-Language`, which `starlette`'s `CORSMiddleware` always allows).
- **Exposed header:** `X-Request-ID` — read it from `response.headers` to correlate a client-side
  error report with a specific backend log line.
- **Production:** a `*` origin is rejected at startup when `APP_ENV=production`
  (`Settings._require_explicit_cors_in_production`) — you cannot accidentally ship a wildcard CORS
  policy; explicit origins are required.

**Why `POST /api/v1/lessons/pdf` and `POST /api/v1/lessons/video` work without a CORS preflight:**
a `multipart/form-data` POST is one of the browser's CORS-safelisted request types, so the browser
does not send an `OPTIONS` preflight for it at all — it only checks the response's
`Access-Control-Allow-Origin` header against the request's `Origin`.

**`POST /api/v1/lessons/youtube` is different:** its body is `application/json`, which is not a
CORS-safelisted content type, so the browser does send an `OPTIONS` preflight first. This already
works with no extra configuration, because `allow_methods` covers `POST` and `allow_headers`
covers `Content-Type` — the same configuration the PDF/video endpoints rely on for their own,
simpler case. No extra CORS configuration is needed for any of the four endpoints unless a future
request adds a custom header (e.g. `Authorization`) that isn't in `allow_headers` yet.

**Using a different frontend port** (e.g. `npm run dev:web -- --port 3001`): add the origin to
`CORS_ALLOWED_ORIGINS` in the repository-root `.env` (comma-separated for multiple origins, e.g.
`CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001`) and restart the API.

No CORS defect was found during this audit; the above documents the existing, already-correct
behaviour (verified by `services/api/tests/test_health.py::test_cors_allows_configured_origin` and
`::test_cors_ignores_unknown_origin`).

## Health and readiness

| Endpoint             | Purpose                                                                          |
| -------------------- | -------------------------------------------------------------------------------- |
| `GET /health`        | Unversioned; for deploy platforms and uptime checks that expect a fixed path.    |
| `GET /api/v1/health` | Same response, under the versioned API prefix — use this one from frontend code. |

```json
{ "status": "ok", "service": "api", "version": "0.1.0", "ai_mode": "mock" }
```

- `ai_mode` is the provider that will be tried first for new lessons (`gemini`, `openrouter`,
  `groq`, or `mock` when no provider is configured). Useful for a "demo mode" banner in local
  development without waiting for an actual lesson to be generated.
- **The health endpoint never calls an AI provider.** It only reads settings resolved at startup
  (`resolve_ai_mode`), so checking it costs nothing and has no latency dependency on any external
  service — safe to poll frequently from a frontend connectivity indicator.
- No separate "readiness" endpoint exists or is needed: the API has no database or external
  dependency to warm up before it can serve traffic, and health reflects the actual `ai_mode` an
  upload will use.

No health-endpoint defect was found during this audit.
