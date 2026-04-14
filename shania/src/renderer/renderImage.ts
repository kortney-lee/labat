/**
 * renderImage.ts — Uses Puppeteer to screenshot rendered HTML into PNG/WEBP.
 */

import puppeteer, { Browser } from "puppeteer";
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

    const screenshotOpts: Record<string, unknown> = {
      type: format === "jpeg" ? "jpeg" : format === "webp" ? "webp" : "png",
      fullPage: false,
      omitBackground: false,
      clip: { x: 0, y: 0, width: spec.width, height: spec.height },
    };

    if ((format === "jpeg" || format === "webp") && quality != null) {
      screenshotOpts.quality = Math.min(100, Math.max(1, quality));
    }

    const raw = await page.screenshot(screenshotOpts);
    const buffer = Buffer.isBuffer(raw) ? raw : Buffer.from(raw);
    logger.info(`Screenshot: ${spec.width}x${spec.height} ${format} (${buffer.length} bytes)`);
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
