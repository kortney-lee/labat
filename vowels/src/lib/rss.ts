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
  const selfUrl = `${siteUrl}/rss.xml`;
  const latestDate = articles.length
    ? new Date(Math.max(...articles.map((a) => +new Date(a.publishedAt)))).toUTCString()
    : new Date().toUTCString();

  const items = articles
    .map((a) => {
      const link = `${siteUrl}/article/${a.slug}`;
      const categories = (a.tags || [])
        .map((tag) => `<category>${escapeXml(tag)}</category>`)
        .join("\n  ");

      return `<item>
  <title>${escapeXml(a.title)}</title>
  <link>${escapeXml(link)}</link>
  <guid>${escapeXml(link)}</guid>
  <pubDate>${new Date(a.publishedAt).toUTCString()}</pubDate>
  <author>editor@vowels.org (${escapeXml(a.author)})</author>
  <description>${escapeXml(a.description)}</description>
  ${categories}
</item>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>Vowels.org | Nutrition Education</title>
  <link>${siteUrl}</link>
  <atom:link href="${selfUrl}" rel="self" type="application/rss+xml" />
  <description>Evidence-based nutrition education for practical daily decisions.</description>
  <language>en-us</language>
  <lastBuildDate>${latestDate}</lastBuildDate>
  <ttl>60</ttl>
  ${items}
</channel>
</rss>`;
}
