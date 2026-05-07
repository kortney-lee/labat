import { NextRequest } from "next/server";

const SERVICES_URL = (process.env.WIHY_SERVICES_URL || "https://services.wihy.ai").replace(/\/+$/, "");
const CLIENT_ID = process.env.WIHY_ML_CLIENT_ID || "";
const CLIENT_SECRET = process.env.WIHY_ML_CLIENT_SECRET || "";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const q = (url.searchParams.get("q") || "").trim();
  const limit = url.searchParams.get("limit") || "8";
  const page = url.searchParams.get("page") || "1";

  if (q.length < 2) {
    return Response.json({ success: true, query: q, suggestions: [], pagination: { page: 1, limit: Number(limit), totalCount: 0, totalPages: 0, hasMore: false } });
  }

  const params = new URLSearchParams({ q, limit, page });

  try {
    const upstream = await fetch(`${SERVICES_URL}/api/research/suggest?${params.toString()}`, {
      headers: {
        "X-Client-ID": CLIENT_ID,
        "X-Client-Secret": CLIENT_SECRET,
        Accept: "application/json",
      },
      next: { revalidate: 600 },
    });

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "public, max-age=120, s-maxage=600, stale-while-revalidate=1200",
      },
    });
  } catch {
    return Response.json({ success: false, suggestions: [], error: "Suggest service unavailable." }, { status: 502 });
  }
}
