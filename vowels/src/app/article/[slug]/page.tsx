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

export default function ArticlePage({ params }: ArticlePageProps) {
  const article = getArticleBySlug(params.slug);
  if (!article) notFound();

  const related = getRelatedArticles(article.slug, 5);
  const html = marked.parse(article.body, { async: false }) as string;
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

        <div
          className="prose prose-lg mt-6 max-w-none prose-headings:font-serif prose-headings:text-slate-950 prose-p:text-slate-800 prose-a:text-newsroom"
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

        <SwgCta variant="inline" />

        <AdSlot slotName="Article Exit Zone Native" size="infeed" className="mt-8" />

        <section className="mt-8">
          <h3 className="font-serif text-4xl uppercase leading-none text-slate-950">Related Articles</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {related.slice(0, 4).map((item) => (
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
