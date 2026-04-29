/**
 * postGenerator.ts — Gemini + Imagen post generation pipeline.
 */

import { VertexAI, SchemaType } from "@google-cloud/vertexai";
import { getHealthContext } from "./ragClient";
import { generateImage, isImagenAvailable } from "./imagenClient";
import { pickAssetLibraryImage } from "../storage/assetLibrary";

import { getBrand, BrandProfile, BrandId } from "../config/brand";
import { FormatKey } from "../config/formats";
import { logger } from "../utils/logger";

const GCP_PROJECT = process.env.GCP_PROJECT || "wihy-ai";
const GCP_LOCATION = process.env.GCP_LOCATION || "us-central1";
const ALEX_URL = process.env.ALEX_URL || "https://wihy-alex-n4l2vldq3q-uc.a.run.app";
const INTERNAL_ADMIN_TOKEN = process.env.INTERNAL_ADMIN_TOKEN || "";

const vertexAI = new VertexAI({ project: GCP_PROJECT, location: GCP_LOCATION });
const NO_ASSET_REUSE_BRANDS = new Set(
  (process.env.SHANIA_NO_ASSET_REUSE_BRANDS || "parentingwithchrist")
    .split(",")
    .map((v) => v.trim().toLowerCase())
    .filter(Boolean),
);

/** What Gemini returns for post planning. */
export interface PostPlan {
  caption: string;
  hashtags: string[];
  topicHint?: string;
}

interface AlexRealtimeSignals {
  hashtags?: string[];
}

/** Final output from the post generator. */
export interface GeneratedPost {
  imageBytes: Buffer;
  mimeType: string;
  caption: string;
  hashtags: string[];
  ragContext?: string;
  templateId: string;
  brand: string;
}

function aspectRatioForFormat(size: FormatKey): "1:1" | "9:16" | "16:9" | "3:4" {
  if (size === "story_vertical") return "9:16";
  if (size === "feed_portrait") return "3:4";
  if (size === "hd_landscape" || size === "ad_landscape" || size === "blog_hero") return "16:9";
  return "1:1";
}

async function tryDownloadImage(url: string): Promise<{ bytes: Buffer; mimeType: string } | null> {
  try {
    const resp = await fetch(url, { signal: AbortSignal.timeout(20000) });
    if (!resp.ok) return null;
    const arr = await resp.arrayBuffer();
    const mimeType = resp.headers.get("content-type") || "image/jpeg";
    return { bytes: Buffer.from(arr), mimeType };
  } catch {
    return null;
  }
}

// ────────── Step 1+2: RAG context → Gemini plan ──────────

const POST_PLAN_SCHEMA = {
  type: SchemaType.OBJECT,
  properties: {
    caption: {
      type: SchemaType.STRING,
      description:
        "The social media caption. Engaging, educational, health-focused. 1-3 short paragraphs. Include a hook opening line. Do NOT include hashtags here.",
    },
    hashtags: {
      type: SchemaType.ARRAY,
      items: { type: SchemaType.STRING },
      description: "5-8 relevant hashtags without # prefix",
    },
    topicHint: {
      type: SchemaType.STRING,
      description:
        "Topic category: nutrition, exercise, supplements, sugar, processed_meat, fasting, alcohol, environment, food_access, data, snacking, or general",
    },
  },
  required: ["caption", "hashtags"],
};

const BRAND_HARD_RULES: Partial<Record<BrandId, string[]>> = {
  wihy: [
    "Focus on app and product value. Mention features, workflows, and outcomes.",
    "Do not drift into generic motivation content.",
  ],
  communitygroceries: [
    "Focus on app and product value tied to meals, grocery lists, and planning tools.",
    "Every caption should connect food inspiration to using the app.",
  ],
  parentingwithchrist: [
    "Never mention Vowels, Vowels.Org, or any parent brand.",
    "Never mention books, ebooks, hardcopy offers, lead magnets, or downloads.",
  ],
  vowels: [
    "Position content as nutrition education and publication-style reporting.",
    "Never mention books, ebooks, hardcopy offers, lead magnets, or downloads.",
  ],
};

