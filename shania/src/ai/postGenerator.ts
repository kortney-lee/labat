/**
 * postGenerator.ts — Full AI post generation pipeline with multi-brand support.
 *
 * Pipeline:
 *  1. Fetch WIHY RAG context for grounded health facts
 *  2. Gemini writes caption + hashtags using brand-specific voice
 *  3. Gemini generates structured graphic content (headline, subtext, template)
 *  4. Create branded design via Canva API with structured data
 *  5. Export design as PNG image via Canva
 *  6. Returns the final image + caption + hashtags
 *
 * Supported brands: wihy, communitygroceries, vowels, snackingwell
 *
 * NOTE: Now 100% powered by Canva — no more HTML templates or Puppeteer
 */

import { VertexAI, SchemaType } from "@google-cloud/vertexai";
import { getHealthContext } from "./ragClient";
import { generateGraphicContent } from "./geminiClient";
import { generateImage, isImagenAvailable } from "./imagenClient";
import { getCanvaClient } from "../services/canvaService";
import type { DesignData } from "../services/canvaService";
import { pickAssetLibraryImage } from "../storage/assetLibrary";

import { getBrand, BrandProfile, BrandId } from "../config/brand";
import { FORMATS, FormatKey } from "../config/formats";
import { TemplateData } from "../types";
import { logger } from "../utils/logger";

const GCP_PROJECT = process.env.GCP_PROJECT || "wihy-ai";
const GCP_LOCATION = process.env.GCP_LOCATION || "us-central1";
const ALEX_URL = process.env.ALEX_URL || "https://wihy-alex-n4l2vldq3q-uc.a.run.app";
const INTERNAL_ADMIN_TOKEN = process.env.INTERNAL_ADMIN_TOKEN || "";

const vertexAI = new VertexAI({ project: GCP_PROJECT, location: GCP_LOCATION });

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

