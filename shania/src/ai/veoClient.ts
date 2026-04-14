/**
 * veoClient.ts — Veo 2 video generation via Google Generative Language API.
 *
 * Generates short-form marketing videos from text prompts.
 * Async: submit → poll operation → download MP4.
 * Supports brand watermark overlay via ffmpeg.
 */

import { execFile } from "child_process";
import { writeFile, readFile, unlink } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { GoogleAuth } from "google-auth-library";
import { BrandProfile } from "../config/brand";
import { logger } from "../utils/logger";

const GCP_PROJECT = process.env.GCP_PROJECT || "wihy-ai";
const GCP_LOCATION = process.env.GCP_LOCATION || "us-central1";
const VEO_MODEL = "veo-2.0-generate-001";
const VERTEX_BASE = `https://${GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/${GCP_PROJECT}/locations/${GCP_LOCATION}/publishers/google/models`;

const auth = new GoogleAuth({ scopes: "https://www.googleapis.com/auth/cloud-platform" });

const POLL_INTERVAL_MS = 5_000;
const MAX_POLL_ATTEMPTS = 60; // 5 min max

export type VideoAspectRatio = "16:9" | "9:16";

export interface VeoRequest {
  prompt: string;
  aspectRatio?: VideoAspectRatio;
  durationSeconds?: number;
}

export interface VeoResult {
  videoBytes: Buffer;
  mimeType: string;
  durationSeconds: number;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Build a brand-aware video prompt that embeds visual identity into the generation.
 */
export function buildBrandedVideoPrompt(basePrompt: string, brand: BrandProfile): string {
  return `${basePrompt}

VISUAL STYLE DIRECTION:
- Color palette: ${brand.colorWords}
- Aesthetic: Professional, modern, cinematic. Clean compositions.
- Brand tone: ${brand.name} — ${brand.tagline}
- ABSOLUTELY NO text, words, letters, numbers, labels, titles, captions, watermarks, or any written content.
- ABSOLUTELY NO food packaging, product labels, barcodes, or nutrition facts panels.
- Focus on real, authentic, beautiful visuals — food, nature, families, children, grandparents.
- Include warm human moments: children and grandparents enjoying healthy food together.
- 100% purely visual storytelling — zero text of any kind.`;
}

/**
 * Generate a video using Veo 2 (async: submit → poll → download).
 */
export async function generateVideo(req: VeoRequest): Promise<VeoResult> {
  const duration = req.durationSeconds || 8;

  const client = await auth.getClient();
  const token = await client.getAccessToken();
  const authHeaders = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token.token}`,
  };

  // Step 1: Submit long-running operation
  const submitUrl = `${VERTEX_BASE}/${VEO_MODEL}:predictLongRunning`;
  const body = {
    instances: [{ prompt: req.prompt }],
    parameters: {
      aspectRatio: req.aspectRatio || "16:9",
      durationSeconds: duration,
    },
  };

  logger.info(`Veo: submitting video generation (${duration}s, ${req.aspectRatio || "16:9"})...`);
  const submitRes = await fetch(submitUrl, {
    method: "POST",
    headers: authHeaders,
    body: JSON.stringify(body),
  });

  if (!submitRes.ok) {
    const errText = await submitRes.text();
    throw new Error(`Veo submit error ${submitRes.status}: ${errText}`);
  }

  const operation = (await submitRes.json()) as { name: string; done?: boolean };
  const operationName = operation.name;
  logger.info(`Veo: operation submitted — ${operationName}`);

  // Step 2: Poll until done
  const pollUrl = `https://${GCP_LOCATION}-aiplatform.googleapis.com/v1/${operationName}`;
  let result: Record<string, unknown> | undefined;

