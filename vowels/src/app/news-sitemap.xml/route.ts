import { getAllArticles } from "@/lib/articles";
import { newsSitemapXml } from "@/lib/sitemap";

export function GET() {
  const xml = newsSitemapXml(getAllArticles());
  return new Response(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=1800, stale-while-revalidate=7200",
    },
  });
}
