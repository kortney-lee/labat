import Link from "next/link";

import { CategoryNav } from "@/components/CategoryNav";
import { SearchBar } from "@/components/SearchBar";

export function Header() {
  return (
    <header className="news-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3 font-semibold tracking-wide text-newsroom">
          <img src="/vowels-logo.svg" alt="Vowels" className="h-10 w-10 rounded-xl" />
          <span className="text-lg uppercase">Vowels Newsroom</span>
        </Link>
        <SearchBar />
      </div>
      <CategoryNav />
    </header>
  );
}
