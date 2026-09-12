# VisuaLearn Frontend

Frontend-only student experience for VisuaLearn. The app keeps the cinematic landing page and restores the perspective card/image-stream animation while adding Motion animations across Create, Processing, Lesson, Practice and Result.

## Run
```bash
npm install
npm run dev
```

## Frontend/backend connection
Copy `.env.example` to `.env.local` and set:
```text
NEXT_PUBLIC_LESSON_API_URL=<your already-deployed lesson endpoint>
```
The frontend then sends a `multipart/form-data` POST containing `source` plus either `url` or `file` to that endpoint. The response is treated as `{ lesson?, mode?, message? }`; the UI uses `mode` to show LIVE / FALLBACK / DEMO. The UI remains demo-safe when the variable is empty.

If your existing backend uses a different request/response shape, change only `src/lib/api.ts` and the lesson mapping stays isolated from the presentation layer.

## Frontend responsibilities
- landing/home
- PDF upload and drag & drop
- loading/processing states
- error states
- lesson layout and sidebar navigation
- quiz and result UI
- responsive/mobile navigation
- keyboard focus and contrast controls
- live/fallback/demo status
- frontend API adapter only

No backend, OCR, transcription, LLM, database, or API-server code is added.

## Animation
- Landing mouse-scrub video with a more reliable seek queue and subtle pointer parallax.
- Restored perspective image-stream/card corridor directly below the hero.
- Motion-based transitions, staggered reveals, hover movement and processing shimmer across the rest of the product.
- `prefers-reduced-motion` is respected.


## Visual learning showcase
The post-hero landing experience uses Motion-powered fan cards, an interactive concept orbit, a learning-loop timeline, and a practice preview. These are frontend-only components and keep Person 3's visualization integration boundary intact.
