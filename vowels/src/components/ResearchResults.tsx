"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

interface ResearchArticle {
  id?: string;
  pmcid?: string;
  pmid?: string;
  title: string;
  authors?: string | string[];
  authorCount?: number;
  journal?: string;
  publishedDate?: string;
  publicationYear?: number;
  abstract?: string;
  studyType?: string;
  study_type?: string;
  evidenceLevel?: string;
  evidence_level?: string;
  relevanceScore?: number;
  relevance_score?: number;
  rank?: number;
  fullTextAvailable?: boolean;
  open_access?: boolean;
  links?: {
    pmcWebsite?: string;
    pubmedLink?: string;
    pdfDownload?: string | null;
    doi?: string;
  };
}

interface SearchResponse {
  success?: boolean;
  keyword?: string;
  totalFound?: number;
  articles?: ResearchArticle[];
  results?: ResearchArticle[];
  error?: string;
}

const STUDY_COLORS: Record<string, string> = {
  randomized_controlled_trial: "bg-rose-50 text-rose-700 border-rose-200",
  meta_analysis: "bg-violet-50 text-violet-700 border-violet-200",
  systematic_review: "bg-sky-50 text-sky-700 border-sky-200",
  cohort_study: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const EVIDENCE_COLORS: Record<string, string> = {
  high: "bg-emerald-50 text-emerald-700 border-emerald-200",
  moderate: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-orange-50 text-orange-700 border-orange-200",
  very_low: "bg-rose-50 text-rose-700 border-rose-200",
};

function studyTypeOf(a: ResearchArticle): string | undefined {
  return (a.studyType || a.study_type || "").toLowerCase() || undefined;
}

function evidenceLevelOf(a: ResearchArticle): string | undefined {
  return (a.evidenceLevel || a.evidence_level || "").toLowerCase() || undefined;
}

function authorsOf(a: ResearchArticle): string {
  if (!a.authors) return "";
  if (Array.isArray(a.authors)) {
    const head = a.authors.slice(0, 3).join(", ");
    return a.authors.length > 3 ? `${head}, et al.` : head;
  }
  return a.authors;
}

function articleHref(a: ResearchArticle): string | undefined {
  return (
    a.links?.pubmedLink ||
    a.links?.pmcWebsite ||
    (a.pmcid ? `https://www.ncbi.nlm.nih.gov/pmc/articles/${a.pmcid}/` : undefined) ||
    (a.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${a.pmid}/` : undefined) ||
    a.links?.doi
  );
}

function relevanceOf(a: ResearchArticle, idx: number): number {
  const raw = a.relevanceScore ?? a.relevance_score;
  if (typeof raw === "number") return raw > 1 ? raw / 100 : raw;
  return Math.max(0.5, 0.95 - idx * 0.03);
}

function formatLabel(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function decodeEntities(text: string): string {
  return text
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, dec) => String.fromCharCode(parseInt(dec, 10)))
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'");
}

function abstractExcerpt(text: string | undefined, max = 320): string {
  if (!text) return "";
  const decoded = decodeEntities(text).trim();
  if (decoded.length <= max) return decoded;
  return decoded.slice(0, max).replace(/\s+\S*$/, "") + "…";
}

interface ResearchResultsProps {
  initialQuery?: string;
}

export function ResearchResults({ initialQuery }: ResearchResultsProps) {
  const params = useSearchParams();
  const queryFromUrl = (params.get("q") || "").trim();
  const query = (initialQuery || queryFromUrl).trim();

  const [articles, setArticles] = useState<ResearchArticle[]>([]);
  const [totalFound, setTotalFound] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!query) {
      setArticles([]);
      setTotalFound(0);
      setError(null);
      setLoading(false);
      return;
    }

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError(null);

    fetch(`/api/research/search?q=${encodeURIComponent(query)}&limit=20`, { signal: ac.signal })
      .then(async (r) => {
        const data = (await r.json()) as SearchResponse;
        if (!r.ok || data.success === false) {
          throw new Error(data.error || `Research service returned ${r.status}`);
        }
        const list = data.articles || data.results || [];
        setArticles(list);
        setTotalFound(typeof data.totalFound === "number" ? data.totalFound : list.length);
      })
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        setError((e as Error).message || "Search failed.");
        setArticles([]);
        setTotalFound(0);
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });

    return () => ac.abort();
  }, [query]);

  const stats = useMemo(() => {
    const high = articles.filter((a) => evidenceLevelOf(a) === "high").length;
    const fullText = articles.filter((a) => a.fullTextAvailable ?? a.open_access).length;
    return { count: articles.length, high, fullText };
  }, [articles]);

  if (!query) return null;

  return (
    <section className="overflow-hidden rounded-[1.5rem] bg-transparent">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-black/10 px-5 py-4 md:px-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Research Results</p>
          <h2 className="mt-1 font-serif text-2xl text-slate-950 md:text-3xl">
            “{query}”
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
          <span className="rounded-full border border-black/10 bg-white px-3 py-1">{loading ? "Searching…" : `${totalFound || stats.count} studies`}</span>
          {stats.high > 0 ? (
            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-emerald-700">
              {stats.high} high evidence
            </span>
          ) : null}
          {stats.fullText > 0 ? (
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-sky-700">
              {stats.fullText} full text
            </span>
          ) : null}
        </div>
      </header>

      <div className="px-5 py-5 md:px-6">
        {loading ? (
          <ul className="space-y-3" aria-busy="true">
            {Array.from({ length: 4 }).map((_, i) => (
              <li key={i} className="rounded-xl border border-black/10 bg-white p-5">
                <div className="h-4 w-3/4 animate-pulse rounded bg-slate-200" />
                <div className="mt-3 h-3 w-1/2 animate-pulse rounded bg-slate-200" />
                <div className="mt-4 h-3 w-full animate-pulse rounded bg-slate-100" />
                <div className="mt-2 h-3 w-5/6 animate-pulse rounded bg-slate-100" />
              </li>
            ))}
          </ul>
        ) : error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
            We couldn’t reach the research index right now. {error}
          </div>
        ) : articles.length === 0 ? (
          <div className="rounded-xl border border-black/10 bg-white p-6 text-sm text-slate-700">
            No published studies matched <span className="font-semibold text-slate-900">“{query}”</span>. Try a broader term.
          </div>
        ) : (
          <ol className="space-y-3">
            {articles.map((a, idx) => {
              const id = a.id || a.pmcid || a.pmid || String(idx);
              const href = articleHref(a);
              const study = studyTypeOf(a);
              const evidence = evidenceLevelOf(a);
              const fullText = a.fullTextAvailable ?? a.open_access;
              const year = a.publicationYear || (a.publishedDate ? new Date(a.publishedDate).getFullYear() : undefined);
              const isOpen = !!expanded[id];
              const fullAbstract = a.abstract ? decodeEntities(a.abstract) : "";
              const excerpt = abstractExcerpt(a.abstract);
              const showToggle = fullAbstract.length > excerpt.length;

              return (
                <li
                  key={id}
                  className="rounded-xl border border-black/10 bg-white p-5 transition hover:border-brand/40 hover:shadow-sm"
                >
                  <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                    <span className="rounded-full border border-black/10 bg-mist px-2.5 py-0.5">#{a.rank ?? idx + 1}</span>
                    {study ? (
                      <span className={`rounded-full border px-2.5 py-0.5 ${STUDY_COLORS[study] || "border-black/10 bg-white text-slate-700"}`}>
                        {formatLabel(study)}
                      </span>
                    ) : null}
                    {evidence ? (
                      <span className={`rounded-full border px-2.5 py-0.5 ${EVIDENCE_COLORS[evidence] || "border-black/10 bg-white text-slate-700"}`}>
                        {formatLabel(evidence)} evidence
                      </span>
                    ) : null}
                    {fullText ? (
                      <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-sky-700">
                        Full text
                      </span>
                    ) : null}
                    <span className="ml-auto text-slate-500">
                      {(relevanceOf(a, idx) * 100).toFixed(0)}% relevance
                    </span>
                  </div>

                  <h3 className="mt-3 font-serif text-xl leading-snug text-slate-950">
                    {href ? (
                      <a href={href} target="_blank" rel="noopener noreferrer" className="hover:text-brand">
                        {a.title}
                      </a>
                    ) : (
                      a.title
                    )}
                  </h3>

                  <p className="mt-1 text-xs text-slate-600">
                    {[authorsOf(a), a.journal, year].filter(Boolean).join(" · ")}
                  </p>

                  {a.abstract ? (
                    <p className="mt-3 text-sm leading-7 text-slate-700">
                      {isOpen ? fullAbstract : excerpt}
                      {showToggle ? (
                        <button
                          type="button"
                          onClick={() => setExpanded((m) => ({ ...m, [id]: !m[id] }))}
                          className="ml-2 text-xs font-semibold uppercase tracking-[0.12em] text-brand hover:underline"
                        >
                          {isOpen ? "Show less" : "Read more"}
                        </button>
                      ) : null}
                    </p>
                  ) : null}

                  <div className="mt-4 flex flex-wrap gap-3 text-xs font-semibold uppercase tracking-[0.12em]">
                    {a.links?.pubmedLink ? (
                      <a href={a.links.pubmedLink} target="_blank" rel="noopener noreferrer" className="text-brand hover:underline">
                        PubMed
                      </a>
                    ) : null}
                    {a.links?.pmcWebsite ? (
                      <a href={a.links.pmcWebsite} target="_blank" rel="noopener noreferrer" className="text-brand hover:underline">
                        PMC
                      </a>
                    ) : null}
                    {a.links?.pdfDownload ? (
                      <a href={a.links.pdfDownload} target="_blank" rel="noopener noreferrer" className="text-brand hover:underline">
                        PDF
                      </a>
                    ) : null}
                    {a.links?.doi ? (
                      <a href={a.links.doi} target="_blank" rel="noopener noreferrer" className="text-slate-600 hover:text-brand hover:underline">
                        DOI
                      </a>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
