/**
 * renderHtml.ts — Compiles Handlebars templates with brand styles and data.
 */

import fs from "fs";
import path from "path";
import Handlebars from "handlebars";
import { BRAND, brandCSSVars, BrandProfile, getBrand, validateTemplateBrand, resolveLogoUrl, BRANDS, BrandId } from "../config/brand";
import { FORMATS, FormatKey, DEFAULT_FORMAT } from "../config/formats";
import { TemplateData } from "../types";
import { logger } from "../utils/logger";

type ArtDirection = "editorial" | "poster" | "data_lab" | "lifestyle";

// ── Local logo cache (base64 data URIs) ─────────────────────────────────────
const ASSETS_DIR = path.resolve(__dirname, "../../assets");
const logoDataUriCache: Record<string, string> = {};

const LOCAL_LOGO_MAP: Record<string, string> = {
  communitygroceries: "CommunityGroceries/Logo_CG.png",
  wihy: "Wihy/wihy_logo.png",
  vowels: "Vowels/Vowels_logo.png",
};

function resolveLogoDataUri(brand?: BrandProfile): string {
  const brandId = brand?.id ?? "wihy";
  // Check parent brand for sub-brands
  const key = LOCAL_LOGO_MAP[brandId]
    ? brandId
    : (brand?.parentBrand && LOCAL_LOGO_MAP[brand.parentBrand])
    ? brand.parentBrand
    : "wihy";

  if (logoDataUriCache[key]) return logoDataUriCache[key];

  const localPath = path.join(ASSETS_DIR, LOCAL_LOGO_MAP[key]);
  if (fs.existsSync(localPath)) {
    const buf = fs.readFileSync(localPath);
    const dataUri = `data:image/png;base64,${buf.toString("base64")}`;
    logoDataUriCache[key] = dataUri;
    return dataUri;
  }

  // Fallback to remote URL
  return resolveLogoUrl(brand ?? getBrand("wihy"));
}

// ── Local asset resolver (base64 data URIs for app screenshots, book covers) ─
const assetDataUriCache: Record<string, string> = {};

/** Brand-specific showcase assets: CG = app screenshots, Vowels = book covers */
const BRAND_ASSETS: Record<string, string[]> = {
  communitygroceries: [
    "CommunityGroceries/CG_home.png",
    "CommunityGroceries/smartmealhome.png",
    "CommunityGroceries/chatscreen.png",
    "CommunityGroceries/shoppinglist.png",
    "CommunityGroceries/MealTemplatesScreen.png",
    "CommunityGroceries/cookinginstructions.png",
    "CommunityGroceries/mypantry.png",
    "CommunityGroceries/calendarplan.png",
    "CommunityGroceries/instacartpage.png",
  ],
  vowels: [
    "ChildrensNutrition/BookGreen.jpg",
    "ChildrensNutrition/BookOrange.jpg",
    "ChildrensNutrition/Book6.jpg",
  ],
};

/** Resolve a brand asset file to a base64 data URI. Picks randomly from available assets. */
function resolveBrandAssetDataUri(brand?: BrandProfile): string | undefined {
  const brandId = brand?.id ?? "wihy";
  const key = BRAND_ASSETS[brandId]
    ? brandId
    : (brand?.parentBrand && BRAND_ASSETS[brand.parentBrand])
    ? brand.parentBrand
    : undefined;
  if (!key) return undefined;

  const assets = BRAND_ASSETS[key];
  const pick = assets[Math.floor(Math.random() * assets.length)];
  const cacheKey = `${key}:${pick}`;

  if (assetDataUriCache[cacheKey]) return assetDataUriCache[cacheKey];

  const localPath = path.join(ASSETS_DIR, pick);
  if (fs.existsSync(localPath)) {
    const buf = fs.readFileSync(localPath);
    const ext = path.extname(pick).toLowerCase();
    const mime = ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
    const dataUri = `data:${mime};base64,${buf.toString("base64")}`;
    assetDataUriCache[cacheKey] = dataUri;
    return dataUri;
  }

  return undefined;
}

function pickArtDirection(brand?: BrandProfile): ArtDirection {
  const family = brand?.id === "communitygroceries"
    ? ["lifestyle", "editorial", "poster"]
    : (brand?.id === "vowels" || brand?.parentBrand === "vowels")
    ? ["data_lab", "editorial", "poster"]
    : ["poster", "editorial", "data_lab", "lifestyle"];
  return family[Math.floor(Math.random() * family.length)] as ArtDirection;
}