  for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt++) {
    await sleep(POLL_INTERVAL_MS);

    const pollRes = await fetch(pollUrl, { headers: authHeaders });
    if (!pollRes.ok) {
      const errText = await pollRes.text();
      throw new Error(`Veo poll error ${pollRes.status}: ${errText}`);
    }

    result = (await pollRes.json()) as Record<string, unknown>;
    if (result.done) {
      logger.info(`Veo: generation complete after ${((attempt + 1) * POLL_INTERVAL_MS) / 1000}s`);
      break;
    }

    if (attempt % 6 === 5) {
      logger.info(`Veo: still generating... (${((attempt + 1) * POLL_INTERVAL_MS) / 1000}s elapsed)`);
    }
  }

  if (!result?.done) {
    throw new Error(`Veo generation timed out after ${(MAX_POLL_ATTEMPTS * POLL_INTERVAL_MS) / 1000}s`);
  }

  // Step 3: Extract video from response
  const response = result.response as Record<string, unknown> | undefined;
  if (!response) throw new Error("Veo returned no response payload");

  // Handle predictLongRunning response: generateVideoResponse.generatedSamples[].video.uri
  const generateVideoResponse = response.generateVideoResponse as Record<string, unknown> | undefined;
  const generatedSamples = (
    (generateVideoResponse?.generatedSamples as Array<{ video?: { uri?: string } }>) || []
  );
  const sampleUri = generatedSamples[0]?.video?.uri;

  // Also check legacy format: generatedVideos[].video.uri
  const generatedVideos = (response.generatedVideos as Array<{ video?: { uri?: string } }>) || [];
  const videoUri = sampleUri || generatedVideos[0]?.video?.uri;

  if (videoUri) {
    logger.info(`Veo: downloading video from URI...`);
    const videoRes = await fetch(videoUri, { headers: { Authorization: `Bearer ${token.token}` } });
    if (!videoRes.ok) throw new Error(`Failed to download Veo video: ${videoRes.status}`);
    const videoBytes = Buffer.from(await videoRes.arrayBuffer());
    logger.info(`Veo: downloaded ${videoBytes.length} bytes`);
    return { videoBytes, mimeType: "video/mp4", durationSeconds: duration };
  }

  // Handle base64-encoded response (predictions[].bytesBase64Encoded)
  const predictions = (response.predictions as Array<{ bytesBase64Encoded?: string }>) || [];
  const b64 = predictions[0]?.bytesBase64Encoded;

  if (b64) {
    const videoBytes = Buffer.from(b64, "base64");
    logger.info(`Veo: decoded ${videoBytes.length} bytes from base64`);
    return { videoBytes, mimeType: "video/mp4", durationSeconds: duration };
  }

  throw new Error("Veo returned no video data (no URI or base64 found)");
}

/**
 * Overlay a brand logo watermark on a video using ffmpeg.
 * Logo is placed at bottom-right with 30% opacity, scaled to 80px wide.
 * Returns the watermarked video bytes, or original if ffmpeg unavailable.
 */
export async function addLogoWatermark(videoBytes: Buffer, logoUrl: string): Promise<Buffer> {
  const ts = Date.now();
  const inputPath = join(tmpdir(), `veo_in_${ts}.mp4`);
  const outputPath = join(tmpdir(), `veo_out_${ts}.mp4`);
  const logoPath = join(tmpdir(), `veo_logo_${ts}.png`);

  try {
    // Download logo
    const logoRes = await fetch(logoUrl);
    if (!logoRes.ok) {
      logger.warn(`Could not download logo from ${logoUrl} — skipping watermark`);
      return videoBytes;
    }
    const logoBytes = Buffer.from(await logoRes.arrayBuffer());

    await writeFile(logoPath, logoBytes);
    await writeFile(inputPath, videoBytes);

    // Overlay: scale logo to 80px wide, 30% opacity, bottom-right with 20px padding
    await new Promise<void>((resolve, reject) => {
      execFile(
        "ffmpeg",
        [
          "-i",
          inputPath,
          "-i",
          logoPath,
          "-filter_complex",
          "[1:v]scale=80:-1,format=rgba,colorchannelmixer=aa=0.3[logo];[0:v][logo]overlay=W-w-20:H-h-20",
          "-codec:a",
          "copy",
          "-y",
          outputPath,
        ],
        { timeout: 60_000 },
        (err) => (err ? reject(err) : resolve()),
      );
    });

    const watermarked = await readFile(outputPath);
    logger.info(`Veo watermark: ${videoBytes.length} → ${watermarked.length} bytes`);
    return watermarked;
  } catch (err: unknown) {
    logger.warn(`ffmpeg watermark failed (returning original): ${err instanceof Error ? err.message : String(err)}`);
    return videoBytes;
  } finally {
    await Promise.allSettled([unlink(inputPath), unlink(outputPath), unlink(logoPath)]);
  }
}

export function isVeoAvailable(): boolean {
  return true;
}
