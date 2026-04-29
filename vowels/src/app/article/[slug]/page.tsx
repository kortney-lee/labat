import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { marked } from "marked";

import { AdSlot } from "@/components/AdSlot";
import { ArticleCard } from "@/components/ArticleCard";
import { ArticleViewTracker } from "@/components/ArticleViewTracker";
import { SponsoredContentLabel } from "@/components/SponsoredContentLabel";
import { getAllArticles, getArticleBySlug, getRelatedArticles } from "@/lib/articles";
import { articleJsonLd, articleMetadata } from "@/lib/seo";

interface ArticlePageProps {
  params: {
    slug: string;
  };
}

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

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <article className="news-card p-6">
        <ArticleViewTracker slug={article.slug} category={article.category} />
        <p className="text-xs font-semibold uppercase tracking-wide text-newsroom">{article.category}</p>
        <h1 className="mt-3 font-serif text-4xl leading-tight text-slate-900">{article.title}</h1>
        <p className="mt-3 text-base text-slate-600">{article.description}</p>
        <div className="mt-4 flex flex-wrap gap-3 text-sm text-slate-600">
          <span>{article.author}</span>
          <span>{new Date(article.publishedAt).toLocaleDateString()}</span>
          <span>{article.readingTime} min read</span>
          {article.isSponsored ? <SponsoredContentLabel /> : null}
        </div>

        <AdSlot slotName="Article Top Banner Ad" className="mt-6" />

        <div
          className="prose prose-slate mt-6 max-w-none prose-headings:font-serif prose-a:text-newsroom"
          dangerouslySetInnerHTML={{ __html: html }}
        />

        <AdSlot slotName="Article Mid-Article Ad" className="mt-6" />

        {article.sourceLinks?.length ? (
          <section className="mt-8 rounded-xl border border-sky-200 bg-sky-50 p-4">
            <h3 className="font-serif text-2xl text-slate-900">Sources</h3>
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

        <AdSlot slotName="Article Bottom Native Ad" className="mt-8" />

        <section className="mt-8">
          <h3 className="font-serif text-3xl text-slate-900">Related Articles</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {related.slice(0, 4).map((item) => (
              <ArticleCard key={item.slug} article={item} />
            ))}
          </div>
          <Link href={`/category/${article.category}`} className="mt-4 inline-block text-sm text-newsroom underline">
            Explore more in {article.category}
          </Link>
        </section>

        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      </article>

      <aside className="space-y-4">
        <AdSlot slotName="Homepage Sidebar Ad" className="min-h-52" />
        <AdSlot slotName="Mobile Sticky Banner Ad" />
      </aside>
    </div>
  );
}