// ── Color palettes for randomization ────────────────────────────────────────

interface ColorPalette {
  name: string;
  bg1: string;       // gradient start
  bg2: string;       // gradient end
  accent: string;    // accent color (dividers, highlights)
  glow: string;      // radial glow color (rgba)
  btnBg: string;     // CTA button background
  btnText: string;   // CTA button text
}

/** CG palette: warm, light backgrounds with dark text */
interface CGPalette {
  name: string;
  bg1: string;         // light background
  bg2: string;         // subtle gradient end
  accent: string;      // primary accent (green)
  accent2: string;     // secondary accent (orange/warm)
  textPrimary: string; // dark heading text
  textSecondary: string; // muted body text
  tagBg: string;       // tag background
  btnBg: string;       // CTA button background
  btnText: string;     // CTA button text
}

/** Vowels palette: light backgrounds with blue/purple academic tones */
interface VowelsPalette {
  name: string;
  bg1: string;
  bg2: string;
  accent: string;
  accent2: string;
  textPrimary: string;
  textSecondary: string;
  tagBg: string;
  btnBg: string;
  btnText: string;
}

const VOWELS_PALETTES: VowelsPalette[] = [
  { name: "ice-blue",        bg1: "#eff6ff", bg2: "#e0f2fe", accent: "#1e40af", accent2: "#7c3aed", textPrimary: "#1e293b", textSecondary: "#475569", tagBg: "rgba(30,64,175,0.08)",  btnBg: "#1e40af", btnText: "#ffffff" },
  { name: "lavender-mist",   bg1: "#faf5ff", bg2: "#ede9fe", accent: "#7c3aed", accent2: "#1e40af", textPrimary: "#1e1b4b", textSecondary: "#6b7280", tagBg: "rgba(124,58,237,0.08)", btnBg: "#7c3aed", btnText: "#ffffff" },
  { name: "steel-white",     bg1: "#f8fafc", bg2: "#f1f5f9", accent: "#2563eb", accent2: "#8b5cf6", textPrimary: "#0f172a", textSecondary: "#64748b", tagBg: "rgba(37,99,235,0.08)",  btnBg: "#2563eb", btnText: "#ffffff" },
  { name: "arctic-indigo",   bg1: "#eef2ff", bg2: "#e0e7ff", accent: "#4338ca", accent2: "#6d28d9", textPrimary: "#1e1b4b", textSecondary: "#6366f1", tagBg: "rgba(67,56,202,0.08)",  btnBg: "#4338ca", btnText: "#ffffff" },
  { name: "cloud-periwinkle",bg1: "#f5f3ff", bg2: "#eff6ff", accent: "#3b82f6", accent2: "#a78bfa", textPrimary: "#1e293b", textSecondary: "#6b7280", tagBg: "rgba(59,130,246,0.08)", btnBg: "#3b82f6", btnText: "#ffffff" },
  { name: "frost-violet",    bg1: "#fefce8", bg2: "#faf5ff", accent: "#7c3aed", accent2: "#2563eb", textPrimary: "#1e1b4b", textSecondary: "#78716c", tagBg: "rgba(124,58,237,0.08)", btnBg: "#7c3aed", btnText: "#ffffff" },
];

