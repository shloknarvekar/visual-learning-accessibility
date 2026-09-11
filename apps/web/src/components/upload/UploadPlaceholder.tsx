const SUPPORTED_INPUTS = [
  { name: "YouTube link", description: "Recorded lectures and explainer videos." },
  { name: "PDF", description: "Lecture notes, handouts and textbook chapters." },
];

/** Placeholder for the upload workflow. Replace once the lesson API endpoints exist. */
export function UploadPlaceholder() {
  return (
    <section
      aria-labelledby="create-lesson-heading"
      className="rounded-lg border-2 border-dashed border-slate-300 bg-white p-6"
    >
      <h2 id="create-lesson-heading" className="text-2xl font-bold text-slate-900">
        Create a lesson
      </h2>
      <p className="mt-2 text-slate-700">
        Coming soon. You will be able to add one of these and get a structured visual lesson:
      </p>
      <ul className="mt-4 grid gap-3 sm:grid-cols-2">
        {SUPPORTED_INPUTS.map((input) => (
          <li key={input.name} className="rounded-md bg-slate-100 p-4">
            <p className="font-bold text-slate-900">{input.name}</p>
            <p className="mt-1 text-slate-700">{input.description}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
