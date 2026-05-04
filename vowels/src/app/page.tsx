import Link from "next/link";

import { AdSlot } from "@/components/AdSlot";
import { ArticleCard } from "@/components/ArticleCard";
import { DataInsightCard } from "@/components/DataInsightCard";
import { FeaturedArticle } from "@/components/FeaturedArticle";
import { SwgCta } from "@/components/SwgCta";
import { getAllArticles, searchArticles } from "@/lib/articles";
import { weeklyInsights } from "@/lib/wihyData";

export const dynamic = "force-static";

interface HomePageProps {
  searchParams?: {
    q?: string;
  };
}

const subjectSeeds = [
  "high protein",
  "meal prep",
  "blood sugar",
  "fiber",
  "processed food",
  "sodium",
  "kids nutrition",
  "weight management",
];

export default function HomePage({ searchParams }: HomePageProps) {
  const query = searchParams?.q?.trim() || "";
  const all = getAllArticles();
  const filtered = query ? searchArticles(query) : all;
  const featured = filtered[0] || all[0];
  const feed = filtered.slice(1, 7);
  const highlight = filtered[1] || all[1];
  const tags = Array.from(new Set((featured?.tags || []).concat(feed.flatMap((item) => item.tags)).slice(0, 8)));

  return (
    <div className="space-y-8 pb-8">
      <section className="reveal news-card relative overflow-hidden px-6 py-8 md:px-8">
        <div className="absolute -right-12 -top-20 h-44 w-44 rounded-full bg-brand/20 blur-3xl" />
        <div className="relative space-y-6">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Today in Nutrition Education</p>
            <h1 className="mt-3 font-serif text-4xl leading-tight text-slate-950 md:text-5xl">The new standard for understanding nutrition.</h1>
            <p className="mt-4 text-base leading-8 text-slate-700">Clear, evidence-based insights to help you make better decisions about food, health, and daily habits.</p>
          </div>
        </div>
      </section>

      {query ? (
        <section className="news-card px-5 py-4 md:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-700">
              Search results for <span className="font-semibold text-slate-900">&quot;{query}&quot;</span>: {filtered.length}
            </p>
            <Link href="/" className="text-xs font-semibold uppercase tracking-[0.12em] text-brand hover:underline">
              Clear search
            </Link>
          </div>
        </section>
      ) : null}

      <section className="news-card p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-serif text-3xl text-slate-950">High-Intent Subjects</h2>
          <Link href="/subjects" className="text-xs font-semibold uppercase tracking-[0.12em] text-brand hover:underline">
            View all subjects
          </Link>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {subjectSeeds.map((seed) => (
            <Link
              key={seed}
              href={`/?q=${encodeURIComponent(seed)}`}
              className="rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-700 transition hover:border-brand/40 hover:text-brand"
            >
              {seed}
            </Link>
          ))}
        </div>
      </section>

      <AdSlot slotName="Homepage Leaderboard" size="leaderboard" className="w-full" />

      <section className="reveal reveal-delay-1 grid gap-5 xl:grid-cols-[1.4fr_0.85fr]">
        <div className="space-y-5">
          {featured ? <FeaturedArticle article={featured} /> : null}

          <section className="news-card overflow-hidden">
            <div className="flex flex-wrap items-center gap-3 border-b border-black/10 px-5 py-4 md:px-6">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand">Explore Topics</p>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <span key={tag} className="rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-medium text-slate-600">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <section className="news-card p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand">Editor&apos;s Note</p>
            <h2 className="mt-3 font-serif text-3xl leading-[0.95] text-slate-950">Truth over trends. Context over noise.</h2>
            <p className="mt-4 text-sm leading-7 text-slate-700">
              We break down nutrition, health, and food systems into clear explanations you can actually use in real life—grounded in evidence, not opinion.
            </p>
            <Link
              href="/editorial-policy"
              className="mt-5 inline-flex rounded-full border border-black/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-700 transition hover:border-brand hover:text-brand"
            >
              View Editorial Standards
            </Link>
          </section>

          {highlight ? (
            <section className="news-card p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">In Focus</p>
              <h3 className="mt-3 font-serif text-3xl leading-[0.95] text-slate-950">
                <Link href={`/article/${highlight.slug}`}>{highlight.title}</Link>
              </h3>
              <p className="mt-3 text-sm leading-7 text-slate-700">{highlight.description}</p>
            </section>
          ) : null}

          <AdSlot slotName="Sidebar Rectangle" size="rectangle" />
          <AdSlot slotName="Sidebar Half Page" size="halfpage" className="mt-4" sticky />
        </aside>
      </section>

      <section className="reveal reveal-delay-2 grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-serif text-4xl leading-none text-slate-950">Latest Insights</h2>
          </div>

          {filtered.length ? (
            <div className="grid gap-4 md:grid-cols-2">
              {feed.slice(0, 2).map((article) => (
                <ArticleCard key={article.slug} article={article} />
              ))}
              <div className="md:col-span-2">
                <AdSlot slotName="In-Feed Content Ad" size="infeed" />
              </div>
              {feed.slice(2).map((article) => (
                <ArticleCard key={article.slug} article={article} />
              ))}
            </div>
          ) : (
            <section className="news-card p-6">
              <h3 className="font-serif text-2xl text-slate-950">No matching stories yet</h3>
              <p className="mt-2 text-sm text-slate-700">Try a broader term like protein, fiber, blood sugar, or meal prep.</p>
            </section>
          )}

          <section className="news-card p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-serif text-4xl leading-none text-slate-950">From the Data</h3>
              <span className="rounded-full bg-mist px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">Weekly pulse</span>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {weeklyInsights.map((insight) => (
                <DataInsightCard key={insight.label} insight={insight} />
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <SwgCta variant="sidebar" />
          <AdSlot slotName="Content Partner Rectangle" size="rectangle" />
          <section className="news-card p-5">
            <h3 className="font-serif text-2xl text-slate-950">Always Ask Why</h3>
            <ul className="mt-3 space-y-2 text-sm leading-7 text-slate-700">
              <li>Why are processed foods the default in low-cost carts?</li>
              <li>Why are labels designed for marketing over clarity?</li>
              <li>Why is healthy access still unequal by neighborhood?</li>
            </ul>
          </section>
        </div>
      </section>

      {/* Mobile anchor banner — fixed bottom, hides on md+ where sidebar handles monetization */}
      <div className="fixed bottom-0 left-0 right-0 z-30 md:hidden">
        <AdSlot slotName="Mobile Anchor Banner" size="mobilebanner" className="rounded-none border-t border-black/10" />
      </div>
    </div>
  );
}
