"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { SearchBar } from "@/components/SearchBar";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/subjects", label: "Subjects" },
  { href: "/category/nutrition-education", label: "Coverage" },
  { href: "/editorial-policy", label: "Editorial Policy" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export function Header() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setIsCollapsed(window.scrollY > 72);
    };

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={`space-y-3 transition-all duration-300 ${isCollapsed ? "space-y-2" : "space-y-3"}`}>
      <div className="flex w-full flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Link href="/" className={`inline-flex items-center origin-left transition-transform duration-300 ${isCollapsed ? "scale-90" : "scale-100"}`}>
          <Image src="/vowels-lockup.png" alt="Vowels" width={180} height={48} priority />
        </Link>

        <div className="w-full max-w-[360px]">
          <SearchBar compact />
        </div>
      </div>

      <nav
        className={`overflow-hidden border-black/10 text-sm transition-all duration-300 ${
          isCollapsed ? "max-h-0 border-transparent pt-0 opacity-0" : "max-h-24 border-t pt-3 opacity-100"
        }`}
        aria-label="Main Navigation"
      >
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {navLinks.map((link, idx) => (
            <div key={link.label} className="flex items-center gap-4">
              <Link href={link.href} className="font-medium text-slate-700 transition hover:text-brand">
                {link.label}
              </Link>
              {idx < navLinks.length - 1 && <span className="hidden text-slate-300 sm:inline">|</span>}
            </div>
          ))}
        </div>
      </nav>
    </header>
  );
}
