import Link from "next/link";

import { SponsoredContentLabel } from "@/components/SponsoredContentLabel";
import { getArticleHeroImage } from "@/lib/article-images";
import type { Article } from "@/types/article";

interface ArticleCardProps {
  article: Article;
}

export function ArticleCard({ article }: ArticleCardProps) {
  const hero = getArticleHeroImage(article);
  return (
    <article className="group news-card overflow-hidden transition hover:-translate-y-1 hover:shadow-[0_16px_42px_rgba(17,19,25,0.16)]">
      <div className="relative h-44 w-full overflow-hidden">
        <img
          src={hero.thumb}
          alt={article.imageAlt ?? article.title}
          width={600}
          height={340}
          className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
          loading="lazy"
        />
        <span className="absolute left-3 top-3 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600 backdrop-blur-sm">
          {article.category}
        </span>
        {article.isSponsored ? (
          <span className="absolute right-3 top-3">
            <SponsoredContentLabel />
          </span>
        ) : null}
      </div>
      <div className="p-5">
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
      </div>
    </article>
  );
}
