/**
 * renderPost.ts - CLI renderer for social templates.
 *
 * Examples:
 *   npm run render -- --template cg_fresh_pick --brand communitygroceries --size feed_square
 *   npm run render -- --template cta_card --brand wihy --size instagram-square --format webp --quality 92
 *   npm run render -- --template stat_card --size 1080x1350 --data ./data/stat.json
 */

import fs from "fs";
import path from "path";
import { renderTemplate, listTemplateIds } from "../renderer/renderHtml";
import { screenshotHtml, closeBrowser } from "../renderer/renderImage";
import { DEFAULT_FORMAT, FORMATS, FormatKey } from "../config/formats";
import { ImageFormat, TemplateData } from "../types";

type RawArgs = Record<string, string | boolean>;

interface CliOptions {
  templateId: string;
  brand?: string;
  outputSize: FormatKey;
  format: ImageFormat;
  quality?: number;
  finalWidth?: number;
  finalHeight?: number;
  dataPath?: string;
  outPath?: string;
  saveHtml: boolean;
}

const SIZE_ALIASES: Record<string, string> = {
  "instagram-square": "feed_square",
  "instagram-portrait": "feed_portrait",
  "story": "story_vertical",
  "story-vertical": "story_vertical",
  "reel-cover": "story_vertical",
  "1080x1080": "feed_square",
  "1080x1350": "feed_portrait",
  "1080x1920": "story_vertical",
  "1920x1080": "hd_landscape",
};

const FORMAT_ALIASES: Record<string, ImageFormat> = {
  "png": "png",
  "webp": "webp",
  "jpg": "jpeg",
  "jpeg": "jpeg",
};

function usage(): string {
  return [
    "Usage:",
    "  npm run render -- --template <template_id> [options]",
    "",
    "Options:",
    "  --template <id>       Template ID (required)",
    "  --brand <id>          Brand key (wihy, communitygroceries, vowels, ...)",
    "  --size <key>          Output size key or alias (default: feed_square)",
    "  --format <fmt>        png | webp | jpg | jpeg (default: png)",
    "  --quality <1-100>     Compression quality for jpeg/webp",
    "  --width <px>          Final output width override",
    "  --height <px>         Final output height override",
    "  --data <file.json>    Template data JSON file",
    "  --out <path>          Output image path",
    "  --no-html             Skip writing companion HTML file",
    "  --help                Show this help",
    "",
    "Size aliases:",
    "  instagram-square -> feed_square",
    "  instagram-portrait -> feed_portrait",
    "  story -> story_vertical",
    "  1080x1080 -> feed_square",
    "  1080x1350 -> feed_portrait",
    "  1080x1920 -> story_vertical",
    "  1920x1080 -> hd_landscape",
  ].join("\n");
}

function parseRawArgs(argv: string[]): RawArgs {
  const out: RawArgs = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;

    if (token === "--help") {
      out.help = true;
      continue;
    }

    if (token.startsWith("--no-")) {
      out[token.slice(5)] = false;
      continue;
    }

    const key = token.slice(2);
    const next = argv[i + 1];
    if (next && !next.startsWith("--")) {
      out[key] = next;
      i += 1;
    } else {
      out[key] = true;
    }
  }
  return out;
}

function normalizeSize(value: string | boolean | undefined): FormatKey {
  const raw = String(value || DEFAULT_FORMAT).trim().toLowerCase();
  const mapped = SIZE_ALIASES[raw] || raw;
  if (!(mapped in FORMATS)) {
    throw new Error(`Unknown size '${raw}'. Valid: ${Object.keys(FORMATS).join(", ")}`);
  }
  return mapped as FormatKey;
}

function normalizeFormat(value: string | boolean | undefined): ImageFormat {
  const raw = String(value || "png").trim().toLowerCase();
  const mapped = FORMAT_ALIASES[raw];
  if (!mapped) {
    throw new Error("Unknown format. Use png, webp, jpg, or jpeg.");
  }
  return mapped;
}

function toInt(value: string | boolean | undefined, label: string): number | undefined {
  if (value == null || typeof value === "boolean") return undefined;
  const n = Number.parseInt(value, 10);
  if (!Number.isFinite(n)) {
    throw new Error(`${label} must be an integer.`);
  }
  return n;
}

function loadTemplateData(dataPath: string | undefined, templateId: string): TemplateData {
  if (!dataPath) {
    return {
      headline: `${templateId.replace(/_/g, " ")} headline`,
      subtext: "High-converting social creative with clear message hierarchy.",
      cta: "Learn more",
      productName: "WIHY",
    };
  }

  const absPath = path.resolve(dataPath);
  if (!fs.existsSync(absPath)) {
    throw new Error(`Data file not found: ${absPath}`);
  }

  const parsed = JSON.parse(fs.readFileSync(absPath, "utf-8"));
  if (!parsed || typeof parsed !== "object") {
    throw new Error("Data JSON must be an object.");
  }
  return parsed as TemplateData;
}

function resolveOutputPath(templateId: string, size: FormatKey, format: ImageFormat, outPath?: string): string {
  if (outPath) return path.resolve(outPath);
  const ext = format === "jpeg" ? "jpg" : format;
  return path.join(process.cwd(), "preview", `${templateId}_${size}.${ext}`);
}

function buildOptions(args: RawArgs): CliOptions {
  const templateToken = args.template || args.templateId;
  if (!templateToken || typeof templateToken !== "string") {
    throw new Error("--template is required.");
  }

  const templateId = templateToken.trim();
  const validTemplates = listTemplateIds();
  if (!validTemplates.includes(templateId)) {
    throw new Error(
      `Unknown template '${templateId}'. Valid templates: ${validTemplates.join(", ")}`
    );
  }

  return {
    templateId,
    brand: typeof args.brand === "string" ? args.brand.trim().toLowerCase() : undefined,
    outputSize: normalizeSize(args.size),
    format: normalizeFormat(args.format),
    quality: toInt(args.quality, "quality"),
    finalWidth: toInt(args.width, "width"),
    finalHeight: toInt(args.height, "height"),
    dataPath: typeof args.data === "string" ? args.data : undefined,
    outPath: typeof args.out === "string" ? args.out : undefined,
    saveHtml: args.html !== false,
  };
}

async function main(): Promise<void> {
  const raw = parseRawArgs(process.argv.slice(2));
  if (raw.help) {
    console.log(usage());
    return;
  }

  const opts = buildOptions(raw);
  const data = loadTemplateData(opts.dataPath, opts.templateId);

  const html = renderTemplate(opts.templateId, data, opts.outputSize, opts.brand);
  const imageBuffer = await screenshotHtml({
    html,
    outputSize: opts.outputSize,
    format: opts.format,
    quality: opts.quality,
    finalWidth: opts.finalWidth,
    finalHeight: opts.finalHeight,
  });

  const outputPath = resolveOutputPath(opts.templateId, opts.outputSize, opts.format, opts.outPath);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, imageBuffer);

  if (opts.saveHtml) {
    const htmlPath = outputPath.replace(/\.[^.]+$/, ".html");
    fs.writeFileSync(htmlPath, html, "utf-8");
    console.log(`HTML: ${htmlPath}`);
  }

  console.log(`Image: ${outputPath}`);
  console.log(`Size: ${FORMATS[opts.outputSize].width}x${FORMATS[opts.outputSize].height} (${opts.outputSize})`);
  console.log(`Format: ${opts.format}`);
}

main()
  .catch((err: unknown) => {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`Render failed: ${message}`);
    console.error("\n" + usage());
    process.exitCode = 1;
  })
  .finally(async () => {
    await closeBrowser();
  });
