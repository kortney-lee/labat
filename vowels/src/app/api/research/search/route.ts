import { NextRequest } from "next/server";

const SERVICES_URL = (process.env.WIHY_SERVICES_URL || "https://services.wihy.ai").replace(/\/+$/, "");
const CLIENT_ID = process.env.WIHY_ML_CLIENT_ID || "";
const CLIENT_SECRET = process.env.WIHY_ML_CLIENT_SECRET || "";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const query = (url.searchParams.get("q") || url.searchParams.get("keyword") || "").trim();
  const limit = url.searchParams.get("limit") || "20";
  const minYear = url.searchParams.get("minYear") || "";
  const type = url.searchParams.get("type") || "";

  if (!query) {
    return Response.json({ success: false, articles: [], error: "Missing query" }, { status: 400 });
  }

  const params = new URLSearchParams({ keyword: query, limit });
  if (minYear) params.set("minYear", minYear);
  if (type && type !== "all") params.set("type", type);

  try {
    const upstream = await fetch(`${SERVICES_URL}/api/research/search?${params.toString()}`, {
      headers: {
        "X-Client-ID": CLIENT_ID,
        "X-Client-Secret": CLIENT_SECRET,
        Accept: "application/json",
      },
      // Cache responses on the edge for a short time to reduce upstream load.
      next: { revalidate: 300 },
    });

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "public, max-age=60, s-maxage=300, stale-while-revalidate=600",
      },
    });
  } catch {
    return Response.json(
      { success: false, articles: [], error: "Research service unavailable." },
      { status: 502 },
    );
  }
}
