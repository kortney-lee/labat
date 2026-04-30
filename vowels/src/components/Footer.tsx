import Image from "next/image";
import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-black/10 bg-white/75 py-10 backdrop-blur">
      <div className="mx-auto flex max-w-[1480px] flex-wrap items-center justify-between gap-4 px-4 text-sm text-slate-600 md:px-8">
        <div className="flex items-center gap-3">
          <Image src="/vowels-brand.png" alt="Vowels cap mark" width={28} height={28} className="h-7 w-7 object-contain" />
          <p>
            <span className="font-serif text-2xl leading-none text-brand">Vowels</span> Evidence-based nutrition education powered by data.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <Link href="/privacy" className="hover:text-brand">Privacy</Link>
          <Link href="/terms" className="hover:text-brand">Terms</Link>
          <Link href="/editorial-policy" className="hover:text-brand">Editorial Policy</Link>
          <Link href="/health-disclaimer" className="hover:text-brand">Health Disclaimer</Link>
        </div>
      </div>
    </footer>
  );
}
