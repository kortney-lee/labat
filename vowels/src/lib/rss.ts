import type { Article } from "@/types/article";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://vowels.org";

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export function buildRss(articles: Article[]): string {
  const items = articles
    .map((a) => {
      const link = `${siteUrl}/article/${a.slug}`;
      return `<item>
  <title>${escapeXml(a.title)}</title>
  <link>${escapeXml(link)}</link>
  <guid>${escapeXml(link)}</guid>
  <pubDate>${new Date(a.publishedAt).toUTCString()}</pubDate>
  <description>${escapeXml(a.description)}</description>
</item>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Vowels.org | Nutrition Education</title>
  <link>${siteUrl}</link>
  <description>Evidence-first nutrition journalism.</description>
  ${items}
</channel>
</rss>`;
}