function buildSystemPrompt(brand: BrandProfile, ragFacts: string | null): string {
  let prompt = `You are a social media content creator for ${brand.name} (${brand.tagline}), a health-focused brand at ${brand.domain}.

BRAND VOICE:
${brand.voice}

CONTENT FOCUS:
${brand.contentFocus}

CORE TOPICS THIS BRAND COVERS:
${brand.topics.map((t) => `- ${t}`).join("\n")}

YOUR JOB:
1. Write an engaging social media caption (1-3 short paragraphs)
2. Create relevant hashtags (include #${brand.hashtagPrefix} as first hashtag)

CAPTION RULES:
- Start with a hook (question, bold statement, or surprising fact)
- Include 1-2 specific, actionable takeaways
- End with engagement driver (question, CTA, or thought-provoker)
- Keep it under 200 words
- Reference ${brand.name} naturally when relevant
- Must relate to ${brand.name}'s actual mission — NO generic wellness fluff`;

  const hardRules = BRAND_HARD_RULES[brand.id as BrandId] || [];
  if (hardRules.length) {
    prompt += `\n\nBRAND HARD RULES (mandatory):\n${hardRules.map((r) => `- ${r}`).join("\n")}`;
  }

  if (ragFacts) {
    prompt += `\n\nGROUNDED KNOWLEDGE BASE (use these facts to inform your caption — cite specific data):
${ragFacts}`;
  }

  return prompt;
}

async function planPost(userPrompt: string, ragFacts: string | null, brand: BrandProfile): Promise<PostPlan> {
  const model = vertexAI.getGenerativeModel({
    model: "gemini-2.5-flash",
    generationConfig: {
      responseMimeType: "application/json",
      responseSchema: POST_PLAN_SCHEMA,
      temperature: 0.9,
    },
  });

  const systemPrompt = buildSystemPrompt(brand, ragFacts);
  const result = await model.generateContent({
    contents: [{ role: "user", parts: [{ text: systemPrompt + "\n\n" + userPrompt }] }],
  });
  const text = result.response?.candidates?.[0]?.content?.parts?.[0]?.text || "";
  const plan: PostPlan = JSON.parse(text);

  logger.info(
    `Post plan [${brand.id}]: caption=${plan.caption.length}ch, hashtags=${plan.hashtags.length}`,
  );
  return plan;
}

async function getAlexRealtimeSignals(query: string, brand: BrandProfile): Promise<AlexRealtimeSignals | null> {
  if (!INTERNAL_ADMIN_TOKEN) {
    return null;
  }

  try {
    const params = new URLSearchParams({
      query,
      brand: brand.id,
      limit: "8",
      refresh_keywords: "true",
    });

    const response = await fetch(`${ALEX_URL}/api/alex/realtime-signals?${params.toString()}`, {
      method: "GET",
      headers: {
        "X-Admin-Token": INTERNAL_ADMIN_TOKEN,
      },
    });

    if (!response.ok) {
      logger.warn(`ALEX realtime signals unavailable: ${response.status}`);
      return null;
    }

    const data = (await response.json()) as AlexRealtimeSignals;
    return data;
  } catch (err: unknown) {
    logger.warn(`ALEX realtime signals fetch failed (non-fatal): ${err instanceof Error ? err.message : String(err)}`);
    return null;
  }
}

