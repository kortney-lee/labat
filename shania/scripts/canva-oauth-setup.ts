/**
 * scripts/canva-oauth-setup.ts — One-time Canva OAuth authorization flow
 *
 * Run this ONCE to obtain an initial refresh token from Canva.
 * The token is then stored in GCP Secret Manager and auto-refreshed by the service.
 *
 * Prerequisites:
 *   1. Created a Canva integration in https://www.canva.com/developers/integrations
 *   2. Set these env vars (or GCP secrets canva-client-id / canva-client-secret):
 *        CANVA_CLIENT_ID=<your client id>
 *        CANVA_CLIENT_SECRET=<your client secret>
 *   3. Added http://127.0.0.1:8765/oauth/callback as a redirect URL in your integration
 *   4. Set scopes: design:content:read design:content:write brandtemplate:meta:read
 *                  brandtemplate:content:read asset:read asset:write
 *
 * Usage:
 *   npx ts-node scripts/canva-oauth-setup.ts
 *
 * After running, the script will:
 *   - Store canva-client-id, canva-client-secret, canva-refresh-token in GCP Secret Manager
 *   - Print the brand templates available to the authenticated user
 */

import crypto from "crypto";
import http from "http";
import { URL } from "url";
import { SecretManagerServiceClient } from "@google-cloud/secret-manager";

const GCP_PROJECT = process.env.GCP_PROJECT || "wihy-ai";
const REDIRECT_URI = "http://127.0.0.1:8765/oauth/callback";
const PORT = 8765;

const SCOPES = [
  "design:content:read",
  "design:content:write",
  "brandtemplate:meta:read",
  "brandtemplate:content:read",
  "asset:read",
  "asset:write",
].join(" ");

// ── PKCE helpers ──────────────────────────────────────────────────────────────

function generateCodeVerifier(): string {
  return crypto.randomBytes(96).toString("base64url");
}

function generateCodeChallenge(verifier: string): string {
  return crypto.createHash("sha256").update(verifier).digest("base64url");
}

function generateState(): string {
  return crypto.randomBytes(32).toString("base64url");
}

// ── GCP Secret Manager ────────────────────────────────────────────────────────

async function upsertSecret(secretName: string, value: string): Promise<void> {
  const client = new SecretManagerServiceClient();

  // Try to create the secret (ok if already exists)
  try {
    await client.createSecret({
      parent: `projects/${GCP_PROJECT}`,
      secretId: secretName,
      secret: { replication: { automatic: {} } },
    });
    console.log(`  Created secret: ${secretName}`);
  } catch (err: unknown) {
    if ((err as { code?: number }).code !== 6) {
      // 6 = ALREADY_EXISTS — that's fine
      throw err;
    }
  }

  // Add a new version
  await client.addSecretVersion({
    parent: `projects/${GCP_PROJECT}/secrets/${secretName}`,
    payload: { data: Buffer.from(value, "utf8") },
  });
  console.log(`  Updated secret: ${secretName}`);
}

// ── Token Exchange ────────────────────────────────────────────────────────────

