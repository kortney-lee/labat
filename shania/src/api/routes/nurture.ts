/**
 * nurture.ts — POST /nurture/dispatch and POST /nurture/trigger endpoints.
 *
 * Two ways to send nurture templates:
 *
 *   POST /nurture/dispatch
 *     Body: { templateId, brand, channel, recipient, overrides? }
 *     Direct dispatch with full control.
 *
 *   POST /nurture/trigger
 *     Body: { trigger, channel?, recipient, overrides? }
 *     Convenience: maps a named trigger event → template + brand automatically.
 *     Supported triggers:
 *       book_requested, book_delivered_d2,
 *       no_purchase_wihy_d4, no_purchase_cg_d4,
 *       bundle_wihy_d6, bundle_cg_d6, final_urgency_d10
 *
 * Both endpoints require X-Admin-Token header.
 */

import { Router, Request, Response } from "express";
import { logger } from "../../utils/logger";
import {
  dispatchNurtureTemplate,
  dispatchByTrigger,
  NurtureTemplateId,
  NurtureBrand,
  NurtureChannel,
  NurtureRecipient,
  PlaceholderOverrides,
} from "../../services/nurture_dispatch";

const router = Router();

const ADMIN_TOKEN = process.env.INTERNAL_ADMIN_TOKEN || "";

function requireAdminToken(req: Request, res: Response): boolean {
  if (!ADMIN_TOKEN) {
    logger.warn("INTERNAL_ADMIN_TOKEN not configured — rejecting nurture request");
    res.status(503).json({ error: "Service not configured" });
    return false;
  }
  if (req.headers["x-admin-token"] !== ADMIN_TOKEN) {
    res.status(401).json({ error: "Unauthorized" });
    return false;
  }
  return true;
}

/**
 * POST /nurture/dispatch
 * Direct dispatch with explicit templateId + brand.
 */
router.post("/nurture/dispatch", async (req: Request, res: Response): Promise<void> => {
  if (!requireAdminToken(req, res)) return;

  const { templateId, brand, channel, recipient, overrides } = req.body as {
    templateId: NurtureTemplateId;
    brand: NurtureBrand;
    channel: NurtureChannel;
    recipient: NurtureRecipient;
    overrides?: PlaceholderOverrides;
  };

  if (!templateId || !brand || !channel || !recipient) {
    res.status(400).json({ error: "templateId, brand, channel, and recipient are required" });
    return;
  }

  if (channel !== "email" && channel !== "sms" && channel !== "both") {
    res.status(400).json({ error: "channel must be 'email', 'sms', or 'both'" });
    return;
  }

  if (channel === "email" && !recipient.email) {
    res.status(400).json({ error: "recipient.email is required for email channel" });
    return;
  }

  if (channel === "sms" && !recipient.phone) {
    res.status(400).json({ error: "recipient.phone is required for sms channel" });
    return;
  }

  try {
    const result = await dispatchNurtureTemplate({ templateId, brand, channel, recipient, overrides });
    const hasErrors = result.errors.length > 0;
    const statusCode = result.channelsSent.length === 0 ? 500 : hasErrors ? 207 : 200;

    res.status(statusCode).json(result);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    logger.error(`nurture/dispatch error: ${msg}`);
    res.status(500).json({ error: msg });
  }
});

/**
 * POST /nurture/trigger
 * Convenience endpoint — pass a trigger event name instead of a templateId.
 */
router.post("/nurture/trigger", async (req: Request, res: Response): Promise<void> => {
  if (!requireAdminToken(req, res)) return;

  const { trigger, channel, recipient, overrides } = req.body as {
    trigger: string;
    channel?: NurtureChannel;
    recipient: NurtureRecipient;
    overrides?: PlaceholderOverrides;
  };

  if (!trigger || !recipient) {
    res.status(400).json({ error: "trigger and recipient are required" });
    return;
  }

  try {
    const result = await dispatchByTrigger(
      trigger,
      recipient,
      channel ?? "both",
      overrides,
    );

    if (!result) {
      res.status(400).json({ error: `Unknown trigger: "${trigger}"` });
      return;
    }

    const hasErrors = result.errors.length > 0;
    const statusCode = result.channelsSent.length === 0 ? 500 : hasErrors ? 207 : 200;

    res.status(statusCode).json(result);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    logger.error(`nurture/trigger error: ${msg}`);
    res.status(500).json({ error: msg });
  }
});

/**
 * GET /nurture/templates
 * List available template IDs and their trigger descriptions.
 */
router.get("/nurture/templates", (_req: Request, res: Response): void => {
  const { NURTURE_EMAIL_TEMPLATES } = require("../../templates/nurture_email");
  const templates = Object.values(NURTURE_EMAIL_TEMPLATES).map((t: any) => ({
    id: t.id,
    brands: t.brands,
    trigger: t.trigger,
    subject: t.subject,
  }));
  res.json({ templates });
});

export default router;
