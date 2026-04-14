/**
 * generate.ts — POST /generate, /generate-post, /generate-from-prompt, and /generate-bulk endpoints.
 */

import { Router, Request, Response } from "express";
import { renderTemplate } from "../../renderer/renderHtml";
import { screenshotHtml } from "../../renderer/renderImage";
import { uploadImage } from "../../storage/gcs";
import { generateGraphicContent } from "../../ai/geminiClient";
import { generatePost, planPostOnly } from "../../ai/postGenerator";
import { generateImage, isImagenAvailable } from "../../ai/imagenClient";
import { getPromptById } from "../../ai/promptLibrary";
import { FORMATS, DEFAULT_FORMAT, FormatKey } from "../../config/formats";
import { GenerateRequest, GenerateResult, ImageFormat, TemplateData } from "../../types";
import { enqueueBulkJob, getJob } from "../../jobs/bulkGenerate";
import { listTemplateIds } from "../../renderer/renderHtml";
import { logger } from "../../utils/logger";
import { getBrand, validateTemplateBrand, BRANDS, BrandId } from "../../config/brand";

const router = Router();

const BRAND_ENFORCEMENT_MODE = (process.env.BRAND_ENFORCEMENT_MODE || "warn").toLowerCase();
const SHANIA_BRAND_SCOPE = (process.env.SHANIA_BRAND_SCOPE || "").trim().toLowerCase();
const KNOWN_BRANDS = new Set(Object.keys(BRANDS));

function isEnforceMode(): boolean {
  return BRAND_ENFORCEMENT_MODE === "enforce";
}

function getScopedBrand(): string | undefined {
  if (!SHANIA_BRAND_SCOPE || SHANIA_BRAND_SCOPE === "all") return undefined;
  return SHANIA_BRAND_SCOPE;
}

function resolveBrandOrFail(req: Request, res: Response, rawBrand: unknown, required = true): string | undefined {
  const endpoint = req.path;
  const scopedBrand = getScopedBrand();
  const brand = typeof rawBrand === "string" ? rawBrand.trim().toLowerCase() : "";

  if (!brand) {
    if (required && isEnforceMode()) {
      res.status(400).json({
        error: "brand is required",
        endpoint,
      });
      return undefined;
    }
    const fallback = scopedBrand || "wihy";
    logger.warn(`Brand missing for ${endpoint}; using ${fallback} in ${BRAND_ENFORCEMENT_MODE} mode`);
    return fallback;
  }

  if (!KNOWN_BRANDS.has(brand)) {
    if (isEnforceMode()) {
      res.status(400).json({
        error: `Unknown brand: ${brand}`,
        availableBrands: Array.from(KNOWN_BRANDS),
      });
      return undefined;
    }
    const fallback = scopedBrand || "wihy";
    logger.warn(`Unknown brand \"${brand}\" for ${endpoint}; using ${fallback} in ${BRAND_ENFORCEMENT_MODE} mode`);
    return fallback;
  }

  if (scopedBrand && brand !== scopedBrand) {
    if (isEnforceMode()) {
      res.status(403).json({
        error: `Brand \"${brand}\" is not allowed for this instance scope \"${scopedBrand}\"`,
      });
      return undefined;
    }
    logger.warn(`Cross-scope brand ${brand} for ${endpoint}; forcing ${scopedBrand} in ${BRAND_ENFORCEMENT_MODE} mode`);
    return scopedBrand;
  }

  return brand;
}

/**
 * POST /generate
 * Generate a single graphic from template + data.
 */
