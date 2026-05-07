import { NextRequest } from "next/server";

const BOOK_SERVICE = process.env.BOOK_SERVICE_URL || "https://whatishealthy.org";

// Vowels.org article slug → health topic mapping for sequence routing
const SLUG_TO_TOPIC: Record<string, string> = {
  "weight": "weight", "lose-weight": "weight", "weight-loss": "weight",
  "kids": "kids", "children": "kids", "family": "family",
  "energy": "energy", "fatigue": "energy", "tired": "energy",
  "grocery": "groceries", "groceries": "groceries", "budget": "groceries",
  "sugar": "weight", "diabetes": "weight", "blood-sugar": "weight",
  "fiber": "weight", "protein": "weight",
  "label": "warning", "labels": "warning", "ingredient": "warning",
};

function topicFromSlug(referralUrl: string): string {
  try {
    const url = new URL(referralUrl);
    const slug = url.pathname.split("/").filter(Boolean).pop() || "";
    for (const [key, topic] of Object.entries(SLUG_TO_TOPIC)) {
      if (slug.includes(key)) return topic;
    }
  } catch { /* ignore */ }
  return "general";
}

interface LeadRequestBody {
  email?: string;
  first_name?: string;
  last_name?: string;
  source?: string;
  topic?: string;          // explicit topic override
  referral_url?: string;   // article page they came from
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

  const source = (body.source || "vowels-newsletter").trim();
  const referralUrl = (body.referral_url || "").trim();

  // Resolve topic: explicit > inferred from article slug > "general"
  const topic = body.topic?.trim() || topicFromSlug(referralUrl) || "general";

  // Vowels.org signups go to the newsletter endpoint (info-first sequence)
  // Book/Facebook leads go to the standard book leads endpoint
  const isNewsletterSignup = source.includes("vowels") || source.includes("newsletter");
  const endpoint = isNewsletterSignup
    ? `${BOOK_SERVICE}/api/book/newsletter-signup`
    : `${BOOK_SERVICE}/api/book/leads`;

  const payload = isNewsletterSignup
    ? { email, first_name: (body.first_name || "").trim(), last_name: (body.last_name || "").trim(), topic, referral_url: referralUrl, utm_source: body.utm_source || "", utm_campaign: body.utm_campaign || "", utm_medium: body.utm_medium || "" }
    : { email, first_name: (body.first_name || "").trim(), last_name: (body.last_name || "").trim(), source, utm_source: body.utm_source || "", utm_campaign: body.utm_campaign || "", utm_content: body.utm_content || topic, utm_medium: body.utm_medium || "", fbclid: body.fbclid || "", referral_url: referralUrl };

  try {
    const upstream = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") || "application/json" },
    });
  } catch {
    return Response.json({ success: false, message: "Signup service unavailable. Please try again." }, { status: 502 });
  }
}
