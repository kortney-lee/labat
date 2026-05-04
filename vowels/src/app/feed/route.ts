import { getAllArticles } from "@/lib/articles";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://vowels.org";

export function GET() {
  const items = getAllArticles().map((article) => ({
    id: `${siteUrl}/article/${article.slug}`,
    url: `${siteUrl}/article/${article.slug}`,
    title: article.title,
    content_text: article.description,
    summary: article.takeaway,
    date_published: new Date(article.publishedAt).toISOString(),
    date_modified: new Date(article.updatedAt || article.publishedAt).toISOString(),
    authors: [{ name: article.author }],
    tags: article.tags,
    image: article.image ? `${siteUrl}${article.image}` : undefined,
  }));

  const feed = {
    version: "https://jsonfeed.org/version/1.1",
    title: "Vowels.org | Nutrition Education",
    home_page_url: siteUrl,
    feed_url: `${siteUrl}/feed`,
    description: "Evidence-based nutrition education for practical daily decisions.",
    language: "en-US",
    items,
  };

  return new Response(JSON.stringify(feed), {
    headers: {
      "Content-Type": "application/feed+json; charset=utf-8",
      "Cache-Control": "public, s-maxage=1800, stale-while-revalidate=7200",
    },
  });
}
