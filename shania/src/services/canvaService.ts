/**
 * canvaService.ts � Canva Connect API client for brand design generation
 *
 * Uses OAuth 2.0 (Authorization Code + PKCE) with rotating refresh tokens.
 * Implements the Autofill + Export async job pipeline:
 *   1. POST /autofills      -> create autofill job (async)
 *   2. GET  /autofills/{id} -> poll until design is ready
 *   3. POST /exports        -> create export job (async)
 *   4. GET  /exports/{id}   -> poll until PNG URL is ready
 *   5. Download PNG bytes from the export URL
 *
 * Brand templates are Canva Brand Templates with named Data autofill fields.
 * Required field names to configure in each Canva template via "Data autofill" app:
 *   HEADLINE, SUBTEXT, BODY, CTA, QUOTE, ATTRIBUTION,
 *   STAT_NUMBER, STAT_LABEL, TIP, SOURCE, PHOTO (image field)
 *
 * NOTE: Brand Templates + Autofill require Canva Enterprise.
 * Without Enterprise, request dev access in the Canva Developer Portal.
 */

import { logger } from "../utils/logger";
import { BrandId } from "../config/brand";

// -- Constants ----------------------------------------------------------------

const API_BASE = "https://api.canva.com/rest/v1";
const TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token";

/** Poll interval for async jobs (ms) */
const POLL_INTERVAL_MS = 2_000;
/** Max polling attempts before timeout (~60s) */
const MAX_POLL_ATTEMPTS = 30;
const CANVA_TEMPLATE_DEBUG = ["1", "true", "yes", "on"].includes(
  (process.env.SHANIA_CANVA_TEMPLATE_DEBUG || "").toLowerCase(),
);

// -- Brand Template Map -------------------------------------------------------

/** Maps each brand to its Canva Brand Template ID */
const BRAND_CANVA_TEMPLATES: Record<BrandId, string> = {
  wihy: process.env.CANVA_TEMPLATE_WIHY || "",
  communitygroceries: process.env.CANVA_TEMPLATE_CG || "",
  vowels: process.env.CANVA_TEMPLATE_VOWELS || "",
  snackingwell: process.env.CANVA_TEMPLATE_SNACKINGWELL || "",
  childrennutrition: process.env.CANVA_TEMPLATE_CHILDRENNUTRITION || "",
  parentingwithchrist: process.env.CANVA_TEMPLATE_PARENTINGWITHCHRIST || "",
  otakulounge: process.env.CANVA_TEMPLATE_OTAKULOUNGE || "",
};

/**
 * Optional style-specific template pools. Each env var can contain one ID or
 * a comma-separated list of IDs for rotation.
 */
const STYLE_TEMPLATE_ENV_KEYS: Record<BrandId, Record<string, string[]>> = {
  wihy: {
    data: ["CANVA_TEMPLATE_WIHY_DATA", "CANVA_TEMPLATE_WIHY_STAT"],
    editorial: ["CANVA_TEMPLATE_WIHY_EDITORIAL"],
    app: ["CANVA_TEMPLATE_WIHY_APP"],
    hook: ["CANVA_TEMPLATE_WIHY_HOOK"],
  },
  communitygroceries: {
    warm: ["CANVA_TEMPLATE_CG_WARM"],
    recipe: ["CANVA_TEMPLATE_CG_RECIPE"],
    community: ["CANVA_TEMPLATE_CG_COMMUNITY"],
  },
  vowels: {
    data: ["CANVA_TEMPLATE_VOWELS_DATA"],
    community: ["CANVA_TEMPLATE_VOWELS_COMMUNITY"],
    clean: ["CANVA_TEMPLATE_VOWELS_CLEAN"],
  },
  snackingwell: {},
  childrennutrition: {},
  parentingwithchrist: {},
  otakulounge: {},
};

// -- Configuration -------------------------------------------------------------

export interface CanvaOAuthConfig {
  clientId: string;
  clientSecret: string;
  /** Current refresh token � rotates on every access token refresh */
  refreshToken: string;
  /**
   * Called whenever the refresh token rotates.
   * Use this to persist the new token to GCP Secret Manager.
   */
  onTokenRefresh?: (newRefreshToken: string) => Promise<void>;
}

// -- Design Data ---------------------------------------------------------------

/**
 * Fields to inject into a Canva Brand Template via the Autofill API.
 * Each property maps to a named data field configured in the Canva template.
 *
 * Text fields: configure in Canva with "Data autofill" app -> field name = HEADLINE etc.
 * Image fields: configure in Canva with "Data autofill" app -> field name = PHOTO etc.
 */
