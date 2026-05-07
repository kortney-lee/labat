"use client";

import Image from "next/image";
import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { trackEvent } from "@/lib/analytics";

interface SearchHeroProps {
  initialQuery?: string;
}

export function SearchHero({ initialQuery = "" }: SearchHeroProps) {
  const router = useRouter();
  const [q, setQ] = useState(initialQuery);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setQ(initialQuery);
  }, [initialQuery]);

  const submit = (raw?: string) => {
    const query = (raw ?? q).trim();
    if (!query) {
      router.push("/");
      return;
    }
    trackEvent({ name: "search_usage", params: { query } });
    router.push(`/?q=${encodeURIComponent(query)}#results`);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  const onClear = () => {
    setQ("");
    inputRef.current?.focus();
    if (initialQuery) router.push("/");
  };

  return (
    <section className="reveal flex flex-col items-center px-4 pb-5 pt-5 md:pb-6 md:pt-10">
      <a href="/" aria-label="Vowels home" className="mb-6 block">
        <Image
          src="/vowels-lockup.png"
          alt="Vowels"
          width={420}
          height={120}
          priority
          className="h-auto w-[220px] md:w-[420px]"
        />
      </a>

      <p className="mb-4 text-center text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500 md:text-xs md:tracking-[0.22em]">
        A research search engine for nutrition &amp; health
      </p>

      <form onSubmit={onSubmit} className="search-sweep relative w-full max-w-3xl px-1.5 py-1.5 shadow-sm">
        <input
          ref={inputRef}
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Search peer-reviewed research"
          aria-label="Search peer-reviewed research"
          maxLength={500}
          enterKeyHint="search"
          className="h-12 w-full rounded-full bg-transparent pl-6 pr-32 text-base font-medium text-slate-900 outline-none placeholder:text-slate-500 md:h-14 md:text-lg"
        />

        <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1.5 rounded-full bg-white/95 p-1">
          {q ? (
            <button
              type="button"
              onClick={onClear}
              aria-label="Clear search"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition hover:bg-slate-200 hover:text-slate-700"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden>
                <path d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
              </svg>
            </button>
          ) : null}

          <button
            type="submit"
            aria-label="Search"
            className="flex h-10 items-center justify-center gap-2 rounded-full bg-brand px-5 text-xs font-bold uppercase tracking-[0.14em] text-white transition hover:-translate-y-0.5 hover:bg-black md:h-11 md:px-6"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden>
              <path d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z" />
            </svg>
            Search
          </button>
        </div>
      </form>

      <div className="mt-4 flex w-full max-w-3xl items-center gap-2 overflow-x-auto pb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 md:flex-wrap md:justify-center md:overflow-visible md:pb-0">
        <span className="shrink-0">Try:</span>
        {["intermittent fasting", "high protein", "blood sugar", "fiber", "ultra processed food"].map((seed) => (
          <button
            key={seed}
            type="button"
            onClick={() => {
              setQ(seed);
              submit(seed);
            }}
            className="shrink-0 rounded-full border border-black/10 bg-white px-3 py-1 text-slate-700 transition hover:border-brand/40 hover:text-brand"
          >
            {seed}
          </button>
        ))}
      </div>
    </section>
  );
}
