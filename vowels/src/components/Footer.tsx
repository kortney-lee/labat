import Image from "next/image";
import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-black/10 bg-white/75 py-10 backdrop-blur">
      <div className="mx-auto flex max-w-[1480px] flex-wrap items-center justify-between gap-4 px-4 text-sm text-slate-600 md:px-8">
        <div className="flex items-center gap-3">
          <Image src="/vowels-lockup.png" alt="Vowels" width={140} height={38} />
          <p className="text-slate-600">Evidence-based nutrition education powered by data.</p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <Link href="/subjects" className="hover:text-brand">Subjects</Link>
          <Link href="/privacy" className="hover:text-brand">Privacy</Link>
          <Link href="/terms" className="hover:text-brand">Terms</Link>
          <Link href="/editorial-policy" className="hover:text-brand">Editorial Policy</Link>
          <Link href="/health-disclaimer" className="hover:text-brand">Health Disclaimer</Link>
          <a href="https://www.instagram.com/vowels_org/" target="_blank" rel="noopener noreferrer" aria-label="Instagram" className="hover:text-brand">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>
          </a>
          <a href="https://www.facebook.com/Vowels.Org/" target="_blank" rel="noopener noreferrer" aria-label="Facebook" className="hover:text-brand">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>
          </a>
        </div>
      </div>
    </footer>
  );
}
