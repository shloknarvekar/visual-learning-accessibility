import { ApiStatus } from "@/components/status/ApiStatus";

export function SiteFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-2 px-6 py-4 text-sm text-slate-700">
        <p>Hackathon prototype</p>
        <ApiStatus />
      </div>
    </footer>
  );
}
