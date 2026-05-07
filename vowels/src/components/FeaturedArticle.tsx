import Link from "next/link";

import { CTAButton } from "@/components/CTAButton";
import { SponsoredContentLabel } from "@/components/SponsoredContentLabel";
import { getArticleHeroImage } from "@/lib/article-images";
import type { Article } from "@/types/article";

interface FeaturedArticleProps {
  article: Article;
}

export function FeaturedArticle({ article }: FeaturedArticleProps) {
  const hero = getArticleHeroImage(article);
  const coverTitle = article.title.length > 108 ? `${article.title.slice(0, 105).trimEnd()}...` : article.title;

  return (
    <section className="relative overflow-hidden rounded-[2rem] border border-black/10 bg-gradient-to-br from-coal via-slate-900 to-black text-white shadow-news">
      <img
        src={hero.src}
        alt={article.imageAlt ?? article.title}
        className="absolute inset-0 h-full w-full object-cover opacity-28"
        loading="lazy"
      />
      <div className="absolute inset-0 bg-gradient-to-r from-black/82 via-black/65 to-black/75" />
      <div className="absolute -left-12 bottom-0 h-52 w-52 rounded-full bg-white/10 blur-3xl" />

      <div className="relative grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="px-6 py-8 md:px-10 md:py-11">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-orange-300">Cover Story</span>
          <h1 className="mt-5 max-w-3xl font-serif text-3xl leading-[1.02] md:text-5xl [text-wrap:balance]">
            <Link href={`/article/${article.slug}`}>{coverTitle}</Link>
          </h1>
          <p className="mt-6 max-w-2xl text-sm leading-7 text-white/82 md:text-base">{article.description}</p>

          <div className="mt-6 flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.12em] text-white/70">
            <span>{article.author}</span>
            <span className="h-1 w-1 rounded-full bg-white/40" />
            <span>{article.readingTime} min read</span>
          </div>
        </div>

        <div className="m-4 rounded-[1.5rem] bg-white/95 p-6 text-black backdrop-blur md:m-6 md:p-8">
          <div className="mb-4 overflow-hidden rounded-xl">
            <img src={hero.thumb} alt={article.imageAlt ?? article.title} className="h-36 w-full object-cover" loading="lazy" />
          </div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Featured Report</p>
          <div className="mt-4 text-sm text-slate-700">
            <p className="font-semibold">{article.takeaway}</p>
          </div>

          <div className="mt-4 space-y-2 text-xs uppercase tracking-[0.1em] text-slate-500">
            <p>Category: {article.category.replace(/-/g, " ")}</p>
            {article.isSponsored ? <SponsoredContentLabel /> : null}
          </div>

          <p className="mt-6 text-sm leading-7 text-slate-700">Research-backed reporting on food systems, nutrition literacy, and what healthy actually means in practice.</p>
          <div className="mt-8">
            <CTAButton label="Read Full Report" href={`/article/${article.slug}`} eventLabel="featured_article_cta" />
          </div>
        </div>
      </div>
    </section>
  );
}
