import { NextRequest } from "next/server";

const SERVICES_URL = (process.env.WIHY_SERVICES_URL || "https://services.wihy.ai").replace(/\/+$/, "");
const CLIENT_ID = process.env.WIHY_ML_CLIENT_ID || "";
const CLIENT_SECRET = process.env.WIHY_ML_CLIENT_SECRET || "";

export const dynamic = "force-dynamic";

function upstreamHeaders() {
  return {
    "X-Client-ID": CLIENT_ID,
    "X-Client-Secret": CLIENT_SECRET,
    Accept: "application/json",
  };
}

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const q = (url.searchParams.get("q") || "").trim();
  const context = (url.searchParams.get("context") || "personal").trim();
  const limit = url.searchParams.get("limit") || "8";
  const includeRelated = url.searchParams.get("include_related") || "true";
  const useGemini = url.searchParams.get("use_gemini") || "false";

  if (!q) {
    return Response.json({ success: false, error: "Missing q" }, { status: 400 });
  }

  const params = new URLSearchParams({
    q,
    context,
    limit,
    include_related: includeRelated,
    use_gemini: useGemini,
  });

  try {
    const upstream = await fetch(`${SERVICES_URL}/api/search/ai-mode?${params.toString()}`, {
      headers: upstreamHeaders(),
      next: { revalidate: 120 },
    });

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "public, max-age=30, s-maxage=120, stale-while-revalidate=300",
      },
    });
  } catch {
    return Response.json({ success: false, error: "AI mode service unavailable." }, { status: 502 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.text();

    const upstream = await fetch(`${SERVICES_URL}/api/search/ai-mode`, {
      method: "POST",
      headers: {
        ...upstreamHeaders(),
        "Content-Type": "application/json",
      },
      body,
      cache: "no-store",
    });

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json({ success: false, error: "AI mode service unavailable." }, { status: 502 });
  }
}
