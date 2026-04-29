import { SecretManagerServiceClient } from "@google-cloud/secret-manager";
import fs from "fs";
import path from "path";
import { logger } from "../utils/logger";

type JsonRecord = Record<string, unknown>;

export interface CanvaDesignSummary {
  id: string;
  title?: string;
  editUrl?: string;
  viewUrl?: string;
  pageCount?: number;
}

export interface CanvaBrandTemplateSummary {
  id: string;
  title?: string;
  viewUrl?: string;
  createUrl?: string;
  thumbnailUrl?: string;
  createdAt?: number;
  updatedAt?: number;
}

export interface CanvaBrandTemplateField {
  name: string;
  type?: string;
  label?: string;
}

export interface CanvaBrandTemplateWithDataset extends CanvaBrandTemplateSummary {
  dataset: JsonRecord;
  fields: CanvaBrandTemplateField[];
}

export interface CanvaResizeRequest {
  sourceDesignId?: string;
  assetId?: string;
  title?: string;
  presetName?: string;
  width?: number;
  height?: number;
}

const CANVA_API_BASE = "https://api.canva.com/rest/v1";
const PROJECT_ID = process.env.GCP_PROJECT || "wihy-ai";

const SECRET_NAME_CLIENT_ID = process.env.CANVA_CLIENT_ID_SECRET || "canva-client-id";
const SECRET_NAME_CLIENT_SECRET = process.env.CANVA_CLIENT_SECRET_SECRET || "canva-client-secret";
const SECRET_NAME_REFRESH_TOKEN = process.env.CANVA_REFRESH_TOKEN_SECRET || "canva-refresh-token";

const ENV_CLIENT_ID = (process.env.CANVA_CLIENT_ID || "").trim();
const ENV_CLIENT_SECRET = (process.env.CANVA_CLIENT_SECRET || "").trim();
const ENV_REFRESH_TOKEN = (process.env.CANVA_REFRESH_TOKEN || "").trim();
const ENV_LOCAL_REFRESH_TOKEN_PATH = (process.env.CANVA_LOCAL_REFRESH_TOKEN_PATH || "").trim();

const DEFAULT_LOCAL_REFRESH_TOKEN_PATH = path.resolve(process.cwd(), ".canva-refresh-token.local");

let secretClient: SecretManagerServiceClient | null = null;
let cachedToken: { accessToken: string; expiresAtMs: number } | null = null;
let pendingRefresh: Promise<string> | null = null;

function isCloudRunRuntime(): boolean {
  return Boolean((process.env.K_SERVICE || "").trim());
}

function getLocalRefreshTokenPath(): string {
  return ENV_LOCAL_REFRESH_TOKEN_PATH || DEFAULT_LOCAL_REFRESH_TOKEN_PATH;
}

function readLocalRefreshToken(): string {
  if (isCloudRunRuntime()) return "";
  const tokenPath = getLocalRefreshTokenPath();
  try {
    if (!fs.existsSync(tokenPath)) return "";
    return fs.readFileSync(tokenPath, "utf8").trim();
  } catch {
    return "";
  }
}

function writeLocalRefreshToken(token: string): void {
  if (isCloudRunRuntime()) return;
  const tokenPath = getLocalRefreshTokenPath();
  try {
    fs.writeFileSync(tokenPath, `${token.trim()}\n`, "utf8");
    logger.info(`Canva refresh token cached locally at ${tokenPath}`);
  } catch (err) {
    logger.warn(`Canva refresh token cache write failed: ${err instanceof Error ? err.message : String(err)}`);
  }
}

function getSecretClient(): SecretManagerServiceClient {
  if (!secretClient) {
    secretClient = new SecretManagerServiceClient();
  }
  return secretClient;
}

function hasEnvCredentials(): boolean {
  return Boolean(ENV_CLIENT_ID && ENV_CLIENT_SECRET && ENV_REFRESH_TOKEN);
}

