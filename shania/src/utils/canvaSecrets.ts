/**
 * utils/canvaSecrets.ts — Load and persist Canva OAuth credentials
 *
 * GCP secrets used:
 *   canva-client-id      -> Canva integration Client ID (static, never changes)
 *   canva-client-secret  -> Canva integration Client Secret (static)
 *   canva-refresh-token  -> OAuth refresh token (rotates on each use — updated automatically)
 *   canva-brand-templates -> JSON mapping brandId -> Canva brand template ID
 *
 * In development, fall back to environment variables:
 *   CANVA_CLIENT_ID, CANVA_CLIENT_SECRET, CANVA_REFRESH_TOKEN
 */

import { SecretManagerServiceClient } from "@google-cloud/secret-manager";
import { logger } from "./logger";

const GCP_PROJECT = process.env.GCP_PROJECT || "wihy-ai";

const SECRET_NAMES = {
  clientId: "canva-client-id",
  clientSecret: "canva-client-secret",
  refreshToken: "canva-refresh-token",
  brandTemplates: "canva-brand-templates",
} as const;

export interface CanvaCredentials {
  clientId: string;
  clientSecret: string;
  refreshToken: string;
  brandTemplates: Record<string, string>;
}

let secretClient: SecretManagerServiceClient | null = null;

function getSecretClient(): SecretManagerServiceClient {
  if (!secretClient) {
    secretClient = new SecretManagerServiceClient();
  }
  return secretClient;
}

async function readSecret(secretName: string): Promise<string | null> {
  try {
    const client = getSecretClient();
    const name = client.secretVersionPath(GCP_PROJECT, secretName, "latest");
    const [version] = await client.accessSecretVersion({ name });
    const payload = version.payload?.data?.toString()?.trim();
    return payload || null;
  } catch {
    return null;
  }
}

/**
 * Create a new version of a GCP secret (used to persist the rotated refresh token).
 * The old version is NOT destroyed — GCP retains history automatically.
 */
export async function updateRefreshToken(newToken: string): Promise<void> {
  try {
    const client = getSecretClient();
    const secretPath = client.secretPath(GCP_PROJECT, SECRET_NAMES.refreshToken);
    await client.addSecretVersion({
      parent: secretPath,
      payload: { data: Buffer.from(newToken, "utf8") },
    });
    logger.info("Canva refresh token updated in GCP Secret Manager");
  } catch (err) {
    logger.error(`Failed to update Canva refresh token in GCP Secret Manager: ${err}`);
    throw err;
  }
}

/**
 * Load all Canva OAuth credentials.
 * Tries GCP Secret Manager first; falls back to environment variables in dev.
 */
export async function loadCanvaCredentials(): Promise<CanvaCredentials> {
  // Try GCP Secret Manager
  const [gcpClientId, gcpClientSecret, gcpRefreshToken, gcpTemplates] = await Promise.all([
    readSecret(SECRET_NAMES.clientId),
    readSecret(SECRET_NAMES.clientSecret),
    readSecret(SECRET_NAMES.refreshToken),
    readSecret(SECRET_NAMES.brandTemplates),
  ]);

  const clientId = gcpClientId || process.env.CANVA_CLIENT_ID || "";
  const clientSecret = gcpClientSecret || process.env.CANVA_CLIENT_SECRET || "";
  const refreshToken = gcpRefreshToken || process.env.CANVA_REFRESH_TOKEN || "";

  if (!clientId || !clientSecret || !refreshToken) {
    throw new Error(
      "Canva OAuth credentials not found. " +
        "Create GCP secrets: canva-client-id, canva-client-secret, canva-refresh-token. " +
        "Run shania/scripts/canva-oauth-setup.ts to obtain the initial refresh token.",
    );
  }

  // Brand template mappings
  let brandTemplates: Record<string, string> = {};
  if (gcpTemplates) {
    try {
      brandTemplates = JSON.parse(gcpTemplates);
      logger.info(`Loaded ${Object.keys(brandTemplates).length} Canva brand template IDs from GCP`);
    } catch {
      logger.warn("Could not parse canva-brand-templates secret as JSON");
    }
  }

  // Override with env vars if present
  for (const [key, envVar] of [
    ["wihy", "CANVA_TEMPLATE_WIHY"],
    ["communitygroceries", "CANVA_TEMPLATE_CG"],
    ["vowels", "CANVA_TEMPLATE_VOWELS"],
    ["snackingwell", "CANVA_TEMPLATE_SNACKINGWELL"],
    ["childrennutrition", "CANVA_TEMPLATE_CHILDRENNUTRITION"],
    ["parentingwithchrist", "CANVA_TEMPLATE_PARENTINGWITHCHRIST"],
    ["otakulounge", "CANVA_TEMPLATE_OTAKULOUNGE"],
  ] as const) {
    const val = process.env[envVar];
    if (val) brandTemplates[key] = val;
  }

  logger.info("Canva OAuth credentials loaded successfully");
  return { clientId, clientSecret, refreshToken, brandTemplates };
}