const PALETTES: ColorPalette[] = [
  { name: "midnight-teal",    bg1: "#0f172a", bg2: "#0d3b42", accent: "#2dd4bf", glow: "rgba(45,212,191,0.08)",  btnBg: "#2dd4bf", btnText: "#0f172a" },
  { name: "deep-purple",      bg1: "#1e1b4b", bg2: "#312e81", accent: "#a78bfa", glow: "rgba(167,139,250,0.08)", btnBg: "#a78bfa", btnText: "#1e1b4b" },
  { name: "ember",            bg1: "#1c1917", bg2: "#431407", accent: "#fb923c", glow: "rgba(251,146,60,0.08)",  btnBg: "#fb923c", btnText: "#1c1917" },
  { name: "ocean",            bg1: "#0c1d2e", bg2: "#1e3a5f", accent: "#38bdf8", glow: "rgba(56,189,248,0.08)",  btnBg: "#38bdf8", btnText: "#0c1d2e" },
  { name: "forest",           bg1: "#0a1f0a", bg2: "#14532d", accent: "#4ade80", glow: "rgba(74,222,128,0.08)",  btnBg: "#4ade80", btnText: "#0a1f0a" },
  { name: "rose",             bg1: "#1a0a14", bg2: "#4c0519", accent: "#fb7185", glow: "rgba(251,113,133,0.08)", btnBg: "#fb7185", btnText: "#1a0a14" },
  { name: "gold",             bg1: "#1c1a0e", bg2: "#422006", accent: "#fbbf24", glow: "rgba(251,191,36,0.08)",  btnBg: "#fbbf24", btnText: "#1c1a0e" },
  { name: "arctic",           bg1: "#0f172a", bg2: "#1e293b", accent: "#e2e8f0", glow: "rgba(226,232,240,0.06)", btnBg: "#f8fafc", btnText: "#0f172a" },
  { name: "coral",            bg1: "#18181b", bg2: "#3f1515", accent: "#f97316", glow: "rgba(249,115,22,0.08)",  btnBg: "#f97316", btnText: "#18181b" },
  { name: "lavender",         bg1: "#1a1625", bg2: "#2e1065", accent: "#c084fc", glow: "rgba(192,132,252,0.08)", btnBg: "#c084fc", btnText: "#1a1625" },
  { name: "mint",             bg1: "#0d1117", bg2: "#064e3b", accent: "#34d399", glow: "rgba(52,211,153,0.08)",  btnBg: "#34d399", btnText: "#0d1117" },
  { name: "steel",            bg1: "#111827", bg2: "#1f2937", accent: "#9ca3af", glow: "rgba(156,163,175,0.06)", btnBg: "#d1d5db", btnText: "#111827" },
];

const CG_PALETTES: CGPalette[] = [
  { name: "garden-cream",    bg1: "#fefce8", bg2: "#f0fdf4", accent: "#166534", accent2: "#f97316", textPrimary: "#14532d", textSecondary: "#4b5563", tagBg: "rgba(22,101,52,0.08)", btnBg: "#166534", btnText: "#ffffff" },
  { name: "warm-linen",      bg1: "#fffbeb", bg2: "#fef3c7", accent: "#b45309", accent2: "#166534", textPrimary: "#78350f", textSecondary: "#6b7280", tagBg: "rgba(180,83,9,0.08)",  btnBg: "#b45309", btnText: "#ffffff" },
  { name: "sage-mist",       bg1: "#f0fdf4", bg2: "#ecfdf5", accent: "#059669", accent2: "#d97706", textPrimary: "#064e3b", textSecondary: "#6b7280", tagBg: "rgba(5,150,105,0.08)", btnBg: "#059669", btnText: "#ffffff" },
  { name: "peach-bloom",     bg1: "#fff7ed", bg2: "#fef2f2", accent: "#ea580c", accent2: "#16a34a", textPrimary: "#7c2d12", textSecondary: "#6b7280", tagBg: "rgba(234,88,12,0.08)", btnBg: "#ea580c", btnText: "#ffffff" },
  { name: "fresh-ivory",     bg1: "#fafaf9", bg2: "#f5f5f4", accent: "#15803d", accent2: "#fb923c", textPrimary: "#1c1917", textSecondary: "#78716c", tagBg: "rgba(21,128,61,0.08)", btnBg: "#15803d", btnText: "#ffffff" },
  { name: "morning-sky",     bg1: "#f0f9ff", bg2: "#f0fdf4", accent: "#0d9488", accent2: "#f59e0b", textPrimary: "#134e4a", textSecondary: "#6b7280", tagBg: "rgba(13,148,136,0.08)", btnBg: "#0d9488", btnText: "#ffffff" },
  { name: "harvest-gold",    bg1: "#fffbeb", bg2: "#fefce8", accent: "#ca8a04", accent2: "#15803d", textPrimary: "#713f12", textSecondary: "#78716c", tagBg: "rgba(202,138,4,0.08)", btnBg: "#ca8a04", btnText: "#ffffff" },
  { name: "meadow-sun",      bg1: "#ecfdf5", bg2: "#fef9c3", accent: "#16a34a", accent2: "#ea580c", textPrimary: "#14532d", textSecondary: "#6b7280", tagBg: "rgba(22,163,74,0.08)", btnBg: "#16a34a", btnText: "#ffffff" },
];

function randomPalette(): ColorPalette {
  return PALETTES[Math.floor(Math.random() * PALETTES.length)];
}

function randomCGPalette(): CGPalette {
  return CG_PALETTES[Math.floor(Math.random() * CG_PALETTES.length)];
}

function randomVowelsPalette(): VowelsPalette {
  return VOWELS_PALETTES[Math.floor(Math.random() * VOWELS_PALETTES.length)];
}

