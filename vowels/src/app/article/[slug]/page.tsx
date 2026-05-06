import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { marked } from "marked";

import { AdSlot } from "@/components/AdSlot";
import { ArticleCard } from "@/components/ArticleCard";
import { ArticleViewTracker } from "@/components/ArticleViewTracker";
import { SponsoredContentLabel } from "@/components/SponsoredContentLabel";
import { SwgCta } from "@/components/SwgCta";
import { getAllArticles, getArticleBySlug, getRelatedArticles } from "@/lib/articles";
import { getArticleHeroImage } from "@/lib/article-images";
import { articleJsonLd, articleMetadata } from "@/lib/seo";
import type { Article } from "@/types/article";

interface ArticlePageProps {
  params: {
    slug: string;
  };
}

export const dynamicParams = false;

export function generateStaticParams() {
  return getAllArticles().map((article) => ({ slug: article.slug }));
}

export function generateMetadata({ params }: ArticlePageProps): Metadata {
  const article = getArticleBySlug(params.slug);
  if (!article) return {};
  return articleMetadata(article);
}

function buildInlineCta(href: string, label: string): string {
  return `<aside class="my-8 rounded-[1.4rem] border border-black/10 bg-mist px-5 py-4"><p class="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">WIHY</p><a class="mt-2 inline-block text-base font-semibold text-newsroom underline" href="${href}" target="_blank" rel="noreferrer" data-wihy-cta="article-inline">${label}</a></aside>`;
}

function injectMidArticleCta(html: string, href: string, label: string): string {
  const cta = buildInlineCta(href, label);
  const h2Matches = [...html.matchAll(/<h2\b[^>]*>/gi)];

  if (h2Matches.length >= 3) {
    const insertIndex = h2Matches[2].index ?? html.length;
    return `${html.slice(0, insertIndex)}${cta}${html.slice(insertIndex)}`;
  }

  return `${html}${cta}`;
}

function getContinueLearning(article: Article, related: Article[]): Article[] {
  const allArticles = getAllArticles();
  const bySlug = new Map(allArticles.map((item) => [item.slug, item]));
  const selected: Article[] = [];
  const seen = new Set<string>();

  for (const slug of article.continueLearning ?? []) {
    const found = bySlug.get(slug);
    if (!found || found.slug === article.slug || seen.has(found.slug)) continue;
    selected.push(found);
    seen.add(found.slug);
  }

  for (const item of related) {
    if (seen.has(item.slug)) continue;
    selected.push(item);
    seen.add(item.slug);
    if (selected.length >= 4) break;
  }

  return selected.slice(0, 4);
}