export interface DesignData {
  headline?: string;
  subtext?: string;
  body?: string;
  cta?: string;
  quote?: string;
  attribution?: string;
  statNumber?: string;
  statLabel?: string;
  tip?: string;
  tipLabel?: string;
  source?: string;
  dataPoints?: string[];
  /** Photo as a data URL or external URL (for future asset upload integration) */
  photoUrl?: string;
  /** Pre-uploaded Canva asset ID for the main photo (use asset upload API first) */
  photoAssetId?: string;
  [key: string]: unknown;
}

export interface CanvaRenderOptions {
  /** Template family from Gemini (e.g., stat_pulse, app_showcase, cg_warm_card) */
  templateHint?: string;
}

interface TemplateSelection {
  templateId: string;
  styleKey?: string;
  pool: string[];
  cursorKey: string;
  cursorIndex: number;
  templateHint?: string;
}

// -- Internal API Types --------------------------------------------------------

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

interface AutofillJobResponse {
  job: {
    id: string;
    status: "in_progress" | "success" | "failed";
    result?: {
      type: string;
      design: {
        url: string;
        thumbnail?: { url: string };
      };
    };
    error?: { code: string; message: string };
  };
}

interface ExportJobResponse {
  job: {
    id: string;
    status: "in_progress" | "success" | "failed";
    urls?: string[];
    error?: { code: string; message: string };
  };
}

// -- Helpers -------------------------------------------------------------------

/**
 * Extract design ID from a Canva design URL.
 * e.g. "https://www.canva.com/design/DAVZr1z5464/edit" -> "DAVZr1z5464"
 */
