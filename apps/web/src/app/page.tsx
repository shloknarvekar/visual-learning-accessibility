import { SampleLessonOutline } from "@/components/lesson/SampleLessonOutline";
import { UploadPlaceholder } from "@/components/upload/UploadPlaceholder";

export default function HomePage() {
  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-12">
      <section aria-labelledby="intro-heading">
        <h1 id="intro-heading" className="text-4xl font-bold tracking-tight text-slate-900">
          Turn lectures and notes into visual lessons
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-700">
          Add a YouTube lecture or a PDF. The same academic content is reorganised into clear
          explanations, diagrams, concept maps and quizzes.
        </p>
      </section>

      <div className="mt-10 grid gap-8">
        <UploadPlaceholder />
        <SampleLessonOutline />
      </div>
    </div>
  );
}
