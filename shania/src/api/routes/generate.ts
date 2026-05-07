/**
 * generate.ts — Gemini/Imagen social generation and delivery endpoints.
 */

import { Router, Request, Response } from "express";
import fs from "fs";
import path from "path";
import { uploadImage, listLibraryAssets, moveAsset } from "../../storage/gcs";
import { generatePost, planPostOnly } from "../../ai/postGenerator";
import { generateImage, isImagenAvailable } from "../../ai/imagenClient";
import { FORMATS, DEFAULT_FORMAT, FormatKey } from "../../config/formats";
import { logger } from "../../utils/logger";
import { getBrand, BRANDS } from "../../config/brand";
import {
  getCanvaDesign,
  createOrResizeCanvaDesign,
  uploadImageAsCanvaAsset,
  autofillBrandTemplate,
  CanvaAutofillField,
  listCanvaBrandTemplatesWithDatasets,
  getCanvaBrandTemplateDataset,
} from "../../services/canvaApi";

const router = Router();

function listTemplateDirectories(): string[] {
  try {
    // In runtime build, templates are copied to dist/templates.
    const templatesRoot = path.resolve(__dirname, "../../templates");
    if (!fs.existsSync(templatesRoot)) return [];
    return fs
      .readdirSync(templatesRoot, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort();
  } catch (err) {
    logger.warn(`Could not list templates directory: ${err}`);
    return [];
  }
}

function escapeCsvCell(value: unknown): string {
  const text = value == null ? "" : String(value);
  if (!/[",\n]/.test(text)) return text;
  return `"${text.replace(/"/g, '""')}"`;
}

function buildBrandTemplateMappingCsv(templates: Array<{
  id: string;
  title?: string;
  viewUrl?: string;
  createUrl?: string;
  fields: Array<{ name: string; type?: string; label?: string }>;
}>): string {
  const header = [
    "template_id",
    "template_title",
    "field_name",
    "field_type",
    "field_label",
    "view_url",
    "create_url",
  ];
  const rows = templates.flatMap((template) => {
    const fields = template.fields.length ? template.fields : [{ name: "", type: "", label: "" }];
    return fields.map((field) => [
      template.id,
      template.title || "",
      field.name || "",
      field.type || "",
      field.label || "",
      template.viewUrl || "",
      template.createUrl || "",
    ]);
  });

  return [header, ...rows].map((row) => row.map(escapeCsvCell).join(",")).join("\n");
}

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
 * GET /templates
 * Returns available output formats + template directories shipped in this service.
 */
router.get("/templates", (_req: Request, res: Response): void => {
  res.json({
    status: "ok",
    defaultFormat: DEFAULT_FORMAT,
    formats: FORMATS,
    templateDirectories: listTemplateDirectories(),
    generatedImageTemplateId: "gemini_imagen",
    assetLibraryTemplateId: "asset_library",
  });
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
 * Full AI pipeline: RAG context → Gemini copywriting → Imagen graphic.
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

// ── Orchestrated Pipeline: Alex → Shania (content + page posts) ─────────────

const ALEX_URL = process.env.ALEX_URL || "https://wihy-alex-n4l2vldq3q-uc.a.run.app";
const SHANIA_ENGAGEMENT_URL =
  process.env.SHANIA_ENGAGEMENT_URL || "https://wihy-shania-12913076533.us-central1.run.app";
const ADMIN_TOKEN = process.env.INTERNAL_ADMIN_TOKEN || "";
const CANVA_DEFAULT_SOURCE_DESIGN_ID = (process.env.CANVA_DEFAULT_SOURCE_DESIGN_ID || "").trim();
const CANVA_DEFAULT_BRAND_TEMPLATE_ID = (process.env.CANVA_DEFAULT_BRAND_TEMPLATE_ID || "").trim();
const CANVA_BRAND_TEMPLATE_FIELDS = {
  headline: (process.env.CANVA_FIELD_HEADLINE || "headline").trim(),
  subheadline: (process.env.CANVA_FIELD_SUBHEADLINE || "subheadline").trim(),
  cta: (process.env.CANVA_FIELD_CTA || "cta").trim(),
  image: (process.env.CANVA_FIELD_IMAGE || "hero_image").trim(),
  brand: (process.env.CANVA_FIELD_BRAND || "brand").trim(),
};
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
  mediaType?: "image" | "video";
  message: string;
  brandId: string;
  scheduledTime?: string;
  dryRun: boolean;
}

function isAdminAuthorized(req: Request): boolean {
  if (!ADMIN_TOKEN) return false;
  return req.headers["x-admin-token"] === ADMIN_TOKEN;
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
      deliveryResults[platform] = { status: "skipped", reason: "asset_upload_failed" };
    }
    return deliveryResults;
  }

  const mediaType = params.mediaType || "image";
  const isVideo = mediaType === "video";

  if (!ADMIN_TOKEN) {
    for (const platform of params.platforms) {
      deliveryResults[platform] = { status: "failed", reason: "missing_admin_token" };
    }
    return deliveryResults;
  }

  for (const platform of params.platforms) {
    try {
      if (PAGE_POSTING.has(platform)) {
        if (isVideo && platform === "threads") {
          deliveryResults[platform] = { status: "skipped", reason: "video_not_supported_for_threads" };
          continue;
        }
        if (isVideo && platform === "linkedin") {
          deliveryResults[platform] = { status: "skipped", reason: "video_not_supported_for_linkedin_route" };
          continue;
        }

        const endpoint = platform === "linkedin"
          ? `${brandScopedShaniaUrl}/api/labat/linkedin/posts`
          : platform === "threads"
          ? `${brandScopedShaniaUrl}/api/labat/posts/threads`
          : platform === "instagram" && isVideo
          ? `${brandScopedShaniaUrl}/api/labat/posts/instagram/video`
          : platform === "instagram"
          ? `${brandScopedShaniaUrl}/api/labat/posts/instagram`
          : platform === "facebook" && isVideo
          ? `${brandScopedShaniaUrl}/api/labat/posts/video`
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
          : platform === "instagram" && isVideo
          ? {
            caption: params.message,
            video_url: params.imageUrl,
            media_type: "REELS",
            page_id: brandProfile.facebookPageId || undefined,
          }
          : platform === "instagram"
          ? { caption: params.message, image_url: params.imageUrl, page_id: brandProfile.facebookPageId || undefined }
          : platform === "facebook" && isVideo
          ? {
            description: params.message,
            file_url: params.imageUrl,
            title: `Video post ${new Date().toISOString().slice(0, 10)}`,
            published: !params.scheduledTime,
            page_id: brandProfile.facebookPageId || undefined,
          }
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
        if (isVideo) {
          deliveryResults[platform] = { status: "skipped", reason: "video_not_supported_for_social_route" };
          continue;
        }
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
 * Full pipeline: Alex signals → Shania content + image asset → deliver to platform(s).
 *
 * Body: { prompt, brand?, platforms?: string[], outputSize?, scheduledTime?, dryRun?: boolean }
 *
 * Flow:
 *   1. Alex provides realtime SEO signals (trending hashtags, keywords)
 *   2. Shania generates caption + hashtags via RAG + Gemini
 *   3. Shania generates or reuses image asset and prepares platform-ready caption
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
      imageUrl,
      heroImage,
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
    const providedImageUrl =
      (typeof imageUrl === "string" && imageUrl.trim())
      || (typeof heroImage === "string" && heroImage.trim())
      || "";

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

    // Step 2: Shania generates content + asset (or reuses provided blog image URL)
    let caption = "";
    let hashtags: string[] = [];
    let imageUrlForDelivery: string | null = null;
    let responseBrand = brandId;

    if (providedImageUrl) {
      const plan = await planPostOnly(prompt, brandId);
      caption = plan.caption;
      hashtags = [...plan.hashtags];
      responseBrand = plan.brand;
      imageUrlForDelivery = providedImageUrl;

      if (alexSignals?.hashtags?.length) {
        const existing = new Set(hashtags.map((h) => h.toLowerCase()));
        for (const tag of alexSignals.hashtags) {
          const clean = tag.replace(/^#+/, "").trim();
          if (clean && !existing.has(clean.toLowerCase())) {
            hashtags.push(clean);
            existing.add(clean.toLowerCase());
          }
          if (hashtags.length >= 12) break;
        }
      }

      results.shania = {
        status: "ok",
        mode: "reuse-image",
        captionLength: caption.length,
        hashtags: hashtags.length,
        imageUrl: imageUrlForDelivery,
      };
    } else {
      const post = await generatePost(prompt, size, brandId);
      caption = post.caption;
      hashtags = [...post.hashtags];
      responseBrand = post.brand;

      // Merge Alex hashtags with Shania hashtags
      if (alexSignals?.hashtags?.length) {
        const existing = new Set(hashtags.map((h) => h.toLowerCase()));
        for (const tag of alexSignals.hashtags) {
          const clean = tag.replace(/^#+/, "").trim();
          if (clean && !existing.has(clean.toLowerCase())) {
            hashtags.push(clean);
            existing.add(clean.toLowerCase());
          }
          if (hashtags.length >= 12) break;
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
      imageUrlForDelivery = uploaded?.publicUrl || null;

      results.shania = {
        status: "ok",
        mode: "generated-image",
        captionLength: caption.length,
        hashtags: hashtags.length,
        imageSize: post.imageBytes.length,
        imageUrl: imageUrlForDelivery,
      };
    }

    // Step 4: Deliver to platforms (unless dry run)
    const fullCaption = `${caption}\n\n${hashtags.map((h) => `#${h}`).join(" ")}`;
    const deliveryResults = await deliverToPlatforms({
      platforms: targetPlatforms,
      imageUrl: imageUrlForDelivery || undefined,
      message: fullCaption,
      brandId,
      scheduledTime,
      dryRun,
    });

    results.delivery = deliveryResults;

    res.json({
      status: "posted",
      caption,
      hashtags: hashtags.map((h) => `#${h}`),
      brand: responseBrand,
      imageUrl: imageUrlForDelivery || null,
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

    // Strip words/phrases that make Imagen generate text, logos, or branded overlays in the image
    const textTriggers = /\b(label|labels|labeling|nutrition facts|ingredient list|food label|packaging|printed|text|reading|literacy|words|writing|sign|signage|checklist|framework|initiative|launch|program|guide|report|plan|brand|logo|branding|title|caption|headline|subtitle|banner|poster|flyer|infographic|chart|graph|diagram|steps?|tips?|tricks?)\b/gi;
    // Also strip parenthetical content like "(LAUNCH)" which triggers text overlays
    let safeTopic = topic.substring(0, 120).replace(/\([^)]*\)/g, "").replace(textTriggers, "").replace(/\s{2,}/g, " ").trim();
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

/**
 * GET /canva/design/:designId
 * Fetch metadata and edit/view links for an existing Canva design.
 */
router.get("/canva/design/:designId", async (req: Request, res: Response): Promise<void> => {
  if (!isAdminAuthorized(req)) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  try {
    const designIdRaw = req.params.designId;
    const designId = (Array.isArray(designIdRaw) ? designIdRaw[0] : designIdRaw || "").trim();
    if (!designId) {
      res.status(400).json({ error: "designId is required" });
      return;
    }

    const design = await getCanvaDesign(designId);
    res.json({ status: "ok", design });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Canva design lookup failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * GET /canva/brand-templates
 * List all accessible Canva brand templates and their autofill fields.
 * Add ?format=csv to receive a flat CSV mapping for spreadsheet workflows.
 */
router.get("/canva/brand-templates", async (req: Request, res: Response): Promise<void> => {
  if (!isAdminAuthorized(req)) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  try {
    const templates = await listCanvaBrandTemplatesWithDatasets();
    const format = String(req.query.format || "json").toLowerCase();
    const csv = buildBrandTemplateMappingCsv(templates);

    if (format === "csv") {
      res.setHeader("Content-Type", "text/csv; charset=utf-8");
      res.setHeader("Content-Disposition", 'inline; filename="canva-brand-template-mapping.csv"');
      res.send(csv);
      return;
    }

    res.json({
      status: "ok",
      count: templates.length,
      templates,
      csv,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Canva brand template listing failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * POST /canva/resize-design
 * Create a Canva design for social dimensions, optionally by copying/resizing an
 * existing design when sourceDesignId is provided.
 *
 * Body:
 * {
 *   sourceDesignId?: string,
 *   title?: string,
 *   presetName?: string,
 *   width?: number,
 *   height?: number,
 *   platformPreset?: "instagram_post_4x5" | "instagram_square" | "instagram_story"
 * }
 */
router.post("/canva/resize-design", async (req: Request, res: Response): Promise<void> => {
  if (!isAdminAuthorized(req)) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  try {
    const {
      sourceDesignId,
      title,
      presetName,
      width,
      height,
      platformPreset,
    } = req.body as {
      sourceDesignId?: string;
      title?: string;
      presetName?: string;
      width?: number;
      height?: number;
      platformPreset?: string;
    };

    const platformMap: Record<string, { width: number; height: number }> = {
      instagram_post_4x5: { width: 1080, height: 1350 },
      instagram_square: { width: 1080, height: 1080 },
      instagram_story: { width: 1080, height: 1920 },
    };

    const mapped = platformPreset ? platformMap[platformPreset] : undefined;
    const resolvedWidth = Number(width || mapped?.width || 0);
    const resolvedHeight = Number(height || mapped?.height || 0);

    if (!presetName && (!resolvedWidth || !resolvedHeight)) {
      res.status(400).json({
        error: "Provide presetName or width+height/platformPreset",
        platformPresets: Object.keys(platformMap),
      });
      return;
    }

    const design = await createOrResizeCanvaDesign({
      sourceDesignId: typeof sourceDesignId === "string" ? sourceDesignId.trim() : undefined,
      title: typeof title === "string" ? title.trim() : undefined,
      presetName: typeof presetName === "string" && presetName.trim() ? presetName.trim() : undefined,
      width: resolvedWidth || undefined,
      height: resolvedHeight || undefined,
    });

    res.json({
      status: "ok",
      operation: sourceDesignId ? "copy-or-resize" : "create",
      request: {
        sourceDesignId: sourceDesignId || null,
        presetName: presetName || null,
        width: resolvedWidth || null,
        height: resolvedHeight || null,
        platformPreset: platformPreset || null,
      },
      design,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Canva resize workflow failed: ${message}`);
    res.status(500).json({ error: message });
  }
});


/**
 * POST /post-from-approved
 * Pull the oldest pre-approved asset from the GCS bucket and post it to platforms.
 *
 * Assets must be uploaded to asset-library/{brand}/approved/ beforehand.
 * After posting, the asset is moved to asset-library/{brand}/posted/.
 *
 * Body: { brand?, platforms?: string[], scheduledTime?, dryRun?: boolean }
 *
 * Used when SHANIA_POSTING_MODE=bucket-only — Shania posts only pre-approved
 * photos/graphics and never auto-generates content.
 */
router.post("/post-from-approved", async (req: Request, res: Response): Promise<void> => {
  if (!ADMIN_TOKEN) {
    res.status(503).json({ error: "INTERNAL_ADMIN_TOKEN not configured" });
    return;
  }
  const authHeader = req.headers["x-admin-token"];
  if (authHeader !== ADMIN_TOKEN) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  try {
    const { brand, platforms, scheduledTime, dryRun = false } = req.body as {
      brand?: string;
      platforms?: string[];
      scheduledTime?: string;
      dryRun?: boolean;
    };

    const brandId = resolveBrandOrFail(req, res, brand, false);
    if (!brandId) return;

    // List pre-approved assets for this brand (oldest first via ascending sort)
    const items = await listLibraryAssets({ brand: brandId, folder: "approved", limit: 50 });
    if (items.length === 0) {
      res.status(404).json({
        status: "no_assets",
        brand: brandId,
        message: `No approved assets found in asset-library/${brandId}/approved/. Upload photos to the bucket first.`,
      });
      return;
    }

    // Pick the oldest asset (sort ascending by updated time, take first)
    const sorted = [...items].sort((a, b) => (a.updated || "").localeCompare(b.updated || ""));
    const asset = sorted[0];
    const assetMediaType = (asset.contentType || "").toLowerCase().startsWith("video/") ? "video" : "image";

    // Generate caption + hashtags using the asset path as the prompt context
    const promptHint = asset.metadata?.caption || asset.metadata?.topic || `New post for ${brandId}`;
    const plan = await planPostOnly(promptHint, brandId);
    const caption = plan.caption;
    const hashtags = plan.hashtags;

    const targetPlatforms = (platforms && platforms.length > 0 ? platforms : defaultPlatformsForBrand(brandId)) as PostPlatform[];
    const fullCaption = `${caption}\n\n${hashtags.map((h) => `#${h}`).join(" ")}`;

    let deliveryResults: Record<string, unknown> = {};
    if (!dryRun) {
      deliveryResults = await deliverToPlatforms({
        platforms: targetPlatforms,
        imageUrl: asset.publicUrl,
        mediaType: assetMediaType,
        message: fullCaption,
        brandId,
        scheduledTime,
        dryRun: false,
      });

      // Move asset from approved/ to posted/
      const postedPath = asset.path.replace(
        /asset-library\/([^/]+)\/approved\//,
        `asset-library/$1/posted/`,
      );
      try {
        await moveAsset(asset.path, postedPath);
        logger.info(`Marked asset as posted: ${asset.path} → ${postedPath}`);
      } catch (moveErr) {
        logger.warn(`Could not move asset to posted/: ${moveErr}`);
      }
    }

    res.json({
      status: dryRun ? "dry_run" : "posted",
      brand: brandId,
      asset: { path: asset.path, publicUrl: asset.publicUrl, mediaType: assetMediaType, contentType: asset.contentType },
      caption,
      hashtags: hashtags.map((h) => `#${h}`),
      platforms: targetPlatforms,
      delivery: deliveryResults,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`post-from-approved failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * POST /canva/generate-post
 * Full end-to-end: Gemini caption + Imagen image → Canva asset upload → blank Canva design.
 * Returns the Canva design edit URL + uploaded asset URL.
 *
 * Body: { prompt, brand?, outputSize?, title?, sourceDesignId?, templateDesignId?,
 *         brandTemplateId?, autofillData?, headline?, subheadline?, cta? }
 *
 * Three modes:
 *   1. brandTemplateId (or CANVA_DEFAULT_BRAND_TEMPLATE_ID) → Autofill API
 *      → fully dynamic text + image substitution into a Canva Brand Template
 *   2. sourceDesignId / templateDesignId → clone existing design + insert image
 *   3. Neither → blank custom design at outputSize with image inserted
 */
router.post("/canva/generate-post", async (req: Request, res: Response): Promise<void> => {
  if (!isAdminAuthorized(req)) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  try {
    const {
      prompt,
      brand,
      brandKey,
      outputSize,
      title,
      sourceDesignId,
      templateDesignId,
      brandTemplateId,
      autofillData,
      headline,
      subheadline,
      cta,
      textOnlyTemplate,
      useAssetLibrary,
    } = req.body as {
      prompt?: string;
      brand?: string;
      brandKey?: string;
      outputSize?: string;
      title?: string;
      sourceDesignId?: string;
      templateDesignId?: string;
      brandTemplateId?: string;
      autofillData?: Record<string, CanvaAutofillField>;
      headline?: string;
      subheadline?: string;
      cta?: string;
      textOnlyTemplate?: boolean;
      useAssetLibrary?: boolean;
    };

    if (!prompt) {
      res.status(400).json({ error: "prompt is required" });
      return;
    }

    const brandId = resolveBrandOrFail(req, res, brand || brandKey, false) || "wihy";
    const size: FormatKey = (outputSize as FormatKey) || DEFAULT_FORMAT;
    const resolvedSourceDesignId =
      (typeof sourceDesignId === "string" && sourceDesignId.trim())
      || (typeof templateDesignId === "string" && templateDesignId.trim())
      || CANVA_DEFAULT_SOURCE_DESIGN_ID
      || undefined;
    const resolvedBrandTemplateId =
      (typeof brandTemplateId === "string" && brandTemplateId.trim())
      || CANVA_DEFAULT_BRAND_TEMPLATE_ID
      || undefined;

    if (!FORMATS[size]) {
      res.status(400).json({ error: `Unknown outputSize: ${size}`, available: Object.keys(FORMATS) });
      return;
    }

    if (!isImagenAvailable()) {
      res.status(503).json({ error: "Imagen image generation not available — GOOGLE_API_KEY not configured" });
      return;
    }

    // Step 1: Generate caption + image. By default we force Imagen, but callers can opt into
    // using the existing asset library (e.g. curated Labat food images).
    const originalEnv = process.env.SHANIA_USE_ASSET_LIBRARY;
    process.env.SHANIA_USE_ASSET_LIBRARY = useAssetLibrary ? "true" : "false";
    let post;
    try {
      post = await generatePost(prompt, size, brandId);
    } finally {
      process.env.SHANIA_USE_ASSET_LIBRARY = originalEnv ?? "true";
    }

    logger.info(`Canva generate-post: image generated (${post.imageBytes.length} bytes, ${post.mimeType})`);

    // Step 2: Upload image to GCS for a public URL
    const ext = post.mimeType.includes("png") ? "png" : "webp";
    let gcsUrl: string | null = null;
    try {
      const uploaded = await uploadImage(post.imageBytes, ext as "png" | "webp", "canva-post");
      gcsUrl = uploaded.publicUrl;
    } catch (uploadErr) {
      logger.warn(`GCS upload failed (non-fatal): ${uploadErr}`);
    }

    // Step 3: Upload image to Canva as an asset
    const assetName = title || `WIHY Post ${new Date().toISOString().slice(0, 10)}`;
    const canvaAsset = await uploadImageAsCanvaAsset(post.imageBytes, post.mimeType, assetName);
    logger.info(`Canva asset uploaded: ${canvaAsset.id}`);

    // Step 4: Create Canva design — Autofill brand template (preferred), clone, or blank
    const spec = FORMATS[size];
    let canvaDesign;
    let mode: "autofill" | "clone" | "blank";

    if (resolvedBrandTemplateId) {
      mode = "autofill";
      // Build autofill data: caller-provided autofillData wins; otherwise auto-build from
      // headline/subheadline/cta + the uploaded image asset.
      const autoBuilt: Record<string, CanvaAutofillField> = {};
      const f = CANVA_BRAND_TEMPLATE_FIELDS;
      const resolvedHeadline = (headline && headline.trim()) || post.caption?.split("\n")[0] || prompt;
      const resolvedSubheadline = (subheadline && subheadline.trim())
        || (post.caption && post.caption.split("\n").slice(1).join(" ").trim())
        || "";
      const resolvedCta = (cta && cta.trim()) || "Learn more";

      if (resolvedHeadline) autoBuilt[f.headline] = { type: "text", text: resolvedHeadline };
      if (resolvedSubheadline) autoBuilt[f.subheadline] = { type: "text", text: resolvedSubheadline };
      if (resolvedCta) autoBuilt[f.cta] = { type: "text", text: resolvedCta };
      const includeImageField = !textOnlyTemplate;
      if (includeImageField && f.image) {
        autoBuilt[f.image] = { type: "image", asset_id: canvaAsset.id };
      }
      if (brandId) autoBuilt[f.brand] = { type: "text", text: brandId };

      let finalData: Record<string, CanvaAutofillField> = {
        ...autoBuilt,
        ...(autofillData && typeof autofillData === "object" ? autofillData : {}),
      };

      // Keep autofill payload aligned with fields that actually exist on the template.
      // Canva can return unnamed placeholders like [Empty 1], [Empty 2], ...
      const templateDataset = await getCanvaBrandTemplateDataset(resolvedBrandTemplateId);
      const datasetKeys = Object.keys(templateDataset || {});
      if (datasetKeys.length > 0) {
        const allowed = new Set(datasetKeys);
        const overlap = Object.keys(finalData).filter((key) => allowed.has(key));

        if (overlap.length === 0 && datasetKeys.every((key) => /^\[Empty\s+\d+\]$/i.test(key))) {
          const sortedEmptyKeys = [...datasetKeys].sort((left, right) => {
            const l = Number((left.match(/\d+/) || ["0"])[0]);
            const r = Number((right.match(/\d+/) || ["0"])[0]);
            return l - r;
          });
          const orderedTextValues = [
            resolvedHeadline,
            resolvedSubheadline,
            resolvedCta,
            brandId,
          ].filter((value): value is string => Boolean(value && value.trim()));

          const fallbackData: Record<string, CanvaAutofillField> = {};
          for (let i = 0; i < sortedEmptyKeys.length && i < orderedTextValues.length; i++) {
            fallbackData[sortedEmptyKeys[i]] = { type: "text", text: orderedTextValues[i] };
          }
          finalData = fallbackData;
        } else {
          finalData = Object.fromEntries(
            Object.entries(finalData).filter(([key]) => allowed.has(key)),
          ) as Record<string, CanvaAutofillField>;
        }
      }

      if (!Object.keys(finalData).length) {
        throw new Error(
          `Canva template ${resolvedBrandTemplateId} has no usable autofill field mapping. `
          + "Name template fields (e.g. headline/subheadline/cta) or pass explicit autofillData keys matching template dataset.",
        );
      }

      canvaDesign = await autofillBrandTemplate({
        brandTemplateId: resolvedBrandTemplateId,
        title: assetName,
        data: finalData,
      });
      logger.info(
        `Canva autofill: design=${canvaDesign.id} brandTemplate=${resolvedBrandTemplateId} fields=${Object.keys(finalData).join(",")}`,
      );
    } else {
      mode = resolvedSourceDesignId ? "clone" : "blank";
      canvaDesign = await createOrResizeCanvaDesign({
        title: assetName,
        width: spec.width,
        height: spec.height,
        assetId: canvaAsset.id,
        sourceDesignId: resolvedSourceDesignId,
      });
      logger.info(
        `Canva design created (${mode}): ${canvaDesign.id} editUrl=${canvaDesign.editUrl} sourceDesignId=${resolvedSourceDesignId || "none"}`,
      );
    }

    res.json({
      status: "created",
      canva: {
        mode,
        designId: canvaDesign.id,
        editUrl: canvaDesign.editUrl,
        viewUrl: canvaDesign.viewUrl,
        sourceDesignId: resolvedSourceDesignId || null,
        brandTemplateId: resolvedBrandTemplateId || null,
        asset: {
          id: canvaAsset.id,
          thumbnailUrl: canvaAsset.thumbnailUrl || null,
        },
      },
      image: {
        gcsUrl,
        mimeType: post.mimeType,
        width: spec.width,
        height: spec.height,
      },
      caption: post.caption,
      hashtags: post.hashtags.map((h) => `#${h}`),
      brand: post.brand,
      createdAt: new Date().toISOString(),
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Canva generate-post failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

export default router;
