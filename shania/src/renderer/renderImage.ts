/**
 * renderImage.ts — Uses Puppeteer to screenshot rendered HTML and Sharp to post-process.
 */

import puppeteer, { Browser } from "puppeteer";
import sharp from "sharp";
import { FORMATS, FormatKey, DEFAULT_FORMAT } from "../config/formats";
import { ImageFormat } from "../types";
import { logger } from "../utils/logger";

let browser: Browser | null = null;

/** Launch or reuse a shared browser instance. */
async function getBrowser(): Promise<Browser> {
  if (browser && browser.connected) return browser;

  logger.info("Launching Puppeteer browser");
  browser = await puppeteer.launch({
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
      "--disable-software-rasterizer",
      "--font-render-hinting=none",
    ],
  });
  return browser;
}

export interface ScreenshotOptions {
  html: string;
  outputSize?: FormatKey;
  format?: ImageFormat;
  quality?: number;
  finalWidth?: number;
  finalHeight?: number;
}

const SHANIA_USE_SHARP = !["0", "false", "no"].includes(
  (process.env.SHANIA_USE_SHARP || "true").trim().toLowerCase(),
);

function clampQuality(value: number | undefined, fallback = 90): number {
  if (value == null || Number.isNaN(value)) return fallback;
  return Math.min(100, Math.max(1, value));
}

async function postProcessWithSharp(
  input: Buffer,
  format: ImageFormat,
  quality: number | undefined,
  width: number,
  height: number,
): Promise<Buffer> {
  let pipeline = sharp(input).resize(width, height, {
    fit: "cover",
    position: "centre",
  });

  if (format === "jpeg") {
    pipeline = pipeline.jpeg({ quality: clampQuality(quality, 88), mozjpeg: true });
  } else if (format === "webp") {
    pipeline = pipeline.webp({ quality: clampQuality(quality, 90), effort: 5 });
  } else {
    pipeline = pipeline.png({ compressionLevel: 9, adaptiveFiltering: true });
  }

  return pipeline.toBuffer();
}

/**
 * Render HTML to an image buffer.
 * Returns the raw image bytes as a Buffer.
 */
export async function screenshotHtml(opts: ScreenshotOptions): Promise<Buffer> {
  const {
    html,
    outputSize = DEFAULT_FORMAT,
    format = "png",
    quality,
    finalWidth,
    finalHeight,
  } = opts;

  const spec = FORMATS[outputSize];
  if (!spec) {
    throw new Error(`Unknown output size: ${outputSize}`);
  }

  const b = await getBrowser();
  const page = await b.newPage();

  try {
    await page.setViewport({
      width: spec.width,
      height: spec.height,
      deviceScaleFactor: 2, // 2x for retina-quality output
    });

    await page.setContent(html, { waitUntil: "networkidle0" });

    // Wait briefly for fonts to load
    await page.evaluate(() => {
      // @ts-ignore - document.fonts exists in browser context
      return (document as any).fonts?.ready ?? Promise.resolve();
    });

    const screenshotType = SHANIA_USE_SHARP
      ? "png"
      : (format === "jpeg" ? "jpeg" : format === "webp" ? "webp" : "png");

    const screenshotOpts: Record<string, unknown> = {
      type: screenshotType,
      fullPage: false,
      omitBackground: false,
      clip: { x: 0, y: 0, width: spec.width, height: spec.height },
    };

    if (!SHANIA_USE_SHARP && (format === "jpeg" || format === "webp") && quality != null) {
      screenshotOpts.quality = clampQuality(quality);
    }

    const raw = await page.screenshot(screenshotOpts);
    let buffer = Buffer.isBuffer(raw) ? raw : Buffer.from(raw);

    if (SHANIA_USE_SHARP) {
      const targetWidth = finalWidth || spec.width;
      const targetHeight = finalHeight || spec.height;
      buffer = await postProcessWithSharp(buffer, format, quality, targetWidth, targetHeight);
      logger.info(
        `Screenshot+Sharp: ${targetWidth}x${targetHeight} ${format} (${buffer.length} bytes)`
      );
    } else {
      logger.info(`Screenshot: ${spec.width}x${spec.height} ${format} (${buffer.length} bytes)`);
    }

    return buffer;
  } finally {
    await page.close();
  }
}

/** Gracefully close the browser (call on shutdown). */
export async function closeBrowser(): Promise<void> {
  if (browser) {
    await browser.close();
    browser = null;
    logger.info("Puppeteer browser closed");
  }
}
