import Link from "next/link";

import { CTAButton } from "@/components/CTAButton";
import { SponsoredContentLabel } from "@/components/SponsoredContentLabel";
import type { Article } from "@/types/article";

interface FeaturedArticleProps {
  article: Article;
}

export function FeaturedArticle({ article }: FeaturedArticleProps) {
  return (
    <section className="news-card p-6">
      <span className="text-xs font-bold uppercase tracking-wide text-newsroom">Featured Report</span>
      <h1 className="mt-3 font-serif text-4xl leading-tight text-slate-900">
        <Link href={`/article/${article.slug}`}>{article.title}</Link>
      </h1>
      <p className="mt-3 max-w-3xl text-base text-slate-600">{article.description}</p>
      <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-600">
        <span>{article.author}</span>
        <span>{article.readingTime} min read</span>
        {article.isSponsored ? <SponsoredContentLabel /> : null}
      </div>
      <div className="mt-5">
        <CTAButton label="Read Full Report" href={`/article/${article.slug}`} eventLabel="featured_article_cta" />
      </div>
    </section>
  );
}