router.post("/generate", async (req: Request, res: Response): Promise<void> => {
  try {
    const { templateId, data, format, outputSize, brand } = req.body as GenerateRequest & { brand?: string };
    const resolvedBrand = resolveBrandOrFail(req, res, brand, false);
    if (brand !== undefined && !resolvedBrand) return;

    if (!templateId || !data?.headline) {
      res.status(400).json({ error: "templateId and data.headline are required" });
      return;
    }

    const validTemplates = listTemplateIds();
    if (!validTemplates.includes(templateId)) {
      res.status(400).json({
        error: `Unknown template: ${templateId}`,
        available: validTemplates,
      });
      return;
    }

    const imgFormat: ImageFormat = format || "png";
    const size: FormatKey = outputSize || DEFAULT_FORMAT;
    if (!FORMATS[size]) {
      res.status(400).json({
        error: `Unknown outputSize: ${size}`,
        available: Object.keys(FORMATS),
      });
      return;
    }

    if (resolvedBrand) {
      const templateCheck = validateTemplateBrand(templateId, resolvedBrand);
      if (!templateCheck.valid) {
        res.status(400).json({ error: templateCheck.reason });
        return;
      }
    }

    const html = renderTemplate(templateId, data, size, resolvedBrand);
    const buffer = await screenshotHtml({ html, outputSize: size, format: imgFormat });

    let uploaded: { id: string; publicUrl: string } | null = null;
    try {
      uploaded = await uploadImage(buffer, imgFormat, templateId);
    } catch (uploadErr) {
      logger.warn(`GCS upload failed, returning image inline: ${uploadErr}`);
    }

    const spec = FORMATS[size];

    if (uploaded) {
      const result: GenerateResult = {
        id: uploaded.id,
        templateId,
        url: uploaded.publicUrl,
        format: imgFormat,
        width: spec.width,
        height: spec.height,
        createdAt: new Date().toISOString(),
      };
      res.json(result);
    } else {
      // Fallback: return image directly as raw binary
      const mime = imgFormat === "webp" ? "image/webp" : "image/png";
      res.writeHead(200, {
        "Content-Type": mime,
        "Content-Length": buffer.length,
        "Content-Disposition": `inline; filename="graphic.${imgFormat}"`,
      });
      res.end(buffer);
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Generate failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * POST /generate-from-prompt
 * Use Gemini to generate content, then render the graphic.
 */
router.post("/generate-from-prompt", async (req: Request, res: Response): Promise<void> => {
  try {
    const { prompt, promptId, templateHint, format, outputSize, brand } = req.body;
    const resolvedBrand = resolveBrandOrFail(req, res, brand, true);
    if (!resolvedBrand) return;

    const actualPrompt = promptId
      ? getPromptById(promptId)?.prompt
      : prompt;

    if (!actualPrompt) {
      res.status(400).json({ error: "prompt or valid promptId required" });
      return;
    }

    const hint = templateHint || (promptId ? getPromptById(promptId)?.suggestedTemplate : undefined);
    const brandProfile = getBrand(resolvedBrand as BrandId);
    const content = await generateGraphicContent(actualPrompt, hint, brandProfile);

    const templateId = content.template;
    const validTemplates = listTemplateIds();
    if (!validTemplates.includes(templateId)) {
      res.status(400).json({
        error: `Gemini suggested unknown template: ${templateId}`,
        geminiResponse: content,
        available: validTemplates,
      });
      return;
    }

    const templateCheck = validateTemplateBrand(templateId, resolvedBrand);
    if (!templateCheck.valid) {
      res.status(400).json({ error: templateCheck.reason, geminiResponse: content });
      return;
    }

    const data: TemplateData = {
      headline: content.headline,
      subtext: content.subtext,
      cta: content.cta,
      theme: (content.theme as TemplateData["theme"]) || "wihy_default",
      quote: content.quote,
      attribution: content.attribution,
    };

    const imgFormat: ImageFormat = format || "png";
    const size: FormatKey = outputSize || DEFAULT_FORMAT;

    const html = renderTemplate(templateId, data, size, resolvedBrand);
    const buffer = await screenshotHtml({ html, outputSize: size, format: imgFormat });

    let uploaded: { id: string; publicUrl: string } | null = null;
    try {
      uploaded = await uploadImage(buffer, imgFormat, templateId);
    } catch (uploadErr) {
      logger.warn(`GCS upload failed, returning image inline: ${uploadErr}`);
    }

    const spec = FORMATS[size];

    if (uploaded) {
      res.json({
        id: uploaded.id,
        templateId,
        url: uploaded.publicUrl,
        format: imgFormat,
        width: spec.width,
        height: spec.height,
        createdAt: new Date().toISOString(),
        geminiContent: content,
      });
    } else {
      const mime = imgFormat === "webp" ? "image/webp" : "image/png";
      res.writeHead(200, {
        "Content-Type": mime,
        "Content-Length": buffer.length,
        "Content-Disposition": `inline; filename="graphic.${imgFormat}"`,
      });
      res.end(buffer);
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Generate from prompt failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * POST /plan-post
 * Text-only content planning: RAG context → Gemini copywriting. No image generation.
 * Returns caption, hashtags, and the image prompt that would be used.
 */
router.post("/plan-post", async (req: Request, res: Response): Promise<void> => {
  try {
    const { prompt, brand, brandKey } = req.body;
    const resolvedBrand = resolveBrandOrFail(req, res, brand || brandKey, true);
    if (!resolvedBrand) return;

    if (!prompt) {
      res.status(400).json({ error: "prompt is required" });
      return;
    }

    const plan = await planPostOnly(prompt, resolvedBrand);

    res.json({
      status: "planned",
      caption: plan.caption,
      hashtags: plan.hashtags.map((h) => `#${h}`),
      topicHint: plan.topicHint || null,
      brand: plan.brand,
      ragContext: plan.ragContext || null,
      createdAt: new Date().toISOString(),
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Plan post failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * POST /generate-post
 * Full AI pipeline: RAG context → Gemini copywriting → branded template graphic.
 * Supports multi-brand: wihy (default), communitygroceries, vowels, snackingwell.
 */
router.post("/generate-post", async (req: Request, res: Response): Promise<void> => {
  try {
    const {
      prompt,
      outputSize,
      brand,
      brandKey,
      platforms,
      scheduledTime,
      dryRun = false,
    } = req.body;
    const brandId = resolveBrandOrFail(req, res, brand || brandKey, true);
    if (!brandId) return;

    const targetPlatforms: PostPlatform[] = Array.isArray(platforms) && platforms.length
      ? platforms as PostPlatform[]
      : defaultPlatformsForBrand(brandId);

    if (!prompt) {
      res.status(400).json({ error: "prompt is required" });
      return;
    }

    const size: FormatKey = outputSize || DEFAULT_FORMAT;
    if (!FORMATS[size]) {
      res.status(400).json({
        error: `Unknown outputSize: ${size}`,
        available: Object.keys(FORMATS),
      });
      return;
    }

    const post = await generatePost(prompt, size, brandId);

    // Try to upload to GCS
    let uploaded: { id: string; publicUrl: string } | null = null;
    try {
      uploaded = await uploadImage(post.imageBytes, "png", "ai-post");
    } catch (uploadErr) {
      logger.warn(`GCS upload failed for post: ${uploadErr}`);
    }

    const spec = FORMATS[size];

    const fullCaption = `${post.caption}\n\n${post.hashtags.map((h) => `#${h}`).join(" ")}`;
    const deliveryResults = await deliverToPlatforms({
      platforms: targetPlatforms,
      imageUrl: uploaded?.publicUrl,
      message: fullCaption,
      brandId,
      scheduledTime,
      dryRun,
    });

    res.json({
      id: uploaded?.id || "local",
      status: "generated",
      imageUrl: uploaded?.publicUrl || undefined,
      imageBase64: uploaded ? undefined : post.imageBytes.toString("base64"),
      mimeType: post.mimeType,
      width: spec.width,
      height: spec.height,
      caption: post.caption,
      hashtags: post.hashtags.map((h) => `#${h}`),
      brand: post.brand,
      ragContext: post.ragContext || null,
      templateId: post.templateId,
      delivery: deliveryResults,
      dryRun,
      createdAt: new Date().toISOString(),
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Generate post failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * POST /generate-bulk
 * Enqueue a batch of generation requests.
 */
router.post("/generate-bulk", async (req: Request, res: Response): Promise<void> => {
  try {
    const { items } = req.body;

    if (!Array.isArray(items) || items.length === 0) {
      res.status(400).json({ error: "items array is required" });
      return;
    }

    if (items.length > 50) {
      res.status(400).json({ error: "Max 50 items per bulk request" });
      return;
    }

    for (let i = 0; i < items.length; i++) {
      const item = items[i] as GenerateRequest & { brand?: string };
      const resolvedBrand = resolveBrandOrFail(req, res, item.brand, true);
      if (!resolvedBrand) return;
      const templateCheck = validateTemplateBrand(item.templateId, resolvedBrand);
      if (!templateCheck.valid) {
        res.status(400).json({
          error: `Bulk item ${i}: ${templateCheck.reason}`,
        });
        return;
      }
      item.brand = resolvedBrand;
    }

    const job = enqueueBulkJob(items);
    res.status(202).json({
      jobId: job.id,
      status: job.status,
      itemCount: items.length,
      statusUrl: `/jobs/${job.id}`,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Bulk generate failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * GET /jobs/:id
 * Check status of a bulk generation job.
 */
router.get("/jobs/:id", (req: Request<{id: string}>, res: Response): void => {
  const job = getJob(req.params.id);
  if (!job) {
    res.status(404).json({ error: "Job not found" });
    return;
  }
  res.json(job);
});


// ── Orchestrated Pipeline: Alex → Shania (content + page posts) ─────────────

const ALEX_URL = process.env.ALEX_URL || "https://wihy-alex-n4l2vldq3q-uc.a.run.app";
const SHANIA_ENGAGEMENT_URL =
  process.env.SHANIA_ENGAGEMENT_URL || "https://wihy-shania-12913076533.us-central1.run.app";
const ADMIN_TOKEN = process.env.INTERNAL_ADMIN_TOKEN || "";
const BRAND_ENGAGEMENT_URLS: Record<string, string> = {
  wihy: process.env.SHANIA_ENGAGEMENT_URL_WIHY || "https://wihy-shania-wihy-n4l2vldq3q-uc.a.run.app",
  communitygroceries: process.env.SHANIA_ENGAGEMENT_URL_CG || "https://wihy-shania-cg-n4l2vldq3q-uc.a.run.app",
  vowels: process.env.SHANIA_ENGAGEMENT_URL_VOWELS || "https://wihy-shania-vowels-n4l2vldq3q-uc.a.run.app",
  childrennutrition: process.env.SHANIA_ENGAGEMENT_URL_CN || "https://wihy-shania-cn-n4l2vldq3q-uc.a.run.app",
  parentingwithchrist: process.env.SHANIA_ENGAGEMENT_URL_PWC || "https://wihy-shania-pwc-n4l2vldq3q-uc.a.run.app",
  otakulounge: process.env.SHANIA_ENGAGEMENT_URL_OTAKU || process.env.SHANIA_ENGAGEMENT_URL_WIHY || "https://wihy-shania-wihy-n4l2vldq3q-uc.a.run.app",
};

function resolvePostingBrandId(rawBrandId: string): string {
  const profile = getBrand(rawBrandId);
  if (BRAND_ENGAGEMENT_URLS[profile.id]) {
    return profile.id;
  }
  if (profile.parentBrand && BRAND_ENGAGEMENT_URLS[profile.parentBrand]) {
    return profile.parentBrand;
  }
  return profile.id;
}

function defaultPlatformsForBrand(brandId: string): PostPlatform[] {
  const brandProfile = getBrand(brandId);
  if (brandProfile.postingEnabled === false) {
    return [];
  }
  return ["facebook", "instagram", "threads"];
}

type PostPlatform = "facebook" | "linkedin" | "twitter" | "instagram" | "tiktok" | "threads";
/** Facebook/LinkedIn/Threads/Instagram use Shania engagement. */
const PAGE_POSTING: Set<PostPlatform> = new Set(["facebook", "linkedin", "threads", "instagram"]);
const SOCIAL_POSTING: Set<PostPlatform> = new Set(["twitter", "tiktok"]);

interface DeliverParams {
  platforms: PostPlatform[];
  imageUrl?: string;
  message: string;
  brandId: string;
  scheduledTime?: string;
  dryRun: boolean;
}

async function deliverToPlatforms(params: DeliverParams): Promise<Record<string, unknown>> {
  const deliveryResults: Record<string, unknown> = {};
  const brandProfile = getBrand(params.brandId);
  const postingBrandId = resolvePostingBrandId(params.brandId);
  const brandScopedShaniaUrl = BRAND_ENGAGEMENT_URLS[postingBrandId] || SHANIA_ENGAGEMENT_URL;

  // Brand safety guard — block posting for brands not yet launched
  if (brandProfile.postingEnabled === false) {
    for (const platform of params.platforms) {
      deliveryResults[platform] = { status: "blocked", reason: "brand_posting_disabled" };
    }
    return deliveryResults;
  }

  if (params.dryRun) {
    for (const platform of params.platforms) {
      deliveryResults[platform] = { status: "dry_run", wouldDeliver: true };
    }
    return deliveryResults;
  }

  if (!params.imageUrl) {
    for (const platform of params.platforms) {
      deliveryResults[platform] = { status: "skipped", reason: "image_upload_failed" };
    }
    return deliveryResults;
  }

  if (!ADMIN_TOKEN) {
    for (const platform of params.platforms) {
      deliveryResults[platform] = { status: "failed", reason: "missing_admin_token" };
    }
    return deliveryResults;
  }

  for (const platform of params.platforms) {
    try {
      if (PAGE_POSTING.has(platform)) {
        const endpoint = platform === "linkedin"
          ? `${brandScopedShaniaUrl}/api/labat/linkedin/posts`
          : platform === "threads"
          ? `${brandScopedShaniaUrl}/api/labat/posts/threads`
          : platform === "instagram"
          ? `${brandScopedShaniaUrl}/api/labat/posts/instagram`
          : `${brandScopedShaniaUrl}/api/labat/posts`;

        if (platform === "facebook" && !brandProfile.facebookPageId) {
          deliveryResults[platform] = { status: "skipped", reason: "no_facebook_page_configured" };
          continue;
        }

        // Threads has a 500-char limit; truncate with ellipsis if needed
        const threadsText = params.message.length > 500
          ? params.message.slice(0, 497) + "..."
          : params.message;

        const payload = platform === "linkedin"
          ? { message: params.message, scheduled_publish_time: params.scheduledTime }
          : platform === "threads"
          ? { text: threadsText, image_url: params.imageUrl, page_id: brandProfile.facebookPageId || undefined }
          : platform === "instagram"
          ? { caption: params.message, image_url: params.imageUrl, page_id: brandProfile.facebookPageId || undefined }
          : { message: params.message, image_url: params.imageUrl, page_id: brandProfile.facebookPageId || undefined };

        const resp = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Admin-Token": ADMIN_TOKEN },
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(platform === "instagram" ? 60000 : 30000),
        });

        if (resp.ok) {
          deliveryResults[platform] = {
            status: "delivered",
            service: "shania-brand",
            postingBrand: postingBrandId,
            endpoint,
            result: await resp.json(),
          };
        } else {
          const errorText = await resp.text();
          deliveryResults[platform] = {
            status: "failed",
            service: "shania-brand",
            postingBrand: postingBrandId,
            endpoint,
            code: resp.status,
            details: errorText,
          };
        }
      } else if (SOCIAL_POSTING.has(platform)) {
        const resp = await fetch(`${SHANIA_ENGAGEMENT_URL}/api/engagement/post`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Admin-Token": ADMIN_TOKEN },
          body: JSON.stringify({
            platform,
            image_url: params.imageUrl,
            message: params.message,
            scheduled_publish_time: params.scheduledTime,
          }),
          signal: AbortSignal.timeout(30000),
        });

        if (resp.ok) {
          deliveryResults[platform] = { status: "delivered", service: "shania", result: await resp.json() };
        } else {
          const errorText = await resp.text();
          deliveryResults[platform] = {
            status: "failed",
            service: "shania",
            code: resp.status,
            details: errorText,
          };
        }
      } else {
        deliveryResults[platform] = { status: "unknown_platform" };
      }
    } catch (err) {
      deliveryResults[platform] = { status: "error", error: String(err) };
    }
  }

  return deliveryResults;
}

/**
 * POST /orchestrate-post
 * Full pipeline: Alex signals → Shania content + branded template graphic → deliver to platform(s).
 *
 * Body: { prompt, brand?, platforms?: string[], outputSize?, scheduledTime?, dryRun?: boolean }
 *
 * Flow:
 *   1. Alex provides realtime SEO signals (trending hashtags, keywords)
 *   2. Shania generates caption + hashtags via RAG + Gemini
 *   3. Gemini generates structured graphic content → rendered via branded HTML templates
 *   4. Uploaded to GCS
 *   5. Delivered directly to each platform:
 *      - facebook/linkedin/threads/instagram → brand-scoped Shania engagement (/api/labat/posts routes)
 *      - twitter/tiktok → Shania engagement (/api/engagement/post)
 */
router.post("/orchestrate-post", async (req: Request, res: Response): Promise<void> => {
  try {
    const {
      prompt,
      brand,
      brandKey,
      platforms,
      outputSize,
      scheduledTime,
      dryRun = false,
    } = req.body;
    const brandId = resolveBrandOrFail(req, res, brand || brandKey, true);
    if (!brandId) return;

    const targetPlatforms: PostPlatform[] = Array.isArray(platforms) && platforms.length
      ? platforms as PostPlatform[]
      : defaultPlatformsForBrand(brandId);

    if (!prompt) {
      res.status(400).json({ error: "prompt is required" });
      return;
    }

    const size: FormatKey = outputSize || DEFAULT_FORMAT;
    const results: Record<string, unknown> = {};

    // Step 1: Alex realtime signals
    let alexSignals: { hashtags?: string[] } | null = null;
    if (ADMIN_TOKEN) {
      try {
        const params = new URLSearchParams({ query: prompt, brand: brandId, limit: "8" });
        const alexResp = await fetch(`${ALEX_URL}/api/alex/realtime-signals?${params}`, {
          headers: { "X-Admin-Token": ADMIN_TOKEN },
          signal: AbortSignal.timeout(10000),
        });
        if (alexResp.ok) {
          alexSignals = await alexResp.json() as { hashtags?: string[] };
          results.alex = { status: "ok", hashtags: alexSignals?.hashtags?.length || 0 };
        } else {
          results.alex = { status: "unavailable", code: alexResp.status };
        }
      } catch (err) {
        results.alex = { status: "unavailable", error: String(err) };
      }
    } else {
      results.alex = { status: "skipped", reason: "no admin token" };
    }

    // Step 2: Shania generates content + asset
    const post = await generatePost(prompt, size, brandId);

    // Merge Alex hashtags with Shania hashtags
    if (alexSignals?.hashtags?.length) {
      const existing = new Set(post.hashtags.map((h) => h.toLowerCase()));
      for (const tag of alexSignals.hashtags) {
        const clean = tag.replace(/^#+/, "").trim();
        if (clean && !existing.has(clean.toLowerCase())) {
          post.hashtags.push(clean);
          existing.add(clean.toLowerCase());
        }
        if (post.hashtags.length >= 12) break;
      }
    }

    // Step 3: Upload asset to GCS
    const ext = post.mimeType.includes("png") ? "png" : "webp";
    let uploaded: { id: string; publicUrl: string } | null = null;
    try {
      uploaded = await uploadImage(post.imageBytes, ext as "png" | "webp", "orchestrated-post");
    } catch (uploadErr) {
      logger.warn(`GCS upload failed: ${uploadErr}`);
    }

    results.shania = {
      status: "ok",
      captionLength: post.caption.length,
      hashtags: post.hashtags.length,
      imageSize: post.imageBytes.length,
      imageUrl: uploaded?.publicUrl || null,
    };

    // Step 4: Deliver to platforms (unless dry run)
    const fullCaption = `${post.caption}\n\n${post.hashtags.map((h) => `#${h}`).join(" ")}`;
    const deliveryResults = await deliverToPlatforms({
      platforms: targetPlatforms,
      imageUrl: uploaded?.publicUrl,
      message: fullCaption,
      brandId,
      scheduledTime,
      dryRun,
    });

    results.delivery = deliveryResults;

    res.json({
      status: "posted",
      caption: post.caption,
      hashtags: post.hashtags.map((h) => `#${h}`),
      brand: post.brand,
      imageUrl: uploaded?.publicUrl || null,
      pipeline: results,
      dryRun,
      createdAt: new Date().toISOString(),
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Orchestrate post failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * POST /generate-hero-image
 * Generate a blog hero image using Imagen 4.0. Brand-aware styling.
 * Body: { topic, brand?, slug? }
 *
 * Returns: { id, url, mimeType, width, height, brand, createdAt }
 */
router.post("/generate-hero-image", async (req: Request, res: Response): Promise<void> => {
  try {
    const { topic, brand, slug } = req.body;
    const brandId = resolveBrandOrFail(req, res, brand, true);
    if (!brandId) return;

    if (!topic) {
      res.status(400).json({ error: "topic is required" });
      return;
    }

    if (!isImagenAvailable()) {
      res.status(503).json({ error: "Imagen image generation not available — API key not configured" });
      return;
    }

    // Strip words that make AI generate text/labels in the image
    const textTriggers = /\b(label|labels|labeling|nutrition facts|ingredient list|food label|packaging|printed|text|reading|literacy|words|writing|sign|signage)\b/gi;
    let safeTopic = topic.substring(0, 120).replace(textTriggers, "").replace(/\s{2,}/g, " ").trim();
    if (!safeTopic) safeTopic = "healthy food photography";

    let styleNote: string;
    if (brandId === "communitygroceries" || brandId === "cg") {
      styleNote =
        "Bright, naturally lit overhead flat-lay of fresh groceries and ingredients " +
        "on a clean wooden kitchen counter. Warm morning sunlight from a window. " +
        "Focus on colorful whole foods, cutting boards, and simple kitchen props.";
    } else {
      styleNote =
        "Dark, dramatic food photography on a black or slate surface. " +
        "Moody directional lighting with deep shadows. Bold, scientific editorial feel. " +
        "Shot with a 50mm lens, shallow depth of field. " +
        "Only whole foods, fresh ingredients, and kitchen surfaces.";
    }

    const prompt =
      `Editorial food photograph inspired by: ${safeTopic}. ` +
      `${styleNote} ` +
      `Photorealistic, shot on a Canon EOS R5, RAW photo look. ` +
      `Absolutely no human body parts, no people, no hands, no fingers, no faces.`;

    const result = await generateImage({
      prompt,
      aspectRatio: "16:9",
      sampleCount: 1,
    });

    // Upload to GCS
    const label = slug || "hero-image";
    let uploaded: { id: string; publicUrl: string } | null = null;
    try {
      uploaded = await uploadImage(result.imageBytes, "jpeg", label);
    } catch (uploadErr) {
      logger.warn(`GCS upload failed for hero image: ${uploadErr}`);
    }

    if (uploaded) {
      res.json({
        id: uploaded.id,
        url: uploaded.publicUrl,
        mimeType: "image/jpeg",
        width: 1792,
        height: 1024,
        brand: brandId,
        slug: slug || null,
        createdAt: new Date().toISOString(),
      });
    } else {
      // Fallback: return image as base64
      res.json({
        id: "local",
        imageBase64: result.imageBytes.toString("base64"),
        mimeType: result.mimeType,
        width: 1792,
        height: 1024,
        brand: brandId,
        slug: slug || null,
        createdAt: new Date().toISOString(),
      });
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Generate hero image failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

export default router;