async function exchangeCodeForTokens(
  code: string,
  codeVerifier: string,
  clientId: string,
  clientSecret: string,
): Promise<{ accessToken: string; refreshToken: string }> {
  const credentials = Buffer.from(`${clientId}:${clientSecret}`).toString("base64");

  const response = await fetch("https://api.canva.com/rest/v1/oauth/token", {
    method: "POST",
    headers: {
      Authorization: `Basic ${credentials}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      code_verifier: codeVerifier,
      redirect_uri: REDIRECT_URI,
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Token exchange failed (${response.status}): ${body}`);
  }

  const data = (await response.json()) as {
    access_token: string;
    refresh_token: string;
  };
  return { accessToken: data.access_token, refreshToken: data.refresh_token };
}

// ── List Brand Templates ──────────────────────────────────────────────────────

async function listBrandTemplates(accessToken: string): Promise<void> {
  const response = await fetch("https://api.canva.com/rest/v1/brand-templates", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!response.ok) {
    console.log("  (Could not list brand templates — may need Enterprise access)");
    return;
  }

  const data = (await response.json()) as { items?: Array<{ id: string; title: string }> };
  const templates = data.items ?? [];

  if (templates.length === 0) {
    console.log("  No brand templates found. Create templates in Canva and publish them.");
  } else {
    console.log(`\n  Found ${templates.length} brand template(s):`);
    for (const t of templates) {
      console.log(`    ID: ${t.id}  |  Title: ${t.title}`);
    }
    console.log(
      "\n  Store these IDs in GCP secret 'canva-brand-templates' as JSON:",
    );
    const mapping: Record<string, string> = {};
    for (const t of templates) {
      const key = t.title.toLowerCase().replace(/[^a-z0-9]/g, "");
      mapping[key] = t.id;
    }
    console.log("  " + JSON.stringify(mapping, null, 2));
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const clientId = process.env.CANVA_CLIENT_ID;
  const clientSecret = process.env.CANVA_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    console.error(
      "Error: CANVA_CLIENT_ID and CANVA_CLIENT_SECRET env vars are required.\n" +
        "Find them at: https://www.canva.com/developers/integrations",
    );
    process.exit(1);
  }

  const codeVerifier = generateCodeVerifier();
  const codeChallenge = generateCodeChallenge(codeVerifier);
  const state = generateState();

  const authUrl =
    `https://www.canva.com/api/oauth/authorize?` +
    `code_challenge=${codeChallenge}` +
    `&code_challenge_method=S256` +
    `&scope=${encodeURIComponent(SCOPES)}` +
    `&response_type=code` +
    `&client_id=${clientId}` +
    `&state=${state}` +
    `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`;

  console.log("\n=== Canva OAuth Setup ===\n");
  console.log("Open this URL in your browser to authorize:\n");
  console.log(authUrl);
  console.log(`\nWaiting for redirect on http://127.0.0.1:${PORT}/oauth/callback ...\n`);

  // Start local server to catch the redirect
  await new Promise<void>((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      if (!req.url?.startsWith("/oauth/callback")) {
        res.writeHead(404);
        res.end();
        return;
      }

      const params = new URL(req.url, `http://127.0.0.1:${PORT}`).searchParams;
      const code = params.get("code");
      const returnedState = params.get("state");

      if (!code) {
        res.writeHead(400);
        res.end("Missing authorization code");
        server.close();
        reject(new Error("No authorization code in callback"));
        return;
      }

      if (returnedState !== state) {
        res.writeHead(400);
        res.end("State mismatch — possible CSRF attack");
        server.close();
        reject(new Error("OAuth state mismatch"));
        return;
      }

      res.writeHead(200, { "Content-Type": "text/html" });
      res.end(
        "<h2>Authorization successful!</h2><p>You can close this tab and return to the terminal.</p>",
      );
      server.close();

      try {
        console.log("Authorization code received. Exchanging for tokens...");
        const { accessToken, refreshToken } = await exchangeCodeForTokens(
          code,
          codeVerifier,
          clientId,
          clientSecret,
        );

        console.log("\nTokens received. Storing in GCP Secret Manager...");
        await upsertSecret("canva-client-id", clientId);
        await upsertSecret("canva-client-secret", clientSecret);
        await upsertSecret("canva-refresh-token", refreshToken);

        console.log("\n✅ Credentials stored in GCP Secret Manager successfully!");
        console.log("\nFetching available brand templates...");
        await listBrandTemplates(accessToken);

        console.log(
          "\n=== Setup complete ===\n" +
            "The Shania service will now use these credentials automatically.\n" +
            "The refresh token rotates on each use — GCP Secret Manager is updated automatically.\n",
        );
        resolve();
      } catch (err) {
        reject(err);
      }
    });

    server.listen(PORT, "127.0.0.1");
    server.on("error", reject);
  });
}

main().catch((err) => {
  console.error("Setup failed:", err);
  process.exit(1);
});