function extractDesignId(url: string): string | null {
  const match = url.match(/\/design\/([A-Za-z0-9_-]+)\//);
  return match?.[1] ?? null;
}

/** Map DesignData fields to the Canva autofill data payload */
function buildAutofillData(
  data: DesignData,
): Record<string, { type: "text"; text: string } | { type: "image"; asset_id: string }> {
  const result: Record<
    string,
    { type: "text"; text: string } | { type: "image"; asset_id: string }
  > = {};

  const textFields: Array<[string, string]> = [
    ["headline", "HEADLINE"],
    ["subtext", "SUBTEXT"],
    ["body", "BODY"],
    ["cta", "CTA"],
    ["quote", "QUOTE"],
    ["attribution", "ATTRIBUTION"],
    ["statNumber", "STAT_NUMBER"],
    ["statLabel", "STAT_LABEL"],
    ["tip", "TIP"],
    ["source", "SOURCE"],
  ];

  for (const [prop, fieldName] of textFields) {
    const value = data[prop];
    if (typeof value === "string" && value.trim()) {
      result[fieldName] = { type: "text", text: value };
    }
  }

  if (data.photoAssetId) {
    result["PHOTO"] = { type: "image", asset_id: data.photoAssetId };
  }

  return result;
}

function parseTemplatePool(raw: string | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function mapTemplateHintToStyle(brandId: BrandId, templateHint?: string): string | undefined {
  if (!templateHint) return undefined;

  if (brandId === "wihy") {
    if (["stat_card", "stat_pulse", "research_card"].includes(templateHint)) return "data";
    if (["editorial_signal", "wihy_signal_clean"].includes(templateHint)) return "editorial";
    if (["app_showcase"].includes(templateHint)) return "app";
    if (["hook_square", "hook_vertical", "cta_card", "quote_card"].includes(templateHint)) return "hook";
  }

  if (brandId === "communitygroceries") {
    if (templateHint === "cg_warm_card") return "warm";
    if (templateHint === "cg_recipe_tip") return "recipe";
    if (templateHint === "cg_community") return "community";
  }

  if (brandId === "vowels") {
    if (templateHint === "vowels_data_card" || templateHint === "vowels_research_tip") return "data";
    if (templateHint === "vowels_community") return "community";
    if (templateHint === "vowels_clean_card") return "clean";
  }

  return undefined;
}

// -- Client --------------------------------------------------------------------

export class CanvaClient {
  private readonly clientId: string;
  private readonly clientSecret: string;
  private refreshToken: string;
  private accessToken: string | null = null;
  private accessTokenExpiry: number = 0;
  private readonly templateCursor: Record<string, number> = {};
  private readonly onTokenRefresh?: (newRefreshToken: string) => Promise<void>;

  constructor(config: CanvaOAuthConfig) {
    if (!config.clientId || !config.clientSecret || !config.refreshToken) {
      throw new Error(
        "Canva OAuth credentials incomplete. Provide clientId, clientSecret, and refreshToken.",
      );
    }
    this.clientId = config.clientId;
    this.clientSecret = config.clientSecret;
    this.refreshToken = config.refreshToken;
    this.onTokenRefresh = config.onTokenRefresh;
  }

  // -- Token Management ------------------------------------------------------

  private basicAuthHeader(): string {
    return Buffer.from(`${this.clientId}:${this.clientSecret}`).toString("base64");
  }

  private async getAccessToken(): Promise<string> {
    // Reuse cached token if still valid (with 60s safety margin)
    if (this.accessToken && Date.now() < this.accessTokenExpiry - 60_000) {
      return this.accessToken;
    }
    return this.refreshAccessToken();
  }

  private async refreshAccessToken(): Promise<string> {
    logger.info("Refreshing Canva access token via refresh token...");

    const response = await fetch(TOKEN_URL, {
      method: "POST",
      headers: {
        Authorization: `Basic ${this.basicAuthHeader()}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: this.refreshToken,
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Canva token refresh failed (${response.status}): ${body}`);
    }

    const data = (await response.json()) as TokenResponse;
    this.accessToken = data.access_token;
    this.accessTokenExpiry = Date.now() + data.expires_in * 1_000;

    // Refresh tokens rotate � persist the new one immediately
    this.refreshToken = data.refresh_token;
    if (this.onTokenRefresh) {
      await this.onTokenRefresh(data.refresh_token).catch((err) =>
        logger.error(`Failed to persist rotated Canva refresh token: ${err}`),
      );
    }

    logger.info("Canva access token refreshed successfully");
    return this.accessToken;
  }

  // -- HTTP Helper -----------------------------------------------------------

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const token = await this.getAccessToken();
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Canva API ${method} ${path} failed (${response.status}): ${errorText}`);
    }

    return response.json() as Promise<T>;
  }

  private getTemplatePoolForBrand(brandId: BrandId, styleKey?: string): string[] {
    if (styleKey) {
      const envKeys = STYLE_TEMPLATE_ENV_KEYS[brandId]?.[styleKey] ?? [];
      const stylePool = envKeys.flatMap((key) => parseTemplatePool(process.env[key]));
      if (stylePool.length > 0) return stylePool;
    }

    const basePool = parseTemplatePool(BRAND_CANVA_TEMPLATES[brandId]);
    return basePool;
  }

  private pickTemplateSelection(brandId: BrandId, templateHint?: string): TemplateSelection {
    const styleKey = mapTemplateHintToStyle(brandId, templateHint);
    const pool = this.getTemplatePoolForBrand(brandId, styleKey);

    if (pool.length === 0) {
      throw new Error(
        `No Canva brand template configured for brand "${brandId}"` +
          (styleKey ? ` (style: ${styleKey})` : "") +
          `. Set CANVA_TEMPLATE_${brandId.toUpperCase()} or style-specific env vars.`,
      );
    }

    const cursorKey = `${brandId}:${styleKey ?? "base"}`;
    const idx = this.templateCursor[cursorKey] ?? 0;
    const selected = pool[idx % pool.length];
    this.templateCursor[cursorKey] = idx + 1;

    return {
      templateId: selected,
      styleKey,
      pool,
      cursorKey,
      cursorIndex: idx,
      templateHint,
    };
  }

  // -- Async Job Polling -----------------------------------------------------

  private async pollUntilDone<T extends { job: { status: string } }>(
    fetchJob: () => Promise<T>,
  ): Promise<T> {
    for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt++) {
      const result = await fetchJob();
      if (result.job.status !== "in_progress") {
        return result;
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
    throw new Error(
      `Canva job timed out after ${MAX_POLL_ATTEMPTS * POLL_INTERVAL_MS}ms of polling`,
    );
  }

  // -- Autofill API ----------------------------------------------------------

  /**
   * Create an autofill job that populates a brand template with the supplied data.
   * Returns the resulting Canva design ID.
   *
   * Requires: brand template configured with named Data autofill fields in Canva.
   * Requires: Canva Enterprise subscription (or dev access approved in Developer Portal).
   */
  async autofillBrandTemplate(
    brandId: BrandId,
    data: DesignData,
    options?: CanvaRenderOptions,
  ): Promise<string> {
    const selection = this.pickTemplateSelection(brandId, options?.templateHint);
    const { templateId } = selection;

    const autofillData = buildAutofillData(data);
    logger.info(
      `Creating Canva autofill job for ${brandId} (template: ${templateId}, style: ${selection.styleKey || "base"}, templateHint: ${options?.templateHint || "none"}, fields: ${Object.keys(autofillData).join(", ")})`,
    );

    if (CANVA_TEMPLATE_DEBUG) {
      logger.info(
        `Canva template selection debug: ${JSON.stringify({
          brandId,
          templateHint: selection.templateHint,
          styleKey: selection.styleKey || "base",
          cursorKey: selection.cursorKey,
          cursorIndex: selection.cursorIndex,
          poolSize: selection.pool.length,
          selectedTemplateId: selection.templateId,
          pool: selection.pool,
        })}`,
      );
    }

    const jobResp = await this.request<AutofillJobResponse>("POST", "/autofills", {
      brand_template_id: templateId,
      data: autofillData,
    });

    const jobId = jobResp.job.id;
    logger.info(`Autofill job started: ${jobId}`);

    const completed = await this.pollUntilDone(() =>
      this.request<AutofillJobResponse>("GET", `/autofills/${jobId}`),
    );

    if (completed.job.status === "failed") {
      throw new Error(`Canva autofill job failed for brand "${brandId}" (job: ${jobId})`);
    }

    const designUrl = completed.job.result?.design?.url ?? "";
    const designId = extractDesignId(designUrl);
    if (!designId) {
      throw new Error(
        `Could not extract design ID from Canva autofill result URL: "${designUrl}"`,
      );
    }

    logger.info(`Autofill complete for ${brandId}. Design ID: ${designId}`);
    return designId;
  }

  // -- Export API ------------------------------------------------------------

  /**
   * Export a design as PNG and return the raw image bytes.
   * Uses an async export job; polls until the download URL is available.
   */
  async exportDesignAsPng(designId: string): Promise<Buffer> {
    logger.info(`Creating Canva export job for design ${designId}`);

    const jobResp = await this.request<ExportJobResponse>("POST", "/exports", {
      design_id: designId,
      format: { type: "png" },
    });

    const jobId = jobResp.job.id;
    logger.info(`Export job started: ${jobId}`);

    const completed = await this.pollUntilDone(() =>
      this.request<ExportJobResponse>("GET", `/exports/${jobId}`),
    );

    if (completed.job.status === "failed") {
      const err = completed.job.error;
      throw new Error(
        `Canva export job failed (${err?.code ?? "unknown"}): ${err?.message ?? "no details"}`,
      );
    }

    const downloadUrl = completed.job.urls?.[0];
    if (!downloadUrl) {
      throw new Error("Canva export succeeded but response contained no download URLs");
    }

    logger.info(`Downloading exported PNG from Canva...`);
    const imgResp = await fetch(downloadUrl);
    if (!imgResp.ok) {
      throw new Error(`Failed to download Canva export (${imgResp.status}): ${downloadUrl}`);
    }

    const buf = Buffer.from(await imgResp.arrayBuffer());
    logger.info(`Canva PNG downloaded: ${buf.length} bytes`);
    return buf;
  }

  // -- Full Pipeline ---------------------------------------------------------

  /**
   * Full pipeline: autofill brand template -> export PNG -> return image buffer.
   * This is the primary entry point used by postGenerator.ts.
   */
  async generateDesignImage(
    brandId: BrandId,
    data: DesignData,
    options?: CanvaRenderOptions,
  ): Promise<Buffer> {
    const designId = await this.autofillBrandTemplate(brandId, data, options);
    return this.exportDesignAsPng(designId);
  }

  // -- Brand Templates -------------------------------------------------------

  /**
   * List all brand templates visible to the authenticated user.
   * Useful for discovering template IDs after creating them in Canva.
   */
  async listBrandTemplates(): Promise<Array<{ id: string; title: string }>> {
    const data = await this.request<{ items: Array<{ id: string; title: string }> }>(
      "GET",
      "/brand-templates",
    );
    return data.items ?? [];
  }

  /**
   * Get the autofill dataset for a brand template � shows available field names.
   * Use this to verify your template fields match what buildAutofillData() sends.
   */
  async getBrandTemplateDataset(templateId: string): Promise<Record<string, { type: string }>> {
    const data = await this.request<{ dataset: Record<string, { type: string }> }>(
      "GET",
      `/brand-templates/${templateId}/dataset`,
    );
    return data.dataset;
  }
}

// -- Singleton -----------------------------------------------------------------

let canvaClient: CanvaClient | null = null;

export function initCanvaClient(config: CanvaOAuthConfig): CanvaClient {
  canvaClient = new CanvaClient(config);
  return canvaClient;
}

export function getCanvaClient(): CanvaClient {
  if (!canvaClient) {
    throw new Error("Canva client not initialized. Call initCanvaClient() first.");
  }
  return canvaClient;
}
