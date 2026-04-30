"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { trackEvent } from "@/lib/analytics";

export function SearchBar() {
  const router = useRouter();
  const [q, setQ] = useState("");

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const query = q.trim();
    const next = query ? `/?q=${encodeURIComponent(query)}` : "/";
    trackEvent({ name: "search_usage", params: { query } });
    router.push(next);
  };

  return (
    <form onSubmit={onSubmit} className="search-sweep flex w-full items-center gap-2 px-4 py-2.5 shadow-sm">
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search nutrition topics"
        className="w-full bg-transparent text-sm font-medium text-slate-900 outline-none placeholder:text-slate-500"
      />
      <button type="submit" className="rounded-full bg-brand px-4 py-2 text-xs font-bold uppercase tracking-[0.14em] text-white transition hover:-translate-y-0.5 hover:bg-black">
        Search
      </button>
    </form>
  );
}
