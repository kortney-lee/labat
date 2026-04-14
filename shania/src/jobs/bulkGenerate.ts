/**
 * bulkGenerate.ts — Queue-based bulk generation for batch graphic creation.
 *
 * Processes an array of generation requests sequentially to avoid
 * overloading the Puppeteer browser instance.
 */

import { v4 as uuid } from "uuid";
import { renderTemplate } from "../renderer/renderHtml";
import { screenshotHtml } from "../renderer/renderImage";
import { uploadImage } from "../storage/gcs";
import { GenerateRequest, GenerateResult } from "../types";
import { DEFAULT_FORMAT } from "../config/formats";
import { logger } from "../utils/logger";

export interface BulkJob {
  id: string;
  status: "queued" | "processing" | "completed" | "failed";
  items: GenerateRequest[];
  results: GenerateResult[];
  errors: Array<{ index: number; error: string }>;
  createdAt: string;
  completedAt?: string;
}

// In-memory job store (swap for Redis in production for persistence)
const jobs = new Map<string, BulkJob>();

/**
 * Enqueue a bulk generation job.
 * Returns the job ID immediately; processing happens async.
 */
export function enqueueBulkJob(items: GenerateRequest[]): BulkJob {
  const job: BulkJob = {
    id: uuid(),
    status: "queued",
    items,
    results: [],
    errors: [],
    createdAt: new Date().toISOString(),
  };
  jobs.set(job.id, job);
  processBulkJob(job.id).catch((err) =>
    logger.error(`Bulk job ${job.id} failed: ${err}`),
  );
  return job;
}

/**
 * Get the status of a bulk job.
 */
export function getJob(id: string): BulkJob | undefined {
  return jobs.get(id);
}

async function processBulkJob(jobId: string): Promise<void> {
  const job = jobs.get(jobId);
  if (!job) return;

  job.status = "processing";
  logger.info(`Bulk job ${jobId}: processing ${job.items.length} items`);

  for (let i = 0; i < job.items.length; i++) {
    const req = job.items[i];
    try {
      const html = renderTemplate(
        req.templateId,
        req.data,
        req.outputSize || DEFAULT_FORMAT,
        req.brand,
      );

      const format = req.format || "png";
      const buffer = await screenshotHtml({
        html,
        outputSize: req.outputSize || DEFAULT_FORMAT,
        format,
      });

      const uploaded = await uploadImage(buffer, format, req.templateId);
      const spec =
        (await import("../config/formats")).FORMATS[
          req.outputSize || DEFAULT_FORMAT
        ];

      job.results.push({
        id: uploaded.id,
        templateId: req.templateId,
        url: uploaded.publicUrl,
        format,
        width: spec.width,
        height: spec.height,
        createdAt: new Date().toISOString(),
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      job.errors.push({ index: i, error: message });
      logger.error(`Bulk job ${jobId} item ${i} failed: ${message}`);
    }
  }

  job.status = job.errors.length === job.items.length ? "failed" : "completed";
  job.completedAt = new Date().toISOString();
  logger.info(
    `Bulk job ${jobId}: ${job.status} (${job.results.length} ok, ${job.errors.length} errors)`,
  );
}
