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
    <form onSubmit={onSubmit} className="flex w-full max-w-sm items-center gap-2 rounded-full border border-sky-200 bg-white px-3 py-2">
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search headlines"
        className="w-full bg-transparent text-sm text-slate-700 outline-none"
      />
      <button type="submit" className="text-xs font-semibold uppercase tracking-wide text-newsroom">
        Search
      </button>
    </form>
  );
}
