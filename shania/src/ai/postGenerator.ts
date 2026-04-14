/**
 * postGenerator.ts — Full AI post generation pipeline with multi-brand support.
 *
 * Pipeline:
 *  1. Fetch WIHY RAG context for grounded health facts
 *  2. Gemini writes caption + hashtags using brand-specific voice
 *  3. Gemini generates structured graphic content (headline, subtext, template)
 *  4. Branded HTML template rendered via Puppeteer into a professional graphic
 *  5. Returns the final image + caption + hashtags
 *
 * Supported brands: wihy, communitygroceries, vowels, snackingwell
 */

import { VertexAI, SchemaType } from "@google-cloud/vertexai";
import { getHealthContext } from "./ragClient";
import { generateGraphicContent } from "./geminiClient";
import { renderTemplateForBrand, listTemplateIds } from "../renderer/renderHtml";
import { screenshotHtml } from "../renderer/renderImage";
import { generateImage, isImagenAvailable } from "./imagenClient";

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

  // Validate template exists, fallback to hook_square
  const validTemplates = listTemplateIds();
  let templateId = validTemplates.includes(graphicContent.template)
    ? graphicContent.template
    : graphicContent.template === "ai_photo" ? "ai_photo" : "hook_square";

  // Image-first mode: if we have a viable photo prompt, bias toward photo-led templates.
  const imageFirstEnabled = (process.env.SHANIA_IMAGE_FIRST_MODE || "true").toLowerCase() !== "false";
  const nonPhotoDataTemplates = new Set(["stat_card", "research_card", "ingredient_breakdown", "comparison_split"]);
  const hasPhotoQuery = Boolean(graphicContent.photoQuery && graphicContent.photoQuery.trim().length > 0);
  if (
    imageFirstEnabled
    && isImagenAvailable()
    && hasPhotoQuery
    && templateId !== "ai_photo"
    && templateId !== "photo_overlay"
    && templateId !== "photo_caption"
    && !nonPhotoDataTemplates.has(templateId)
  ) {
    templateId = Math.random() < 0.55 ? "photo_overlay" : "photo_caption";
    logger.info(`Post pipeline [${brand.id}]: image-first promoted template to ${templateId}`);
  }

  // If ai_photo mode: generate standalone Imagen image (no template wrapping)
  if (templateId === "ai_photo" && graphicContent.photoQuery && isImagenAvailable()) {
    try {
      logger.info(`Post pipeline [${brand.id}]: generating standalone Imagen photo for "${graphicContent.photoQuery}"...`);
      const imagenResult = await generateImage({ prompt: graphicContent.photoQuery, aspectRatio: "1:1" });

      const elapsed = Date.now() - startTime;
      logger.info(`Post pipeline [${brand.id}] complete (ai_photo) in ${elapsed}ms (${imagenResult.imageBytes.length} bytes)`);

      return {
        imageBytes: imagenResult.imageBytes,
        mimeType: imagenResult.mimeType,
        caption: plan.caption,
        hashtags: combinedHashtags,
        ragContext: ragFacts || undefined,
        templateId: "ai_photo",
        brand: brand.id,
      };
    } catch (err: unknown) {
      logger.warn(`Imagen generation failed — falling back to hook_square: ${err instanceof Error ? err.message : String(err)}`);
      templateId = "hook_square";
    }
  } else if (templateId === "ai_photo") {
    // ai_photo without query or Imagen unavailable — fallback
    templateId = "hook_square";
  }

  // Photo templates (photo_overlay, photo_caption): generate Imagen photo then embed in template
  const isPhotoTemplate = templateId === "photo_overlay" || templateId === "photo_caption";
  let photoUrl: string | undefined;

  if (isPhotoTemplate && graphicContent.photoQuery && isImagenAvailable()) {
    try {
      logger.info(`Post pipeline [${brand.id}]: generating Imagen photo for ${templateId}...`);
      const imagenResult = await generateImage({ prompt: graphicContent.photoQuery, aspectRatio: "1:1" });
      photoUrl = `data:${imagenResult.mimeType};base64,${Buffer.from(imagenResult.imageBytes).toString("base64")}`;
      logger.info(`Post pipeline [${brand.id}]: Imagen photo generated (${imagenResult.imageBytes.length} bytes)`);
    } catch (err: unknown) {
      logger.warn(`Imagen photo generation failed for ${templateId} — falling back to hook_square: ${err instanceof Error ? err.message : String(err)}`);
      templateId = "hook_square";
    }
  } else if (isPhotoTemplate) {
    // Photo template but no query or Imagen unavailable — fallback
    logger.warn(`Photo template ${templateId} without photoQuery or Imagen — falling back to hook_square`);
    templateId = "hook_square";
  }

  // Template-based path: render branded template → Puppeteer screenshot
  logger.info(`Post pipeline [${brand.id}]: rendering template "${templateId}"...`);
  const templateData: TemplateData = {
    headline: graphicContent.headline,
    subtext: graphicContent.subtext,
    cta: graphicContent.cta,
    theme: (graphicContent.theme as TemplateData["theme"]) || "wihy_default",
    artDirection: (graphicContent.artDirection as TemplateData["artDirection"]) || undefined,
    quote: graphicContent.quote,
    attribution: graphicContent.attribution,
    statNumber: graphicContent.statNumber,
    statLabel: graphicContent.statLabel,
    dataPoints: graphicContent.dataPoints,
    source: graphicContent.source,
    photoUrl,
  };

  const html = renderTemplateForBrand(templateId, templateData, brand, outputSize);
  const finalImage = await screenshotHtml({ html, outputSize, format: "png" });

  const elapsed = Date.now() - startTime;
  logger.info(`Post pipeline [${brand.id}] complete in ${elapsed}ms (${finalImage.length} bytes)`);

  return {
    imageBytes: finalImage,
    mimeType: "image/png",
    caption: plan.caption,
    hashtags: combinedHashtags,
    ragContext: ragFacts || undefined,
    templateId,
    brand: brand.id,
  };
}
