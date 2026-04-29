/**
 * delivery.ts — POST /deliver endpoint.
 * Routes generated graphics to the correct posting service:
 *   - Facebook/LinkedIn/Threads/Instagram → Shania engagement (Page publishing lives on Shania)
 *   - Twitter/TikTok → Shania engagement
 *
 * Note: The /api/labat/posts routes are mounted on the Shania engagement
 * service (not LABAT). LABAT handles ads & paid campaigns only.
 */

import { Router, Request, Response } from "express";
import { logger } from "../../utils/logger";
import { getBrand } from "../../config/brand";

const router = Router();

const SHANIA_ENGAGEMENT_URL =
  process.env.SHANIA_ENGAGEMENT_URL ||
  "https://wihy-shania-12913076533.us-central1.run.app";

const ADMIN_TOKEN = process.env.INTERNAL_ADMIN_TOKEN || "";
const BRAND_ENGAGEMENT_URLS: Record<string, string> = {
  wihy: process.env.SHANIA_ENGAGEMENT_URL_WIHY || "https://wihy-shania-wihy-n4l2vldq3q-uc.a.run.app",
  communitygroceries: process.env.SHANIA_ENGAGEMENT_URL_CG || "https://wihy-shania-cg-n4l2vldq3q-uc.a.run.app",
  vowels: process.env.SHANIA_ENGAGEMENT_URL_VOWELS || "https://wihy-shania-vowels-n4l2vldq3q-uc.a.run.app",
  childrennutrition: process.env.SHANIA_ENGAGEMENT_URL_CN || "https://wihy-shania-cn-n4l2vldq3q-uc.a.run.app",
  parentingwithchrist: process.env.SHANIA_ENGAGEMENT_URL_PWC || "https://wihy-shania-pwc-n4l2vldq3q-uc.a.run.app",
  otakulounge: process.env.SHANIA_ENGAGEMENT_URL_OTAKU || process.env.SHANIA_ENGAGEMENT_URL_WIHY || "https://wihy-shania-wihy-n4l2vldq3q-uc.a.run.app",
};

type DeliveryPlatform = "facebook" | "instagram" | "twitter" | "linkedin" | "tiktok" | "threads";

interface DeliverRequest {
  assetUrl: string;
  platform: DeliveryPlatform;
  caption?: string;
  scheduledTime?: string;
  brand?: string;
}

/** Platforms that use Facebook/LinkedIn/Threads/Instagram page-posting routes (served by Shania engagement). */
const PAGE_PLATFORMS = new Set<DeliveryPlatform>(["facebook", "linkedin", "threads", "instagram"]);
/** Platforms routed to Shania engagement social posting. */
const SOCIAL_PLATFORMS = new Set<DeliveryPlatform>(["twitter", "tiktok"]);

function resolvePostingBrandId(brandId?: string): string {
  const profile = getBrand(brandId);
  if (BRAND_ENGAGEMENT_URLS[profile.id]) {
    return profile.id;
  }
  if (profile.parentBrand && BRAND_ENGAGEMENT_URLS[profile.parentBrand]) {
    return profile.parentBrand;
  }
  return profile.id;
}

/**
 * POST /deliver
 * Route a generated graphic to the correct posting service.
 *   - facebook/linkedin/threads/instagram → Shania page routes
 *   - twitter/tiktok → Shania engagement
 */
router.post("/deliver", async (req: Request, res: Response): Promise<void> => {
  try {
    const { assetUrl, platform, caption, scheduledTime, brand } = req.body as DeliverRequest;

    if (!assetUrl || !platform) {
      res.status(400).json({ error: "assetUrl and platform are required" });
      return;
    }

    // Approval queue removed — all posts deliver directly

    if (!ADMIN_TOKEN) {
      res.status(503).json({ error: "INTERNAL_ADMIN_TOKEN not configured" });
      return;
    }

    const brandProfile = getBrand(brand);
    const postingBrandId = resolvePostingBrandId(brand);
    const brandScopedShaniaUrl = BRAND_ENGAGEMENT_URLS[postingBrandId] || SHANIA_ENGAGEMENT_URL;

    // Route Facebook/LinkedIn/Threads page posts through Shania engagement
    // (the /api/labat/posts routes are mounted on Shania, not LABAT)
    if (PAGE_PLATFORMS.has(platform)) {
      const pageEndpoint = platform === "linkedin"
        ? `${brandScopedShaniaUrl}/api/labat/linkedin/posts`
        : platform === "threads"
        ? `${brandScopedShaniaUrl}/api/labat/posts/threads`
        : platform === "instagram"
        ? `${brandScopedShaniaUrl}/api/labat/posts/instagram`
        : `${brandScopedShaniaUrl}/api/labat/posts`;

      // Threads has a 500-char limit; truncate with ellipsis if needed
      const threadsCaption = (caption || "").length > 500
        ? (caption || "").slice(0, 497) + "..."
        : caption || "";

      const pagePayload = platform === "linkedin"
        ? { message: caption || "", scheduled_publish_time: scheduledTime }
        : platform === "threads"
        ? { text: threadsCaption, image_url: assetUrl, page_id: brandProfile.facebookPageId || undefined }
        : platform === "instagram"
        ? { caption: caption || "", image_url: assetUrl, page_id: brandProfile.facebookPageId || undefined }
        : {
            message: caption || "",
            image_url: assetUrl,
            published: !scheduledTime,
            scheduled_publish_time: scheduledTime,
            page_id: brandProfile.facebookPageId || undefined,
          };

      const response = await fetch(pageEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": ADMIN_TOKEN,
        },
        body: JSON.stringify(pagePayload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.error(`Page delivery to ${platform} failed: ${response.status} ${errorText}`);
        res.status(502).json({ error: `Page delivery failed: ${response.status}`, details: errorText });
        return;
      }

      const result = await response.json();
      logger.info(`Delivered to ${platform} via Shania page routes: ${assetUrl}`);
      res.json({
        status: "delivered",
        platform,
        service: "shania-brand",
        postingBrand: postingBrandId,
        endpoint: pageEndpoint,
        result,
      });
      return;
    }

    // Route to Shania engagement for Twitter/Instagram/TikTok
    if (SOCIAL_PLATFORMS.has(platform)) {
      const response = await fetch(`${SHANIA_ENGAGEMENT_URL}/api/engagement/post`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": ADMIN_TOKEN,
        },
        body: JSON.stringify({
          platform,
          image_url: assetUrl,
          message: caption || "",
          scheduled_publish_time: scheduledTime,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.error(`Shania delivery to ${platform} failed: ${response.status} ${errorText}`);
        res.status(502).json({ error: `Shania delivery failed: ${response.status}`, details: errorText });
        return;
      }

      const result = await response.json();
      logger.info(`Delivered to ${platform} via Shania: ${assetUrl}`);
      res.json({ status: "delivered", platform, service: "shania", result });
      return;
    }

    res.status(400).json({
      error: `Unknown platform: ${platform}`,
      supported: [...PAGE_PLATFORMS, ...SOCIAL_PLATFORMS],
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Delivery failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

export default router;
