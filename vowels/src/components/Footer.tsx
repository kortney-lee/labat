import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-10 border-t border-sky-300 py-8 text-sm text-slate-600">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4">
        <p>Vowels.org - Evidence-first nutrition newsroom.</p>
        <div className="flex flex-wrap items-center gap-4">
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
          <Link href="/editorial-policy">Editorial Policy</Link>
          <Link href="/health-disclaimer">Health Disclaimer</Link>
        </div>
      </div>
    </footer>
  );
}
