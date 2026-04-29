import Link from "next/link";

import { SponsoredContentLabel } from "@/components/SponsoredContentLabel";
import type { Article } from "@/types/article";

interface ArticleCardProps {
  article: Article;
}

export function ArticleCard({ article }: ArticleCardProps) {
  return (
    <article className="news-card p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-newsroom">{article.category}</span>
        {article.isSponsored ? <SponsoredContentLabel /> : null}
      </div>
      <h3 className="font-serif text-2xl leading-tight text-slate-900">
        <Link href={`/article/${article.slug}`}>{article.title}</Link>
      </h3>
      <p className="mt-2 text-sm text-slate-600">{article.description}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        <span>{article.author}</span>
        <span>-</span>
        <span>{new Date(article.publishedAt).toLocaleDateString()}</span>
        <span>-</span>
        <span>{article.readingTime} min read</span>
      </div>
    </article>
  );
}
