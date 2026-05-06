import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AdSlot } from "@/components/AdSlot";
import { ArticleCard } from "@/components/ArticleCard";
import { getAllArticles, getArticlesByCategory } from "@/lib/articles";
import type { ArticleCategory } from "@/types/article";

interface CategoryPageProps {
  params: {
    slug: string;
  };
}

export const dynamicParams = false;

const validCategories = new Set<string>([
  "nutrition-education",
  "health-explained",
  "food-systems",
  "research-explained",
  "from-the-data",
  "perspective",
  "sponsored",
]);

export function generateStaticParams() {
  return Array.from(new Set(getAllArticles().map((a) => a.category))).map((slug) => ({ slug }));
}

export function generateMetadata({ params }: CategoryPageProps): Metadata {
  const categoryName = params.slug.replace(/-/g, " ");
  return {
    title: `Category: ${categoryName} | Vowels.org`,
    description: `Evidence-based nutrition stories in ${categoryName}.`,
    alternates: {
      canonical: `/category/${params.slug}`,
    },
    openGraph: {
      title: `Category: ${categoryName} | Vowels.org`,
      description: `Evidence-based nutrition stories in ${categoryName}.`,
      url: `/category/${params.slug}`,
      type: "website",
    },
  };
}

export default function CategoryPage({ params }: CategoryPageProps) {
  if (!validCategories.has(params.slug)) notFound();

  const articles = getArticlesByCategory(params.slug as ArticleCategory);
  return (
    <section className="space-y-4">
      <header className="news-card p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-newsroom">Category</p>
        <h1 className="mt-2 font-serif text-4xl text-slate-900">{params.slug.replace(/-/g, " ")}</h1>
        <p className="mt-2 text-sm text-slate-600">{articles.length} published articles</p>
      </header>
      <AdSlot slotName="Category Leaderboard" size="leaderboard" />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {articles.map((article, idx) => (
          <>
            <ArticleCard key={article.slug} article={article} />
            {(idx + 1) % 6 === 0 && idx + 1 < articles.length ? (
              <div key={`ad-${idx}`} className="md:col-span-2 lg:col-span-3">
                <AdSlot slotName="Category In-Grid Ad" size="leaderboard" />
              </div>
            ) : null}
          </>
        ))}
      </div>

      <AdSlot slotName="Category Bottom Leaderboard" size="leaderboard" className="mt-4" />
    </section>
  );
}
