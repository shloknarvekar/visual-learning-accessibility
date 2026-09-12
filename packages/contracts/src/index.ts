import photosynthesisLessonJson from "../examples/photosynthesis.lesson.json";
import type { Lesson } from "./generated/lesson";

export type * from "./generated/lesson";

/**
 * Hand-written lesson that conforms to lesson.schema.json (checked by `npm run contracts:validate`).
 * Use it to build and test UI without running the API.
 */
export const photosynthesisExampleLesson = photosynthesisLessonJson as Lesson;
