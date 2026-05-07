"use client";

import { FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { fetchAiMode } from "@/lib/aiMode";
import type { AiModeResponse } from "@/types/aiMode";

interface AiModeResultsProps {
  initialQuery?: string;
}

type Turn = {
  id: string;
  query: string;
  loading: boolean;
  error: string | null;
  data: AiModeResponse | null;
};

function makeTurn(query: string): Turn {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    query,
    loading: true,
    error: null,
    data: null,
  };
}

export function AiModeResults({ initialQuery }: AiModeResultsProps) {
  const params = useSearchParams();
  const queryFromUrl = (params.get("q") || "").trim();
  const query = (initialQuery || queryFromUrl).trim();

  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const latestTurn = turns[turns.length - 1] || null;
  const topCitations = useMemo(() => (latestTurn?.data?.citations || []).slice(0, 5), [latestTurn]);

  const runTurn = async (nextQuery: string) => {
    const q = nextQuery.trim();
    if (!q) return;

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    const turn = makeTurn(q);
    setTurns((prev) => [...prev, turn]);

    // Keep context continuity by reusing latest cited articles when available.
    const contextArticles = (latestTurn?.data?.research?.articles || []).slice(0, 6).map((a) => ({
      title: a.title,
      abstract: a.abstract || undefined,
      journal: a.journal || undefined,
      year: a.year || undefined,
      pmcid: a.pmcid || undefined,
      pmid: a.pmid || undefined,
      doi: a.doi || undefined,
      url: a.url || undefined,
      study_type: a.study_type || undefined,
    }));

    try {
      const res = await fetchAiMode({
        query: q,
        limit: 8,
        include_related: true,
        use_gemini: true,
        articles: contextArticles.length > 0 ? contextArticles : undefined,
      });

      if (!ac.signal.aborted) {
        setTurns((prev) =>
          prev.map((t) => (t.id === turn.id ? { ...t, loading: false, data: res } : t))
        );
      }
    } catch (e: unknown) {
      if ((e as Error).name === "AbortError") return;
      const message = (e as Error).message || "AI mode failed.";
      setTurns((prev) =>
        prev.map((t) => (t.id === turn.id ? { ...t, loading: false, error: message, data: null } : t))
      );
    }
  };

  useEffect(() => {
    if (!query) {
      setTurns([]);
      setDraft("");
      return;
    }

    setTurns([]);
    setDraft("");
    runTurn(query);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  const submitFollowUp = (e: FormEvent) => {
    e.preventDefault();
    const q = draft.trim();
    if (!q) return;
    setDraft("");
    runTurn(q);
  };

  if (!query) return null;

  return (
    <section className="overflow-hidden rounded-[1.5rem] bg-transparent">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-black/10 px-5 py-4 md:px-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">AI Conversation</p>
          <h2 className="mt-1 font-serif text-2xl text-slate-950 md:text-3xl">{query}</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
          {latestTurn?.data?.answer?.verdict ? (
            <span className="rounded-full border border-black/10 bg-white px-3 py-1">{latestTurn.data.answer.verdict}</span>
          ) : null}
          {latestTurn?.data?.answer?.evidence_grade ? (
            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-emerald-700">{latestTurn.data.answer.evidence_grade}</span>
          ) : null}
          {latestTurn?.data?.llm?.used ? (
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-sky-700">Gemini Synthesized</span>
          ) : (
            <span className="rounded-full border border-black/10 bg-mist px-3 py-1">Rules + Retrieval</span>
          )}
        </div>
      </header>

      <div className="px-5 py-5 md:px-6">
        <div className="space-y-3">
          {turns.map((turn) => (
            <article key={turn.id} className="rounded-xl border border-black/10 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">You asked</p>
              <p className="mt-1 text-sm font-medium text-slate-900">{turn.query}</p>

              {turn.loading ? (
                <div className="mt-3 rounded-xl border border-black/10 bg-mist p-4 text-sm text-slate-700">Generating evidence-based answer...</div>
              ) : turn.error ? (
                <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{turn.error}</div>
              ) : !turn.data ? null : (
                <div className="mt-3 space-y-3">
                  {turn.data.answer?.summary ? (
                    <p className="text-sm leading-7 text-slate-800">{turn.data.answer.summary}</p>
                  ) : null}

                  {(turn.data.answer?.key_findings || []).length > 0 ? (
                    <section>
                      <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Key Findings</h3>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                        {turn.data.answer.key_findings.slice(0, 5).map((item, idx) => (
                          <li key={`${turn.id}-${idx}-${item.slice(0, 16)}`}>{item}</li>
                        ))}
                      </ul>
                    </section>
                  ) : null}

                  {turn.data.answer?.limitations ? (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                      <span className="font-semibold">Limits:</span> {turn.data.answer.limitations}
                    </div>
                  ) : null}

                  {(turn.data.follow_up_questions || []).length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {turn.data.follow_up_questions.slice(0, 3).map((q, i) => (
                        <button
                          key={`${turn.id}-follow-${i}`}
                          type="button"
                          onClick={() => runTurn(q)}
                          className="rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-700 transition hover:border-brand/40 hover:text-brand"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              )}
            </article>
          ))}
        </div>

        <form onSubmit={submitFollowUp} className="mt-4 search-sweep relative w-full px-1.5 py-1.5 shadow-sm">
          <input
            ref={inputRef}
            type="search"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask a follow-up question"
            aria-label="Ask a follow-up question"
            className="h-11 w-full rounded-full bg-transparent pl-5 pr-28 text-sm font-medium text-slate-900 outline-none placeholder:text-slate-500"
          />
          <button
            type="submit"
            className="absolute right-2 top-1/2 flex h-9 -translate-y-1/2 items-center justify-center rounded-full bg-brand px-4 text-[11px] font-bold uppercase tracking-[0.14em] text-white transition hover:-translate-y-[54%] hover:bg-black"
          >
            Ask
          </button>
        </form>

        {topCitations.length > 0 ? (
          <section className="mt-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Top Sources</h3>
            <ul className="mt-2 space-y-2 text-sm text-slate-700">
              {topCitations.map((c, idx) => (
                <li key={`${idx}-${c.title.slice(0, 20)}`}>
                  {c.url ? (
                    <a href={c.url} target="_blank" rel="noopener noreferrer" className="font-medium text-brand hover:underline">
                      {c.title}
                    </a>
                  ) : (
                    <span className="font-medium">{c.title}</span>
                  )}
                  <span className="ml-2 text-slate-500">{[c.journal, c.year].filter(Boolean).join(" · ")}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {latestTurn?.data?.safety?.note ? (
          <p className="mt-4 text-xs text-slate-500">{latestTurn.data.safety.note}</p>
        ) : null}
      </div>
    </section>
  );
}