function normalizeHashtag(raw: string): string {
  const cleaned = raw.replace(/^#+/, "").trim();
  return cleaned;
}

function mergeHashtags(primary: string[], secondary: string[], cap: number = 10): string[] {
  const merged: string[] = [];
  for (const tag of [...primary, ...secondary]) {
    const normalized = normalizeHashtag(tag);
    if (!normalized) continue;
    if (!merged.some((t) => t.toLowerCase() === normalized.toLowerCase())) {
      merged.push(normalized);
    }
    if (merged.length >= cap) break;
  }
  return merged;
}

// ────────── Text-only pipeline (no image generation) ──────────

export interface PlannedPost {
  caption: string;
  hashtags: string[];
  topicHint?: string;
  ragContext?: string;
  brand: string;
}

export async function planPostOnly(
  userPrompt: string,
  brandId?: BrandId | string,
): Promise<PlannedPost> {
  const brand = getBrand(brandId);

  logger.info(`Plan-only [${brand.id}]: fetching RAG context...`);
  const ragContext = await getHealthContext(userPrompt);
  const ragFacts = ragContext?.facts || null;

  logger.info(`Plan-only [${brand.id}]: planning with Gemini...`);
  const plan = await planPost(userPrompt, ragFacts, brand);
  const alexSignals = await getAlexRealtimeSignals(userPrompt, brand);
  const combinedHashtags = mergeHashtags(plan.hashtags, alexSignals?.hashtags || []);

  return {
    caption: plan.caption,
    hashtags: combinedHashtags,
    topicHint: plan.topicHint,
    ragContext: ragFacts || undefined,
    brand: brand.id,
  };
}

// ────────── Full pipeline (Gemini planning → Imagen image generation) ──────────

export async function generatePost(
  userPrompt: string,
  outputSize: FormatKey = "feed_square",
  brandId?: BrandId | string,
): Promise<GeneratedPost> {
  const startTime = Date.now();
  const brand = getBrand(brandId);

  // Step 1: Fetch RAG context
  logger.info(`Post pipeline [${brand.id}]: fetching RAG context...`);
  const ragContext = await getHealthContext(userPrompt);
  const ragFacts = ragContext?.facts || null;

  // Step 2: Gemini plans the caption + hashtags with brand-specific voice
  logger.info(`Post pipeline [${brand.id}]: planning caption with Gemini...`);
  const plan = await planPost(userPrompt, ragFacts, brand);
  const alexSignals = await getAlexRealtimeSignals(userPrompt, brand);
  const combinedHashtags = mergeHashtags(plan.hashtags, alexSignals?.hashtags || []);

  // Step 3: optional asset-library pick (if enabled)
  let libraryImageBytes: Buffer | undefined;
  let libraryImageMimeType: string | undefined;
  const libraryImageEnabled =
    (process.env.SHANIA_USE_ASSET_LIBRARY || "true").toLowerCase() !== "false"
    && !NO_ASSET_REUSE_BRANDS.has(brand.id.toLowerCase());

  if (!libraryImageEnabled && NO_ASSET_REUSE_BRANDS.has(brand.id.toLowerCase())) {
    logger.info(`Post pipeline [${brand.id}]: asset-library reuse disabled for this brand`);
  }

  if (libraryImageEnabled) {
    const imageHint = [plan.topicHint, userPrompt].filter(Boolean).join(" ");
    const libraryPick = await pickAssetLibraryImage(brand.id, imageHint);
    if (libraryPick) {
      const downloaded = await tryDownloadImage(libraryPick.url);
      if (downloaded) {
        // Reject non-image content (e.g. GCS objects stored with wrong content-type)
        const isRealImage = downloaded.mimeType.startsWith("image/");
        if (isRealImage) {
          libraryImageBytes = downloaded.bytes;
          libraryImageMimeType = downloaded.mimeType;
          logger.info(
            `Post pipeline [${brand.id}]: using asset-library image (${libraryPick.provider}) ${libraryPick.label}`,
          );
        } else {
          logger.warn(
            `Post pipeline [${brand.id}]: asset-library image rejected (mimeType=${downloaded.mimeType}) ${libraryPick.label} — falling back to Imagen`,
          );
        }
      }
    }
  }

  if (libraryImageBytes && libraryImageMimeType) {
    const elapsed = Date.now() - startTime;
    logger.info(`Post pipeline [${brand.id}] complete (asset-library) in ${elapsed}ms (${libraryImageBytes.length} bytes)`);
    return {
      imageBytes: libraryImageBytes,
      mimeType: libraryImageMimeType,
      caption: plan.caption,
      hashtags: combinedHashtags,
      ragContext: ragFacts || undefined,
      templateId: "asset_library",
      brand: brand.id,
    };
  }

  if (!isImagenAvailable()) {
    throw new Error("Imagen generation unavailable");
  }

  const aspectRatio = aspectRatioForFormat(outputSize);
  const prompt = [
    `${brand.name} branded health social image`,
    `Topic: ${userPrompt}`,
    plan.topicHint ? `Theme: ${plan.topicHint}` : "",
    ragFacts ? `Grounding facts: ${ragFacts.substring(0, 700)}` : "",
    "Photorealistic editorial style, high detail, no text, no logos, no watermarks, no overlays",
  ]
    .filter(Boolean)
    .join(". ");

  logger.info(`Post pipeline [${brand.id}]: generating Imagen image (aspect=${aspectRatio})...`);
  const imagenResult = await generateImage({ prompt, aspectRatio });
  const elapsed = Date.now() - startTime;
  logger.info(`Post pipeline [${brand.id}] complete (imagen) in ${elapsed}ms (${imagenResult.imageBytes.length} bytes)`);

  return {
    imageBytes: Buffer.from(imagenResult.imageBytes),
    mimeType: imagenResult.mimeType,
    caption: plan.caption,
    hashtags: combinedHashtags,
    ragContext: ragFacts || undefined,
    templateId: "gemini_imagen",
    brand: brand.id,
  };
}
