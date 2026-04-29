import type { Article } from "@/types/article";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://vowels.org";

export function allStaticRoutes(): string[] {
  return [
    "/",
    "/about",
    "/contact",
    "/privacy",
    "/terms",
    "/editorial-policy",
    "/health-disclaimer",
  ];
}

export function articleRoutes(articles: Article[]): string[] {
  return articles.map((a) => `/article/${a.slug}`);
}

export function categoryRoutes(articles: Article[]): string[] {
  const unique = new Set(articles.map((a) => a.category));
  return Array.from(unique).map((c) => `/category/${c}`);
}

export function newsSitemapXml(articles: Article[]): string {
  const twoDaysAgo = Date.now() - 2 * 24 * 60 * 60 * 1000;
  const recent = articles.filter((a) => +new Date(a.publishedAt) >= twoDaysAgo);

  const rows = recent
    .map((a) => {
      const loc = `${siteUrl}/article/${a.slug}`;
      return `<url>
  <loc>${loc}</loc>
  <news:news>
    <news:publication>
      <news:name>Vowels.org</news:name>
      <news:language>en</news:language>
    </news:publication>
    <news:publication_date>${new Date(a.publishedAt).toISOString()}</news:publication_date>
    <news:title>${a.title}</news:title>
  </news:news>
</url>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
${rows}
</urlset>`;
}
