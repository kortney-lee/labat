/**
 * gcs.ts — Cloud Storage client for storing and serving generated images.
 */

import { Storage } from "@google-cloud/storage";
import { v4 as uuid } from "uuid";
import { ImageFormat } from "../types";
import { logger } from "../utils/logger";

const BUCKET_NAME = process.env.GCS_BUCKET || "wihy-shania-graphics";
const PROJECT_ID = process.env.GCP_PROJECT || "wihy-ai";

let storage: Storage | null = null;

function getStorage(): Storage {
  if (!storage) {
    storage = new Storage({ projectId: PROJECT_ID });
  }
  return storage;
}

const MIME_TYPES: Record<ImageFormat, string> = {
  png: "image/png",
  webp: "image/webp",
  jpeg: "image/jpeg",
};

export interface UploadResult {
  id: string;
  bucket: string;
  path: string;
  publicUrl: string;
  signedUrl?: string;
}

/**
 * Upload an image buffer to Cloud Storage.
 * Returns the public URL and metadata.
 */
export async function uploadImage(
  buffer: Buffer,
  format: ImageFormat,
  templateId: string,
  metadata?: Record<string, string>,
): Promise<UploadResult> {
  const s = getStorage();
  const id = uuid();
  const ext = format === "jpeg" ? "jpg" : format;
  const date = new Date().toISOString().slice(0, 10);
  const filePath = `graphics/${date}/${templateId}/${id}.${ext}`;

  const bucket = s.bucket(BUCKET_NAME);
  const file = bucket.file(filePath);

  await file.save(buffer, {
    contentType: MIME_TYPES[format],
    metadata: {
      cacheControl: "public, max-age=31536000",
      metadata: {
        templateId,
        generatedAt: new Date().toISOString(),
        ...metadata,
      },
    },
  });

  const publicUrl = `https://storage.googleapis.com/${BUCKET_NAME}/${filePath}`;
  logger.info(`Uploaded to GCS: ${filePath} (${buffer.length} bytes)`);

  return { id, bucket: BUCKET_NAME, path: filePath, publicUrl };
}

/**
 * Upload a video buffer to Cloud Storage.
 */
export async function uploadVideo(
  buffer: Buffer,
  label: string,
  metadata?: Record<string, string>,
): Promise<UploadResult> {
  const s = getStorage();
  const id = uuid();
  const date = new Date().toISOString().slice(0, 10);
  const filePath = `videos/${date}/${label}/${id}.mp4`;

  const bucket = s.bucket(BUCKET_NAME);
  const file = bucket.file(filePath);

  await file.save(buffer, {
    contentType: "video/mp4",
    metadata: {
      cacheControl: "public, max-age=31536000",
      metadata: {
        label,
        generatedAt: new Date().toISOString(),
        ...metadata,
      },
    },
  });

  const publicUrl = `https://storage.googleapis.com/${BUCKET_NAME}/${filePath}`;
  logger.info(`Uploaded video to GCS: ${filePath} (${buffer.length} bytes)`);

  return { id, bucket: BUCKET_NAME, path: filePath, publicUrl };
}

/**
 * Generate a time-limited signed URL for an asset.
 */
export async function getSignedUrl(
  filePath: string,
  expiresMinutes: number = 60,
): Promise<string> {
  const s = getStorage();
  const [url] = await s
    .bucket(BUCKET_NAME)
    .file(filePath)
    .getSignedUrl({
      action: "read",
      expires: Date.now() + expiresMinutes * 60 * 1000,
    });
  return url;
}

/**
 * Get metadata for an asset.
 */
export async function getAssetMetadata(filePath: string): Promise<Record<string, unknown>> {
  const s = getStorage();
  const [metadata] = await s.bucket(BUCKET_NAME).file(filePath).getMetadata();
  return metadata as Record<string, unknown>;
}

/**
 * Ensure the bucket exists (call once on startup).
 */
export async function ensureBucket(): Promise<void> {
  try {
    const s = getStorage();
    const [exists] = await s.bucket(BUCKET_NAME).exists();
    if (!exists) {
      logger.warn(`Bucket ${BUCKET_NAME} does not exist — create it in GCP console or via gcloud`);
    } else {
      logger.info(`GCS bucket verified: ${BUCKET_NAME}`);
    }
  } catch (err) {
    logger.warn(`Could not verify GCS bucket: ${err}`);
  }
}
