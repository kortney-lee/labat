/**
 * imagenClient.ts — Imagen 4.0 image generation via Vertex AI.
 *
 * Generates high-quality marketing images from text prompts.
 * Uses Vertex AI endpoint with Application Default Credentials (service account on Cloud Run).
 */

import { GoogleAuth } from "google-auth-library";
import { logger } from "../utils/logger";

const GCP_PROJECT = process.env.GCP_PROJECT || "wihy-ai";
const GCP_LOCATION = process.env.GCP_LOCATION || "us-central1";
const IMAGEN_MODEL = "imagen-4.0-generate-001";

const auth = new GoogleAuth({ scopes: "https://www.googleapis.com/auth/cloud-platform" });

export type AspectRatio = "1:1" | "9:16" | "16:9" | "4:3" | "3:4";

export interface ImagenRequest {
  prompt: string;
  aspectRatio?: AspectRatio;
  sampleCount?: number;
}

export interface ImagenResult {
  imageBytes: Buffer;
  mimeType: string;
}

/**
 * Generate an image using Imagen 4.0 via Vertex AI.
 */
export async function generateImage(req: ImagenRequest): Promise<ImagenResult> {
  // Always append no-text instructions — Imagen tends to generate garbled text on signs/labels
  const sanitizedPrompt = `${req.prompt}. The image must contain absolutely no text, no words, no letters, no numbers, no writing, no signs, no labels, no price tags, no watermarks.`;

  const body = {
    instances: [{ prompt: sanitizedPrompt }],
    parameters: {
      sampleCount: req.sampleCount || 1,
      aspectRatio: req.aspectRatio || "1:1",
    },
  };

  const url = `https://${GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/${GCP_PROJECT}/locations/${GCP_LOCATION}/publishers/google/models/${IMAGEN_MODEL}:predict`;

  const client = await auth.getClient();
  const token = await client.getAccessToken();

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token.token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Imagen API error ${response.status}: ${errText}`);
  }

  const data = (await response.json()) as { predictions?: Array<{ bytesBase64Encoded?: string; mimeType?: string }> };
  const prediction = data.predictions?.[0];

  if (!prediction?.bytesBase64Encoded) {
    throw new Error("Imagen returned no image data");
  }

  const imageBytes = Buffer.from(prediction.bytesBase64Encoded, "base64");
  logger.info(`Imagen generated image: ${imageBytes.length} bytes`);

  return {
    imageBytes,
    mimeType: prediction.mimeType || "image/png",
  };
}

export function isImagenAvailable(): boolean {
  return true;
}
