import { NextRequest } from "next/server";

const defaultTarget = "https://whatishealthy.org/api/book/leads";
const upstreamUrl = process.env.LEADS_API_URL || defaultTarget;

interface LeadRequestBody {
  email?: string;
  first_name?: string;
  last_name?: string;
  source?: string;
  utm_source?: string;
  utm_campaign?: string;
  utm_content?: string;
  utm_medium?: string;
  fbclid?: string;
}

export async function POST(req: NextRequest) {
  let body: LeadRequestBody;

  try {
    body = (await req.json()) as LeadRequestBody;
  } catch {
    return Response.json({ success: false, message: "Invalid JSON body." }, { status: 400 });
  }

  const email = (body.email || "").trim().toLowerCase();
  if (!email) {
    return Response.json({ success: false, message: "Email is required." }, { status: 400 });
  }

  try {
    const upstream = await fetch(upstreamUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        first_name: (body.first_name || "").trim(),
        last_name: (body.last_name || "").trim(),
        source: (body.source || "vowels").trim(),
        utm_source: body.utm_source || "",
        utm_campaign: body.utm_campaign || "",
        utm_content: body.utm_content || "",
        utm_medium: body.utm_medium || "",
        fbclid: body.fbclid || "",
      }),
    });

    const text = await upstream.text();
    const contentType = upstream.headers.get("content-type") || "application/json";

    return new Response(text, {
      status: upstream.status,
      headers: { "Content-Type": contentType },
    });
  } catch {
    return Response.json(
      { success: false, message: "Lead service is unavailable right now." },
      { status: 502 }
    );
  }
}
