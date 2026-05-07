import { getExternalFeedArticles } from "@/lib/externalFeeds";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const rawLimit = Number(searchParams.get("limit") || "120");
  const limit = Number.isFinite(rawLimit) ? Math.min(300, Math.max(20, rawLimit)) : 120;

  const articles = await getExternalFeedArticles(limit);

  return Response.json(
    {
      success: true,
      total: articles.length,
      articles,
      generatedAt: new Date().toISOString(),
    },
    {
      headers: {
        "Cache-Control": "public, s-maxage=900, stale-while-revalidate=3600",
      },
    },
  );
}