export default function ArticlePage({ params }: ArticlePageProps) {
  const article = getArticleBySlug(params.slug);
  if (!article) notFound();

  const related = getRelatedArticles(article.slug, 5);
  const midArticleCtaHref = article.midArticleCtaHref || "https://wihy.ai";
  const midArticleCtaLabel = article.midArticleCtaLabel || "See how this applies to you -> WIHY";
  const html = injectMidArticleCta(marked.parse(article.body, { async: false }) as string, midArticleCtaHref, midArticleCtaLabel);
  const continueLearning = getContinueLearning(article, related);
  const jsonLd = articleJsonLd(article);
  const hero = getArticleHeroImage(article);

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <article className="news-card p-6">
        <ArticleViewTracker slug={article.slug} category={article.category} />
        <p className="text-xs font-bold uppercase tracking-[0.22em] text-newsroom">{article.category}</p>
        <h1 className="mt-3 font-serif text-5xl leading-[0.95] text-slate-950">{article.title}</h1>
        <p className="mt-4 max-w-3xl text-base leading-8 text-slate-700">{article.description}</p>
        <div className="mt-4 flex flex-wrap gap-3 text-sm uppercase tracking-[0.08em] text-slate-500">
          <span>{article.author}</span>
          <span>{new Date(article.publishedAt).toLocaleDateString()}</span>
          <span>{article.readingTime} min read</span>
          {article.isSponsored ? <SponsoredContentLabel /> : null}
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
          <span className="rounded-full bg-mist px-3 py-1">Evidence-based content</span>
          <span className="rounded-full bg-mist px-3 py-1">Sources reviewed</span>
          <span className="rounded-full bg-mist px-3 py-1">Educational purposes only</span>
        </div>

        {article.quickTake ? (
          <section className="mt-6 rounded-[1.5rem] border border-newsroom/20 bg-newsroom/5 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-newsroom">Quick Take</p>
            <p className="mt-3 text-base leading-8 text-slate-800">{article.quickTake}</p>
          </section>
        ) : null}

        {article.wihyData ? (
          <section className="mt-4 rounded-[1.5rem] border border-black/10 bg-sand p-5">
            <h2 className="font-serif text-3xl leading-none text-slate-950">From WIHY Data</h2>
            <div className="mt-4 grid gap-3 text-sm text-slate-700 md:grid-cols-3">
              <p>
                <span className="block text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Average intake trend</span>
                <span className="mt-1 block">{article.wihyData.intakeTrend ?? "Not specified"}</span>
              </p>
              <p>
                <span className="block text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Most common source</span>
                <span className="mt-1 block">{article.wihyData.mostCommonSource ?? "Not specified"}</span>
              </p>
              <p>
                <span className="block text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Common issue</span>
                <span className="mt-1 block">{article.wihyData.commonIssue ?? "Not specified"}</span>
              </p>
            </div>
          </section>
        ) : null}

        {/* Hero image */}
        <figure className="mt-6 overflow-hidden rounded-2xl">
          <img
            src={hero.src}
            alt={article.imageAlt ?? article.title}
            width={1200}
            height={630}
            className="h-64 w-full object-cover sm:h-80 lg:h-96"
            loading="eager"
          />
          {(article.imageCaption || hero.credit) && (
            <figcaption className="mt-2 px-1 text-xs text-slate-400">
              {article.imageCaption ?? ""}
              {hero.credit && (
                <span className="ml-1">Photo: {hero.credit}</span>
              )}
            </figcaption>
          )}
        </figure>

        <AdSlot slotName="Article Top Leaderboard" size="leaderboard" className="mt-6" />

        <SwgCta variant="inline" />

        <div
          className="article-prose prose prose-lg mt-6 max-w-none prose-headings:font-serif prose-headings:text-slate-950 prose-p:text-slate-800 prose-a:text-newsroom"
          dangerouslySetInnerHTML={{ __html: html }}
        />

        <AdSlot slotName="Article Mid-Content Rectangle" size="largerect" className="mt-6" />

        <AdSlot slotName="Article Pre-Source Native" size="infeed" className="mt-6" />

        {article.sourceLinks?.length ? (
          <section className="mt-8 rounded-[1.75rem] border-2 border-black bg-sand p-5">
            <h3 className="font-serif text-3xl text-slate-950">Sources</h3>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {article.sourceLinks.map((link) => (
                <li key={link}>
                  <a href={link} className="text-newsroom underline" target="_blank" rel="noreferrer">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {article.whatToDo?.length ? (
          <section className="mt-8 rounded-[1.75rem] border border-black/10 bg-white p-5">
            <h3 className="font-serif text-3xl text-slate-950">What to Do</h3>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-7 text-slate-700">
              {article.whatToDo.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <div
              className="article-prose mt-4 max-w-none"
              dangerouslySetInnerHTML={{ __html: buildInlineCta(midArticleCtaHref, midArticleCtaLabel) }}
            />
          </section>
        ) : null}

        <AdSlot slotName="Article Exit Zone Native" size="infeed" className="mt-8" />

        <section className="mt-8">
          <h3 className="font-serif text-4xl uppercase leading-none text-slate-950">Continue Learning</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {continueLearning.map((item) => (
              <ArticleCard key={item.slug} article={item} />
            ))}
          </div>
          <Link href={`/category/${article.category}`} className="mt-4 inline-block text-sm text-newsroom underline">
            Explore more in {article.category}
          </Link>
        </section>

        <AdSlot slotName="Article Post-Read Leaderboard" size="leaderboard" className="mt-8" />

        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      </article>

      <aside className="space-y-4">
        <SwgCta variant="sidebar" />
        <AdSlot slotName="Article Sidebar Rectangle" size="rectangle" sticky />
        <AdSlot slotName="Article Sidebar Half Page" size="halfpage" className="mt-4" />
      </aside>
    </div>
  );
}
