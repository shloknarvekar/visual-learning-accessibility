import { photosynthesisExampleLesson as lesson, type Section } from "@visual-learning/contracts";

// Typed against the contract: adding a section type to the schema fails the build until it is labelled here.
const SECTION_TYPE_LABELS: Record<Section["type"], string> = {
  concept: "Key concept",
  explanation: "Explanation",
  process: "Process",
  comparison: "Comparison",
  timeline: "Timeline",
  example: "Example",
  concept_map: "Concept map",
  diagram: "Diagram",
  chart: "Chart",
};

/** Outline of the hand-written example lesson from @visual-learning/contracts. */
export function SampleLessonOutline() {
  return (
    <section aria-labelledby="sample-lesson-heading" className="rounded-lg bg-white p-6 shadow-sm">
      <p className="text-sm font-bold uppercase tracking-wide text-slate-600">
        Sample lesson (example data)
      </p>
      <h2 id="sample-lesson-heading" className="mt-1 text-2xl font-bold text-slate-900">
        {lesson.title}
      </h2>
      <p className="mt-2 text-slate-700">{lesson.overview}</p>
      <ol className="mt-4 space-y-2">
        {lesson.sections.map((section) => (
          <li key={section.id} className="flex flex-wrap items-baseline gap-2">
            <span className="rounded bg-blue-100 px-2 py-0.5 text-sm font-bold text-blue-900">
              {SECTION_TYPE_LABELS[section.type]}
            </span>
            <span className="text-slate-900">{section.title}</span>
          </li>
        ))}
      </ol>
      <p className="mt-4 text-slate-700">{lesson.quiz.length} quiz questions</p>
    </section>
  );
}
