import Link from "next/link";

import { SponsoredContentLabel } from "@/components/SponsoredContentLabel";
import type { Article } from "@/types/article";

interface ArticleCardProps {
  article: Article;
}

export function ArticleCard({ article }: ArticleCardProps) {
  return (
    <article className="group news-card p-5 transition hover:-translate-y-1 hover:shadow-[0_16px_42px_rgba(17,19,25,0.16)]">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="rounded-full bg-mist px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">{article.category}</span>
        {article.isSponsored ? <SponsoredContentLabel /> : null}
      </div>
      <h3 className="font-serif text-3xl leading-[0.95] text-slate-950 transition group-hover:text-brand">
        <Link href={`/article/${article.slug}`} className="[text-wrap:balance]">{article.title}</Link>
      </h3>
      <p className="mt-3 text-sm leading-6 text-slate-700">{article.description}</p>
      <div className="mt-4 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-[0.06em] text-slate-500">
        <span>{article.author}</span>
        <span>-</span>
        <span>{new Date(article.publishedAt).toLocaleDateString()}</span>
        <span>-</span>
        <span>{article.readingTime} min read</span>
      </div>
    </article>
  );
}
