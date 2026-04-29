import { AdSlot } from "@/components/AdSlot";
import { ArticleCard } from "@/components/ArticleCard";
import { DataInsightCard } from "@/components/DataInsightCard";
import { FeaturedArticle } from "@/components/FeaturedArticle";
import { NewsletterSignup } from "@/components/NewsletterSignup";
import { getAllArticles, searchArticles } from "@/lib/articles";
import { weeklyInsights } from "@/lib/wihyData";

interface HomePageProps {
  searchParams?: {
    q?: string;
  };
}

export default function HomePage({ searchParams }: HomePageProps) {
  const all = getAllArticles();
  const query = searchParams?.q || "";
  const filtered = query ? searchArticles(query) : all;
  const featured = filtered[0] || all[0];
  const feed = filtered.slice(1);

  return (
    <div className="space-y-5">
      <AdSlot slotName="Homepage Leaderboard Ad" className="h-20" />

      {featured ? <FeaturedArticle article={featured} /> : null}

      <section className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-serif text-3xl text-slate-900">Latest Headlines</h2>
            {query ? <span className="text-sm text-slate-600">Search: {query}</span> : null}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {feed.map((article) => (
              <ArticleCard key={article.slug} article={article} />
            ))}
          </div>

          <AdSlot slotName="Homepage In-Feed Ad" />

          <section className="news-card p-5">
            <h3 className="font-serif text-3xl text-slate-900">From the Data</h3>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {weeklyInsights.map((insight) => (
                <DataInsightCard key={insight.label} insight={insight} />
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <AdSlot slotName="Homepage Sidebar Ad" className="min-h-52" />
          <NewsletterSignup />
          <AdSlot slotName="Mobile Sticky Banner Ad" />
        </div>
      </section>
    </div>
  );
}
