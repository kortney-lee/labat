import Link from "next/link";

import { SearchBar } from "@/components/SearchBar";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/category/nutrition-education", label: "Coverage" },
  { href: "/editorial-policy", label: "Editorial Policy" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export function Header() {
  return (
    <header className="space-y-3">
      <div className="w-full">
        <SearchBar />
      </div>

      <nav className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-black/10 pt-3 text-sm" aria-label="Main Navigation">
        {navLinks.map((link, idx) => (
          <div key={link.label} className="flex items-center gap-4">
            <Link href={link.href} className="font-medium text-slate-700 transition hover:text-brand">
              {link.label}
            </Link>
            {idx < navLinks.length - 1 && <span className="hidden text-slate-300 sm:inline">|</span>}
          </div>
        ))}
      </nav>
    </header>
  );
}