async function readSecret(secretId: string): Promise<string> {
  const name = `projects/${PROJECT_ID}/secrets/${secretId}/versions/latest`;
  const [version] = await getSecretClient().accessSecretVersion({ name });
  const rawBytes = version.payload?.data;
  const data = rawBytes ? Buffer.from(rawBytes).toString("utf8").trim() : "";
  if (!data) throw new Error(`Secret ${secretId} is empty`);
  return data;
}

async function addSecretVersion(secretId: string, value: string): Promise<void> {
  const parent = `projects/${PROJECT_ID}/secrets/${secretId}`;
  await getSecretClient().addSecretVersion({
    parent,
    payload: { data: Buffer.from(value, "utf8") },
  });
}

async function loadCredentials(): Promise<{ clientId: string; clientSecret: string; refreshToken: string }> {
  if (hasEnvCredentials()) {
    const localToken = readLocalRefreshToken();
    return {
      clientId: ENV_CLIENT_ID,
      clientSecret: ENV_CLIENT_SECRET,
      refreshToken: localToken || ENV_REFRESH_TOKEN,
    };
  }

  const [clientId, clientSecret, refreshToken] = await Promise.all([
    readSecret(SECRET_NAME_CLIENT_ID),
    readSecret(SECRET_NAME_CLIENT_SECRET),
    readSecret(SECRET_NAME_REFRESH_TOKEN),
  ]);

  return { clientId, clientSecret, refreshToken: readLocalRefreshToken() || refreshToken };
}

