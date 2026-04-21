/**
 * assets.ts — GET /assets/:id endpoint for retrieving generated images.
 */

import { Router, Request, Response } from "express";
import {
  getSignedUrl,
  getAssetMetadata,
  listLibraryAssets,
  uploadLibraryAsset,
} from "../../storage/gcs";
import { logger } from "../../utils/logger";

const router = Router();
const ASSET_LIBRARY_PROVIDER = (process.env.ASSET_LIBRARY_PROVIDER || "gcp").toLowerCase();

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

/**
 * GET /asset-library/list
 * Query:
 *   brand  — optional brand scope (e.g., wihy, communitygroceries)
 *   folder — optional subfolder (default images)
 *   prefix — optional raw GCS prefix override
 *   limit  — max items (1..200, default 50)
 */
router.get("/asset-library/list", async (req: Request, res: Response): Promise<void> => {
  try {
    if (ASSET_LIBRARY_PROVIDER !== "gcp") {
      res.status(501).json({
        error: `Asset provider "${ASSET_LIBRARY_PROVIDER}" is not implemented yet. Use ASSET_LIBRARY_PROVIDER=gcp.`,
      });
      return;
    }

    const items = await listLibraryAssets({
      brand: (req.query.brand as string) || undefined,
      folder: (req.query.folder as string) || undefined,
      prefix: (req.query.prefix as string) || undefined,
      limit: req.query.limit ? Number(req.query.limit) : undefined,
    });

    res.json({ provider: "gcp", count: items.length, items });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Asset library list failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * POST /asset-library/upload
 * Body (JSON):
 * {
 *   fileName: string,
 *   contentType: string,
 *   dataBase64: string, // raw base64 or data URL
 *   brand?: string,
 *   folder?: string,
 *   tags?: string[]
 * }
 */
router.post("/asset-library/upload", async (req: Request, res: Response): Promise<void> => {
  try {
    if (ASSET_LIBRARY_PROVIDER !== "gcp") {
      res.status(501).json({
        error: `Asset provider "${ASSET_LIBRARY_PROVIDER}" is not implemented yet. Use ASSET_LIBRARY_PROVIDER=gcp.`,
      });
      return;
    }

    const {
      fileName,
      contentType,
      dataBase64,
      brand,
      folder,
      tags,
    } = req.body as {
      fileName?: string;
      contentType?: string;
      dataBase64?: string;
      brand?: string;
      folder?: string;
      tags?: string[];
    };

    if (!fileName || !contentType || !dataBase64) {
      res.status(400).json({
        error: "fileName, contentType, and dataBase64 are required",
      });
      return;
    }

    const base64Payload = dataBase64.includes(",")
      ? dataBase64.split(",").pop() || ""
      : dataBase64;
    const buffer = Buffer.from(base64Payload, "base64");

    if (buffer.length === 0) {
      res.status(400).json({ error: "Decoded asset payload is empty" });
      return;
    }

    const uploaded = await uploadLibraryAsset(buffer, fileName, contentType, {
      brand,
      folder,
      tags: Array.isArray(tags) ? tags : [],
    });

    res.status(201).json({ provider: "gcp", ...uploaded, bytes: buffer.length });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Asset library upload failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

/**
 * GET /asset-library/signed-url?path=...&expires=60
 */
router.get("/asset-library/signed-url", async (req: Request, res: Response): Promise<void> => {
  try {
    const filePath = req.query.path as string;
    if (!filePath) {
      res.status(400).json({ error: "path query parameter required" });
      return;
    }

    const signedUrl = await getSignedUrl(filePath, Number(req.query.expires) || 60);
    res.json({ path: filePath, signedUrl });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`Asset library signed-url failed: ${message}`);
    res.status(500).json({ error: message });
  }
});

export default router;
