import { getAllArticles } from "@/lib/articles";
import { buildRss } from "@/lib/rss";

export function GET() {
  const xml = buildRss(getAllArticles());
  return new Response(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=1800, stale-while-revalidate=7200",
    },
  });
}