async function refreshAccessToken(): Promise<string> {
  const { clientId, clientSecret, refreshToken } = await loadCredentials();

  const body = new URLSearchParams({
    grant_type: "refresh_token",
    client_id: clientId,
    client_secret: clientSecret,
    refresh_token: refreshToken,
  });

  const response = await fetch(`${CANVA_API_BASE}/oauth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  const raw = await response.text();
  let payload: JsonRecord = {};
  try {
    payload = raw ? (JSON.parse(raw) as JsonRecord) : {};
  } catch {
    payload = { raw };
  }

  if (!response.ok) {
    throw new Error(`Canva token refresh failed (${response.status}): ${JSON.stringify(payload)}`);
  }

  const accessToken = String(payload.access_token || "");
  const expiresIn = Number(payload.expires_in || 3600);
  const rotatedRefreshToken = String(payload.refresh_token || "");

  if (!accessToken) {
    throw new Error("Canva token refresh succeeded but access_token missing");
  }

  // Always persist the rotated refresh token — even when credentials came from env vars.
  // This ensures local dev runs don't invalidate the Secret Manager token for Cloud Run.
  if (rotatedRefreshToken && rotatedRefreshToken !== refreshToken) {
    // Keep local testing stable even when ADC cannot update Secret Manager.
    writeLocalRefreshToken(rotatedRefreshToken);
    try {
      await addSecretVersion(SECRET_NAME_REFRESH_TOKEN, rotatedRefreshToken);
      logger.info("Canva refresh token rotated and stored in Secret Manager");
    } catch (err) {
      logger.warn(`Canva refresh token rotation: failed to update Secret Manager: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  cachedToken = {
    accessToken,
    // Refresh a minute early to avoid edge expirations.
    expiresAtMs: Date.now() + Math.max(60, expiresIn - 60) * 1000,
  };

  return accessToken;
}

async function getAccessToken(force = false): Promise<string> {
  if (!force && cachedToken && Date.now() < cachedToken.expiresAtMs) {
    return cachedToken.accessToken;
  }

  if (!pendingRefresh) {
    pendingRefresh = refreshAccessToken().finally(() => {
      pendingRefresh = null;
    });
  }
  return pendingRefresh;
}

async function canvaRequest<T = JsonRecord>(
  path: string,
  init?: Omit<RequestInit, "headers"> & { headers?: Record<string, string> },
): Promise<T> {
  const attempt = async (token: string): Promise<Response> => {
    return fetch(`${CANVA_API_BASE}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });
  };

  let response = await attempt(await getAccessToken(false));
  if (response.status === 401) {
    response = await attempt(await getAccessToken(true));
  }

  const raw = await response.text();
  let payload: JsonRecord = {};
  try {
    payload = raw ? (JSON.parse(raw) as JsonRecord) : {};
  } catch {
    payload = { raw };
  }

  if (!response.ok) {
    throw new Error(`Canva API ${path} failed (${response.status}): ${JSON.stringify(payload)}`);
  }

  return payload as T;
}

function summarizeDesign(payload: JsonRecord): CanvaDesignSummary {
  const design = (payload.design || payload) as JsonRecord;
  const urls = (design.urls || {}) as JsonRecord;
  const thumbnail = (design.thumbnail || {}) as JsonRecord;

  return {
    id: String(design.id || ""),
    title: typeof design.title === "string" ? design.title : undefined,
    editUrl: typeof urls.edit_url === "string" ? urls.edit_url : undefined,
    viewUrl: typeof urls.view_url === "string" ? urls.view_url : undefined,
    pageCount: Number.isFinite(Number(thumbnail.page_count))
      ? Number(thumbnail.page_count)
      : undefined,
  };
}

function summarizeBrandTemplate(payload: JsonRecord): CanvaBrandTemplateSummary {
  const template = (payload.brand_template || payload) as JsonRecord;
  const thumbnail = (template.thumbnail || {}) as JsonRecord;

  return {
    id: String(template.id || ""),
    title: typeof template.title === "string" ? template.title : undefined,
    viewUrl: typeof template.view_url === "string" ? template.view_url : undefined,
    createUrl: typeof template.create_url === "string" ? template.create_url : undefined,
    thumbnailUrl: typeof thumbnail.url === "string" ? thumbnail.url : undefined,
    createdAt: Number.isFinite(Number(template.created_at)) ? Number(template.created_at) : undefined,
    updatedAt: Number.isFinite(Number(template.updated_at)) ? Number(template.updated_at) : undefined,
  };
}

function extractBrandTemplateFields(dataset: JsonRecord): CanvaBrandTemplateField[] {
  return Object.entries(dataset)
    .map(([name, raw]) => {
      const field = (raw || {}) as JsonRecord;
      const type =
        typeof field.type === "string"
          ? field.type
          : typeof field.field_type === "string"
            ? field.field_type
            : undefined;
      const label =
        typeof field.label === "string"
          ? field.label
          : typeof field.display_name === "string"
            ? field.display_name
            : undefined;
      return { name, type, label };
    })
    .sort((left, right) => left.name.localeCompare(right.name));
}

function buildDesignType(req: CanvaResizeRequest): JsonRecord {
  if (req.presetName) {
    return {
      type: "preset",
      name: req.presetName,
    };
  }
  if (req.width && req.height) {
    return {
      type: "custom",
      width: req.width,
      height: req.height,
      unit: "px",
    };
  }
  throw new Error("Either presetName or width+height must be provided");
}

export async function getCanvaDesign(designId: string): Promise<CanvaDesignSummary> {
  const payload = await canvaRequest<JsonRecord>(`/designs/${encodeURIComponent(designId)}`);
  return summarizeDesign(payload);
}

export async function listCanvaBrandTemplates(): Promise<CanvaBrandTemplateSummary[]> {
  const payload = await canvaRequest<JsonRecord>("/brand-templates");
  const items = Array.isArray(payload.items) ? payload.items : [];
  return items
    .map((item) => summarizeBrandTemplate(item as JsonRecord))
    .sort((left, right) => (left.title || left.id).localeCompare(right.title || right.id));
}

export async function getCanvaBrandTemplateDataset(templateId: string): Promise<JsonRecord> {
  const payload = await canvaRequest<JsonRecord>(`/brand-templates/${encodeURIComponent(templateId)}/dataset`);
  const nested = payload.dataset;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    return nested as JsonRecord;
  }
  return payload;
}

export async function listCanvaBrandTemplatesWithDatasets(): Promise<CanvaBrandTemplateWithDataset[]> {
  const templates = await listCanvaBrandTemplates();
  return Promise.all(
    templates.map(async (template) => {
      const dataset = await getCanvaBrandTemplateDataset(template.id);
      return {
        ...template,
        dataset,
        fields: extractBrandTemplateFields(dataset),
      };
    }),
  );
}

/**
 * Canva's create-design supports creating from a preset/custom type and also copying
 * existing designs. The exact copy field names can vary by API version, so we try a
 * small set of documented/legacy-compatible payload shapes.
 */
export async function createOrResizeCanvaDesign(req: CanvaResizeRequest): Promise<CanvaDesignSummary> {
  const designType = buildDesignType(req);
  const basePayload: JsonRecord = {
    type: "type_and_asset",
    design_type: designType,
    title: req.title,
    ...(req.assetId ? { asset_id: req.assetId } : {}),
  };

  const payloadCandidates: JsonRecord[] = [];

  if (req.sourceDesignId) {
    payloadCandidates.push(
      {
        ...basePayload,
        source_design_id: req.sourceDesignId,
      },
      {
        ...basePayload,
        design_id: req.sourceDesignId,
      },
      {
        type: "copy_and_resize",
        design_type: designType,
        design_id: req.sourceDesignId,
        title: req.title,
      },
    );
  }

  payloadCandidates.push(basePayload);

  let lastError = "";
  for (const candidate of payloadCandidates) {
    try {
      const payload = await canvaRequest<JsonRecord>("/designs", {
        method: "POST",
        body: JSON.stringify(candidate),
      });
      return summarizeDesign(payload);
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
  }

  throw new Error(`Unable to create/resize Canva design: ${lastError}`);
}

// ── Asset upload ─────────────────────────────────────────────────────────

export interface CanvaAssetSummary {
  id: string;
  name?: string;
  url?: string;
  thumbnailUrl?: string;
}

/**
 * Upload image bytes to Canva as a new asset via the asset-upload job API.
 * Canva's asset upload protocol:
 *   1. POST /asset-uploads with:
 *      - Content-Type: <image mimeType>  (raw binary body)
 *      - Asset-Upload-Metadata: base64(JSON({ name_base64: base64(name) }))
 *   2. GET /asset-uploads/{job_id} → poll until status = success or failed
 *
 * Returns the Canva asset once the upload job succeeds.
 */
export async function uploadImageAsCanvaAsset(
  imageBytes: Buffer,
  mimeType: string,
  name: string,
): Promise<CanvaAssetSummary> {
  const token = await getAccessToken();

  // Canva requires metadata as a raw JSON string in the Asset-Upload-Metadata header.
  // The name itself is base64-encoded inside the JSON, but the header value is NOT base64.
  // See: https://www.canva.dev/docs/connect/api-reference/assets/create-asset-upload-job/
  const metadataHeader = JSON.stringify({ name_base64: Buffer.from(name).toString("base64") });

  const uploadResp = await fetch(`${CANVA_API_BASE}/asset-uploads`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/octet-stream",
      "Asset-Upload-Metadata": metadataHeader,
    },
    body: imageBytes,
  });

  const uploadRaw = await uploadResp.text();
  let uploadPayload: JsonRecord = {};
  try { uploadPayload = JSON.parse(uploadRaw) as JsonRecord; } catch { uploadPayload = { raw: uploadRaw }; }

  if (!uploadResp.ok) {
    throw new Error(`Canva asset upload failed (${uploadResp.status}): ${JSON.stringify(uploadPayload)}`);
  }

  // Step 2: poll job for completion (max 30s)
  const jobId = String((uploadPayload.job as JsonRecord)?.id || uploadPayload.id || "");
  if (!jobId) {
    throw new Error(`Canva asset upload: no job id in response: ${JSON.stringify(uploadPayload)}`);
  }

  for (let attempt = 0; attempt < 12; attempt++) {
    await new Promise((r) => setTimeout(r, 2500));
    const pollResp = await fetch(`${CANVA_API_BASE}/asset-uploads/${encodeURIComponent(jobId)}`, {
      headers: { Authorization: `Bearer ${await getAccessToken()}` },
    });
    const pollRaw = await pollResp.text();
    let pollPayload: JsonRecord = {};
    try { pollPayload = JSON.parse(pollRaw) as JsonRecord; } catch { /* ignore */ }

    const job = (pollPayload.job || pollPayload) as JsonRecord;
    const status = String(job.status || "").toLowerCase();
    if (status === "success") {
      const asset = (job.asset || {}) as JsonRecord;
      const thumbnail = (asset.thumbnail || {}) as JsonRecord;
      return {
        id: String(asset.id || jobId),
        name: String(asset.name || name),
        url: typeof asset.url === "string" ? asset.url : undefined,
        thumbnailUrl: typeof thumbnail.url === "string" ? thumbnail.url : undefined,
      };
    }
    if (status === "failed") {
      throw new Error(`Canva asset upload job failed: ${JSON.stringify(pollPayload)}`);
    }
    logger.info(`Canva asset upload job ${jobId}: status=${status || "pending"}...`);
  }

  throw new Error(`Canva asset upload job ${jobId} timed out after 30s`);
}

// ── Brand Template Autofill ──────────────────────────────────────────────

export type CanvaAutofillField =
  | { type: "text"; text: string }
  | { type: "image"; asset_id: string };

export interface CanvaAutofillRequest {
  brandTemplateId: string;
  title?: string;
  data: Record<string, CanvaAutofillField>;
}

/**
 * Create a new design from a brand template by autofilling its data fields.
 * Requires Canva Teams/Enterprise + scope `brandtemplate:content:read` +
 * `design:content:write`.
 *
 * Protocol:
 *   1. POST /v1/autofills  → returns a job
 *   2. GET  /v1/autofills/{jobId}  → poll until status=success|failed
 */
export async function autofillBrandTemplate(
  req: CanvaAutofillRequest,
): Promise<CanvaDesignSummary> {
  if (!req.brandTemplateId) throw new Error("brandTemplateId is required");

  const body: JsonRecord = {
    brand_template_id: req.brandTemplateId,
    data: req.data,
    ...(req.title ? { title: req.title } : {}),
  };

  const createResp = await canvaRequest<JsonRecord>("/autofills", {
    method: "POST",
    body: JSON.stringify(body),
  });

  const job = (createResp.job || createResp) as JsonRecord;
  const jobId = String(job.id || "");
  if (!jobId) {
    throw new Error(`Canva autofill: no job id in response: ${JSON.stringify(createResp)}`);
  }

  // Inline result (some Canva responses include the design directly on success)
  const inlineStatus = String(job.status || "").toLowerCase();
  if (inlineStatus === "success" && job.result) {
    const result = job.result as JsonRecord;
    const design = (result.design || result) as JsonRecord;
    return summarizeDesign({ design });
  }

  // Poll up to ~60s
  for (let attempt = 0; attempt < 24; attempt++) {
    await new Promise((r) => setTimeout(r, 2500));
    const pollResp = await canvaRequest<JsonRecord>(
      `/autofills/${encodeURIComponent(jobId)}`,
    );
    const pollJob = (pollResp.job || pollResp) as JsonRecord;
    const status = String(pollJob.status || "").toLowerCase();

    if (status === "success") {
      const result = (pollJob.result || {}) as JsonRecord;
      const design = (result.design || result) as JsonRecord;
      return summarizeDesign({ design });
    }
    if (status === "failed") {
      throw new Error(`Canva autofill job failed: ${JSON.stringify(pollResp)}`);
    }
    logger.info(`Canva autofill job ${jobId}: status=${status || "pending"}...`);
  }

  throw new Error(`Canva autofill job ${jobId} timed out after 60s`);
}

// ── OAuth Authorization Code helpers (one-time consent / re-consent) ─────

const DEFAULT_CANVA_SCOPES = [
  "app:read",
  "app:write",
  "design:meta:read",
  "design:content:read",
  "design:content:write",
  "asset:read",
  "asset:write",
  "brandtemplate:meta:read",
  "brandtemplate:content:read",
].join(" ");

export interface CanvaOAuthClientInfo {
  clientId: string;
  clientSecret: string;
}

export async function getCanvaOAuthClientInfo(): Promise<CanvaOAuthClientInfo> {
  if (ENV_CLIENT_ID && ENV_CLIENT_SECRET) {
    return { clientId: ENV_CLIENT_ID, clientSecret: ENV_CLIENT_SECRET };
  }
  const [clientId, clientSecret] = await Promise.all([
    readSecret(SECRET_NAME_CLIENT_ID),
    readSecret(SECRET_NAME_CLIENT_SECRET),
  ]);
  return { clientId, clientSecret };
}

export function buildCanvaAuthorizeUrl(params: {
  clientId: string;
  redirectUri: string;
  state: string;
  codeChallenge: string;
  scope?: string;
}): string {
  const scope = params.scope || process.env.CANVA_OAUTH_SCOPES || DEFAULT_CANVA_SCOPES;
  const qs = new URLSearchParams({
    response_type: "code",
    client_id: params.clientId,
    redirect_uri: params.redirectUri,
    scope,
    state: params.state,
    code_challenge: params.codeChallenge,
    code_challenge_method: "S256",
  });
  return `https://www.canva.com/api/oauth/authorize?${qs.toString()}`;
}

export async function exchangeCanvaAuthCode(params: {
  code: string;
  redirectUri: string;
  codeVerifier: string;
}): Promise<{ accessToken: string; refreshToken: string; expiresIn: number; scope?: string }> {
  const { clientId, clientSecret } = await getCanvaOAuthClientInfo();

  const credentials = Buffer.from(`${clientId}:${clientSecret}`).toString("base64");

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code: params.code,
    redirect_uri: params.redirectUri,
    code_verifier: params.codeVerifier,
  });

  const response = await fetch(`${CANVA_API_BASE}/oauth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Basic ${credentials}`,
    },
    body,
  });

  const raw = await response.text();
  let payload: JsonRecord = {};
  try {
    payload = raw ? (JSON.parse(raw) as JsonRecord) : {};
  } catch {
    payload = { raw };
  }

  if (!response.ok) {
    throw new Error(`Canva auth code exchange failed (${response.status}): ${JSON.stringify(payload)}`);
  }

  const accessToken = String(payload.access_token || "");
  const refreshToken = String(payload.refresh_token || "");
  const expiresIn = Number(payload.expires_in || 3600);
  const scope = typeof payload.scope === "string" ? payload.scope : undefined;

  if (!accessToken || !refreshToken) {
    throw new Error("Canva auth code exchange returned no access_token or refresh_token");
  }

  // Cache the access token so subsequent API calls don't immediately refresh.
  cachedToken = {
    accessToken,
    expiresAtMs: Date.now() + Math.max(60, expiresIn - 60) * 1000,
  };

  return { accessToken, refreshToken, expiresIn, scope };
}

export async function storeCanvaRefreshToken(refreshToken: string): Promise<void> {
  if (!refreshToken) throw new Error("Empty refresh token");
  await addSecretVersion(SECRET_NAME_REFRESH_TOKEN, refreshToken);
  logger.info("Canva refresh token stored in Secret Manager (re-consent)");
}
