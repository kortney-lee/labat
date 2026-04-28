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
const GOOGLE_DRIVE_API_BASE = "https://www.googleapis.com/drive/v3/files";

function resolveGoogleDriveFolder(brand?: string): string {
  const byBrandRaw = process.env.ASSET_LIBRARY_GOOGLE_DRIVE_FOLDERS || "";
  if (byBrandRaw) {
    try {
      const parsed = JSON.parse(byBrandRaw) as Record<string, string>;
      const b = (brand || "").toLowerCase().trim();
      return (b && parsed[b]) || parsed.default || "";
    } catch (err) {
      logger.warn(`Invalid ASSET_LIBRARY_GOOGLE_DRIVE_FOLDERS JSON: ${String(err)}`);
    }
  }
  return process.env.ASSET_LIBRARY_GOOGLE_DRIVE_FOLDER_ID || "";
}

async function listGoogleDriveAssets(
  folderId: string,
  apiKey: string,
  limit: number,
): Promise<Array<{ id: string; path: string; publicUrl: string; contentType: string; updated?: string }>> {
  const q = `'${folderId}' in parents and trashed=false and mimeType contains 'image/'`;
  const params = new URLSearchParams({
    q,
    pageSize: String(limit),
    fields: "files(id,name,mimeType,modifiedTime,webViewLink)",
    includeItemsFromAllDrives: "true",
    supportsAllDrives: "true",
    orderBy: "modifiedTime desc",
    key: apiKey,
  });

  const response = await fetch(`${GOOGLE_DRIVE_API_BASE}?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Google Drive list failed: ${response.status} ${await response.text()}`);
  }

  const payload = (await response.json()) as {
    files?: Array<{ id: string; name: string; mimeType: string; modifiedTime?: string }>;
  };

  return (payload.files || []).map((file) => ({
    id: file.id,
    path: file.name,
    publicUrl: `https://drive.google.com/uc?export=download&id=${file.id}`,
    contentType: file.mimeType,
    updated: file.modifiedTime,
  }));
}

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
    const limit = req.query.limit ? Number(req.query.limit) : undefined;

    if (ASSET_LIBRARY_PROVIDER === "google_drive") {
      const apiKey = process.env.ASSET_LIBRARY_GOOGLE_DRIVE_API_KEY || "";
      const folderId = resolveGoogleDriveFolder((req.query.brand as string) || undefined);
      if (!apiKey || !folderId) {
        res.status(400).json({
          error: "Google Drive asset library requires ASSET_LIBRARY_GOOGLE_DRIVE_API_KEY and folder id",
        });
        return;
      }

      const items = await listGoogleDriveAssets(
        folderId,
        apiKey,
        Math.min(Math.max(limit || 50, 1), 200),
      );
      res.json({ provider: "google_drive", count: items.length, items });
      return;
    }

    if (ASSET_LIBRARY_PROVIDER !== "gcp") {
      res.status(501).json({
        error: `Asset provider "${ASSET_LIBRARY_PROVIDER}" is not implemented. Use gcp or google_drive.`,
      });
      return;
    }

    const items = await listLibraryAssets({
      brand: (req.query.brand as string) || undefined,
      folder: (req.query.folder as string) || undefined,
      prefix: (req.query.prefix as string) || undefined,
      limit,
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
        error: `Asset provider "${ASSET_LIBRARY_PROVIDER}" is read-only or not implemented for upload. Use ASSET_LIBRARY_PROVIDER=gcp.`,
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
    if (ASSET_LIBRARY_PROVIDER === "google_drive") {
      const id = (req.query.id as string) || "";
      if (!id) {
        res.status(400).json({ error: "id query parameter required for google_drive" });
        return;
      }
      const signedUrl = `https://drive.google.com/uc?export=download&id=${id}`;
      res.json({ id, signedUrl });
      return;
    }

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