// ────────── Full pipeline (context generation → branded template) ──────────

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

  // Step 3: Gemini generates structured graphic content (headline, subtext, template)
  //         NOW with RAG facts so the graphic contains real data
  logger.info(`Post pipeline [${brand.id}]: generating graphic content...`);
  const graphicContent = await generateGraphicContent(userPrompt, undefined, brand, ragFacts);
  const isCommunityGroceries = brand.id === "communitygroceries";

  // Now using Canva templates — map old template types to design content
  // All template selection logic simplified since Canva handles layout variations
  let selectedBrand = brand.id;

  // Generate photo if needed for image-first mode
  let photoUrl: string | undefined;
  let mealPhotoBytes: Buffer | undefined;
  let mealPhotoMimeType: string | undefined;
  const libraryImageEnabled = (process.env.SHANIA_USE_ASSET_LIBRARY || "true").toLowerCase() !== "false";
  const imageFirstEnabled = (process.env.SHANIA_IMAGE_FIRST_MODE || "true").toLowerCase() !== "false";
  const hasPhotoQuery = Boolean(graphicContent.photoQuery && graphicContent.photoQuery.trim().length > 0);
  const cgMealImagePriority = (process.env.SHANIA_CG_MEAL_IMAGE_PRIORITY || "true").toLowerCase() !== "false";

  // Prefer image/graphic asset library first, then fallback to generated images.
  if (libraryImageEnabled) {
    const imageHint = [plan.topicHint, userPrompt].filter(Boolean).join(" ");
    const libraryPick = await pickAssetLibraryImage(brand.id, imageHint);
    if (libraryPick) {
      photoUrl = libraryPick.url;
      logger.info(
        `Post pipeline [${brand.id}]: using asset-library image (${libraryPick.provider}) ${libraryPick.label}`,
      );
    }
  }

  // CG must always have a meal-centric photo prompt; synthesize fallback if Gemini misses it.
  if (isCommunityGroceries && !hasPhotoQuery) {
    const fallbackPhotoQuery = [
      "A warm, realistic home kitchen scene with a freshly plated healthy family meal",
      graphicContent.headline ? `inspired by: ${graphicContent.headline}` : "",
      graphicContent.subtext ? `${graphicContent.subtext}` : "",
      "natural light, editorial food photography, appetizing textures, no text no signs no labels",
    ]
      .filter(Boolean)
      .join(", ");

    graphicContent.photoQuery = fallbackPhotoQuery;
  }

  const shouldGeneratePhoto =
    !photoUrl &&
    (imageFirstEnabled && isImagenAvailable() && Boolean(graphicContent.photoQuery && graphicContent.photoQuery.trim().length > 0)) ||
    (!photoUrl && isCommunityGroceries && isImagenAvailable() && Boolean(graphicContent.photoQuery && graphicContent.photoQuery.trim().length > 0));

  if (shouldGeneratePhoto) {
    try {
      logger.info(`Post pipeline [${brand.id}]: generating Imagen photo...`);
      const imagenResult = await generateImage({ prompt: graphicContent.photoQuery!, aspectRatio: "1:1" });
      photoUrl = `data:${imagenResult.mimeType};base64,${Buffer.from(imagenResult.imageBytes).toString("base64")}`;
      mealPhotoBytes = Buffer.from(imagenResult.imageBytes);
      mealPhotoMimeType = imagenResult.mimeType;
      logger.info(`Post pipeline [${brand.id}]: Imagen photo generated (${imagenResult.imageBytes.length} bytes)`);
    } catch (err: unknown) {
      logger.warn(`Imagen photo generation failed — continuing without photo: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  // For Community Groceries, prioritize posting actual meal images through Labat.
  // Falls back to Canva if photo generation failed.
  if (isCommunityGroceries && cgMealImagePriority && mealPhotoBytes && mealPhotoMimeType) {
    const elapsed = Date.now() - startTime;
    logger.info(
      `Post pipeline [${brand.id}] complete (meal-image-priority) in ${elapsed}ms (${mealPhotoBytes.length} bytes)`,
    );

    return {
      imageBytes: mealPhotoBytes,
      mimeType: mealPhotoMimeType,
      caption: plan.caption,
      hashtags: combinedHashtags,
      ragContext: ragFacts || undefined,
      templateId: "cg_meal_photo",
      brand: brand.id,
    };
  }

  // Step 4: Create design via Canva API using brand-specific template
  logger.info(
    `Post pipeline [${brand.id}]: creating Canva design (templateHint=${graphicContent.template || "none"})...`,
  );

  const designData: DesignData = {
    headline: graphicContent.headline,
    subtext: graphicContent.subtext,
    cta: graphicContent.cta,
    quote: graphicContent.quote,
    attribution: graphicContent.attribution,
    tip: graphicContent.tip,
    tipLabel: graphicContent.tipLabel,
    statNumber: graphicContent.statNumber,
    statLabel: graphicContent.statLabel,
    dataPoints: graphicContent.dataPoints,
    source: graphicContent.source,
    // photoUrl is used for future asset upload integration
    photoUrl,
  };

  try {
    const canvaClient = getCanvaClient();
    const finalImage = await canvaClient.generateDesignImage(
      selectedBrand as BrandId,
      designData,
      { templateHint: graphicContent.template },
    );

    const elapsed = Date.now() - startTime;
    logger.info(`Post pipeline [${brand.id}] complete (Canva) in ${elapsed}ms (${finalImage.length} bytes)`);

    return {
      imageBytes: finalImage,
      mimeType: "image/png",
      caption: plan.caption,
      hashtags: combinedHashtags,
      ragContext: ragFacts || undefined,
      templateId: graphicContent.template || selectedBrand,
      brand: brand.id,
    };
  } catch (err: unknown) {
    logger.error(`Canva design generation failed: ${err instanceof Error ? err.message : String(err)}`);
    throw err;
  }
}