function findPaletteByName<T extends { name: string }>(
  palettes: T[],
  name: string,
  fallback: T,
): T {
  return palettes.find((p) => p.name === name) ?? fallback;
}

// ── Handlebars helpers ──────────────────────────────────────────────────────

Handlebars.registerHelper("eq", (a: unknown, b: unknown) => a === b);
Handlebars.registerHelper("gte", (a: number, b: number) => a >= b);
Handlebars.registerHelper("indexPlusOne", function (this: { index?: number }, options: Handlebars.HelperOptions) {
  return (options.data.index ?? 0) + 1;
});

// ── Template cache ──────────────────────────────────────────────────────────

const templateCache = new Map<string, HandlebarsTemplateDelegate>();
const COMPILED_TEMPLATES_DIR = path.join(__dirname, "..", "templates");
const SOURCE_TEMPLATES_DIR = path.join(process.cwd(), "src", "templates");

function resolveTemplatesDir(): string {
  if (fs.existsSync(SOURCE_TEMPLATES_DIR)) return SOURCE_TEMPLATES_DIR;
  if (fs.existsSync(COMPILED_TEMPLATES_DIR)) return COMPILED_TEMPLATES_DIR;
  return COMPILED_TEMPLATES_DIR;
}

function getTemplateDir(templateId: string): string {
  // Map template IDs like "hook_square" to directory names like "hook-square"
  return templateId.replace(/_/g, "-");
}

function loadTemplate(templateId: string): HandlebarsTemplateDelegate {
  const cached = templateCache.get(templateId);
  if (cached) return cached;

  const dir = getTemplateDir(templateId);
  const htmlPath = path.join(resolveTemplatesDir(), dir, "template.html");

  if (!fs.existsSync(htmlPath)) {
    throw new Error(`Template not found: ${templateId} (looked in ${htmlPath})`);
  }

  const source = fs.readFileSync(htmlPath, "utf-8");
  const compiled = Handlebars.compile(source);
  templateCache.set(templateId, compiled);
  logger.info(`Template loaded: ${templateId}`);
  return compiled;
}

// ── Brand style block ───────────────────────────────────────────────────────

function buildBrandStyleBlock(width: number, height: number): string {
  return `<style>${BRAND.fontImport}\n${brandCSSVars()}\n:root{--canvas-w:${width}px;--canvas-h:${height}px;--bg1:${BRAND.colors.backgroundDark};--bg2:${BRAND.colors.background};--accent:${BRAND.colors.primary};--glow:rgba(250,95,6,0.12);--btn-bg:${BRAND.colors.primary};--btn-text:${BRAND.colors.white};--text-primary:${BRAND.colors.white};--text-secondary:rgba(249,250,251,0.78);}</style>`;
}

// ── Public API ──────────────────────────────────────────────────────────────

export function renderTemplate(
  templateId: string,
  data: TemplateData,
  outputSize: FormatKey = DEFAULT_FORMAT,
  brandId?: string,
): string {
  // Auto-detect brand from template prefix if not explicitly provided
  const effectiveBrand = brandId
    || (templateId.startsWith("cg_") ? "communitygroceries" : undefined)
    || (templateId.startsWith("vowels_") ? "vowels" : undefined);

  // If a brand is specified (or auto-detected), delegate to the brand-aware renderer
  if (effectiveBrand) {
    const brand = getBrand(effectiveBrand);
    return renderTemplateForBrand(templateId, data, brand, outputSize);
  }

  const template = loadTemplate(templateId);
  const format = FORMATS[outputSize];
  if (!format) {
    throw new Error(`Unknown output size: ${outputSize}. Valid: ${Object.keys(FORMATS).join(", ")}`);
  }

  const context = {
    ...data,
    width: format.width,
    height: format.height,
    brandStyles: buildBrandStyleBlock(format.width, format.height),
    showLogo: data.showLogo !== false,
    theme: data.theme || "wihy_default",
    artDirection: data.artDirection || pickArtDirection(),
    logoUrl: resolveLogoDataUri(),
    brandAssetUrl: resolveBrandAssetDataUri(),
  };

  return template(context);
}

