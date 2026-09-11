# Product and MVP scope

## Problem

Most educational content is delivered hearing-first: recorded lectures, YouTube explainers, spoken
explanations, and notes written to accompany speech. Captions and transcripts make the words
available, but they keep the original linear, speech-shaped structure. Students still have to
extract the concepts, steps and relationships themselves from a long stream of text.

Existing tools already offer captions, transcripts, summaries, mind maps, quizzes and some
sign-language-oriented accessibility. Our focus is different.

## What we are building

A system that **transforms educational content into a visual-first learning experience**. It keeps
the academic content and reorganises it into:

- concise, literal explanations
- key concepts and definitions
- step-by-step processes
- relationships between ideas (concept maps)
- comparisons (tables)
- timelines
- charts, when the source contains real data
- worked examples
- checkpoint questions

We are **not** simplifying ("dumbing down") the material. The same content is represented with
clearer structure and multiple representations.

## Target users

**Primary:** Deaf and hard-of-hearing students in higher education (18 and over) who learn from
lecture videos and written course material.

> **Why 18+ for the prototype:** the Gemini API terms, which cover our free AI tier, require users to
> be 18 or older and do not allow apps directed at people under 18. Secondary-school students are a
> natural future audience, but only with an AI setup whose terms allow it.

We do not assume all Deaf learners learn the same way, or that Deaf learners are inherently "visual
learners". Language backgrounds vary widely (for example sign language as a first language, spoken
language with hearing technology, late deafness), and so do reading preferences. The product offers
structured, multi-representation content that learners can use in the way that suits them.

**Secondary:** any student who benefits from structured, visual study material, such as second
language learners or students reviewing for exams.

## MVP (36-hour hackathon)

### Inputs

1. **YouTube URL:** lecture or explainer video with an available transcript.
2. **PDF:** lecture notes, handouts or textbook chapters with extractable text.

### Output

A **structured visual lesson** (see `packages/contracts/lesson.schema.json`) containing:

- title and overview
- ordered sections, each rendered according to its type (concept, explanation, process, comparison,
  concept map, example, and others)
- quiz questions linked back to the sections they test
- references to source pages or timestamps where practical

### MVP user journey

1. Student opens the web app.
2. Student pastes a YouTube link or uploads a PDF.
3. The app shows progress while the lesson is generated.
4. Student studies the lesson: overview, sections, visuals.
5. Student answers checkpoint questions and sees explanations.

### Demo success criteria

- One YouTube lecture and one PDF each produce a complete, readable lesson.
- At least one process and one concept map render as visuals, not just text.
- Every section can be traced back to a page or timestamp.
- The lesson page works with keyboard only and meets WCAG 2.2 AA contrast.

## Not in the MVP

Authentication and accounts, saved libraries, teacher dashboards, curriculum standards alignment,
sign-language avatar or video generation, mobile apps, real-time collaboration, analytics, LMS
integration, payments, and formats beyond YouTube and PDF (slides, audio files, live classes).

## Future scope

- Sign-language video integration for key terms (human-produced or verified).
- More inputs: slide decks, audio recordings, web articles, live lectures.
- Learner controls: reading-level options while keeping technical terms, glossary, and choice of
  representation.
- Teacher review and editing of generated lessons before sharing.
- Spaced-repetition review built from quiz results.
- Persistent accounts and lesson libraries.

## Research to validate (Person 4)

- Evidence on barriers Deaf and hard-of-hearing students face with lecture-based content, from
  published research and advocacy organisations. Cite sources.
- How current tools (caption, transcript, summary and mind-map products) fall short for this
  audience.
- Feedback from Deaf or hard-of-hearing students or educators on the lesson format, if reachable
  during the hackathon.
- Which representations help most for which content types (processes, comparisons, relationships).
