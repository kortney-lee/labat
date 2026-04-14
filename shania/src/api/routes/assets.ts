/**
 * assets.ts — GET /assets/:id endpoint for retrieving generated images.
 */

import { Router, Request, Response } from "express";
import { getSignedUrl, getAssetMetadata } from "../../storage/gcs";
import { logger } from "../../utils/logger";

const router = Router();

/**
 * GET /assets/:id
 * Get info and signed URL for a generated asset.
 *
 * Query params:
 *   path — The GCS file path (required)
 *   expires — Signed URL expiry in minutes (default 60)
 */
router.get("/assets/:id", async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const filePath = req.query.path as string;

    if (!filePath) {
      res.status(400).json({ error: "path query parameter required" });
      return;
    }

    const [metadata, signedUrl] = await Promise.all([
      getAssetMetadata(filePath).catch(() => null),
      getSignedUrl(filePath, Number(req.query.expires) || 60),
    ]);

    if (!metadata) {
      res.status(404).json({ error: "Asset not found" });
      return;
    }

    res.json({
      id,
      path: filePath,
      signedUrl,
      metadata,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Asset lookup failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

export default router;