/** List available template IDs. */
export function listTemplateIds(): string[] {
  const templatesDir = resolveTemplatesDir();
  if (!fs.existsSync(templatesDir)) return [];
  return fs.readdirSync(templatesDir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .filter((d) => fs.existsSync(path.join(templatesDir, d.name, "template.html")))
    .map((d) => d.name.replace(/-/g, "_"));
}

/**
 * Render a template with brand-specific colors applied.
 * Uses the per-brand color profile instead of the global WIHY defaults.
 */
export function renderTemplateForBrand(
  templateId: string,
  data: TemplateData,
  brand: BrandProfile,
  outputSize: FormatKey = DEFAULT_FORMAT,
): string {
  const template = loadTemplate(templateId);
  const format = FORMATS[outputSize];
  if (!format) {
    throw new Error(`Unknown output size: ${outputSize}. Valid: ${Object.keys(FORMATS).join(", ")}`);
  }

  const brandStyleBlock = buildBrandStyleBlockForBrand(format.width, format.height, brand);

  const context = {
    ...data,
    width: format.width,
    height: format.height,
    brandStyles: brandStyleBlock,
    showLogo: data.showLogo !== false,
    theme: data.theme || "wihy_default",
    artDirection: data.artDirection || pickArtDirection(brand),
    logoUrl: resolveLogoDataUri(brand),
    brandAssetUrl: resolveBrandAssetDataUri(brand),
  };

  return template(context);
}

/** Build CSS custom properties using a specific brand's colors. */
function buildBrandStyleBlockForBrand(width: number, height: number, brand: BrandProfile): string {
  // CG brand → CG light palettes
  if (brand.id === "communitygroceries") {
    const p = findPaletteByName(CG_PALETTES, "garden-cream", CG_PALETTES[0]);
    logger.info(`Using CG palette: ${p.name} (fixed)`);
    return `<style>${BRAND.fontImport}
      :root {
        --font-headline: ${BRAND.fonts.headline};
        --font-body: ${BRAND.fonts.body};
        --canvas-w: ${width}px;
        --canvas-h: ${height}px;
        --bg1: ${p.bg1};
        --bg2: ${p.bg2};
        --accent: ${p.accent};
        --accent2: ${p.accent2};
        --text-primary: ${p.textPrimary};
        --text-secondary: ${p.textSecondary};
        --tag-bg: ${p.tagBg};
        --glow: rgba(0,0,0,0);
        --btn-bg: ${p.btnBg};
        --btn-text: ${p.btnText};
      }
    </style>`;
  }

  // Vowels family (vowels + sub-brands) → Vowels blue/purple palettes
  const isVowelsFamily = brand.id === "vowels" || brand.parentBrand === "vowels";
  if (isVowelsFamily) {
    const paletteNameByBrand: Record<string, string> = {
      vowels: "ice-blue",
      childrennutrition: "ice-blue",
      parentingwithchrist: "lavender-mist",
      snackingwell: "steel-white",
      otakulounge: "arctic-indigo",
    };
    const preferred = paletteNameByBrand[brand.id] ?? "ice-blue";
    const p = findPaletteByName(VOWELS_PALETTES, preferred, VOWELS_PALETTES[0]);
    logger.info(`Using Vowels palette: ${p.name} (fixed, brand: ${brand.id})`);
    return `<style>${BRAND.fontImport}
      :root {
        --font-headline: ${BRAND.fonts.headline};
        --font-body: ${BRAND.fonts.body};
        --canvas-w: ${width}px;
        --canvas-h: ${height}px;
        --bg1: ${p.bg1};
        --bg2: ${p.bg2};
        --accent: ${p.accent};
        --accent2: ${p.accent2};
        --text-primary: ${p.textPrimary};
        --text-secondary: ${p.textSecondary};
        --tag-bg: ${p.tagBg};
        --glow: rgba(0,0,0,0);
        --btn-bg: ${p.btnBg};
        --btn-text: ${p.btnText};
      }
    </style>`;
  }

  // Default: WIHY dark palettes
  const p = findPaletteByName(PALETTES, "ocean", PALETTES[0]);
  logger.info(`Using WIHY palette: ${p.name} (fixed)`);
  return `<style>${BRAND.fontImport}
    :root {
      --font-headline: ${BRAND.fonts.headline};
      --font-body: ${BRAND.fonts.body};
      --canvas-w: ${width}px;
      --canvas-h: ${height}px;
      --bg1: ${p.bg1};
      --bg2: ${p.bg2};
      --accent: ${p.accent};
      --glow: ${p.glow};
      --btn-bg: ${p.btnBg};
      --btn-text: ${p.btnText};
      --text-primary: #f1f5f9;
      --text-secondary: rgba(241,245,249,0.55);
    }
  </style>`;
}

/** Clear template cache (e.g. after hot-reload in dev). */
export function clearTemplateCache(): void {
  templateCache.clear();
}
