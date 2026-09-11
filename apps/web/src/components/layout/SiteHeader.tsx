import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex w-full max-w-5xl items-center px-6 py-4">
        <Link href="/" className="text-xl font-bold text-slate-900">
          Visual Learning
        </Link>
      </div>
    </header>
  );
}
