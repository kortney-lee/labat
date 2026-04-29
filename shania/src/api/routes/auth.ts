/**
 * auth.ts — Canva OAuth re-consent flow.
 *
 *   GET  /oauth/start      Admin-only by default. Optional public start mode
 *                          via CANVA_OAUTH_ALLOW_PUBLIC_START=true.
 *   GET  /oauth/callback   Canva redirects here with ?code&state. Stores
 *                           refresh_token in Secret Manager.
 *
 * State is stateless: the `state` param sent to Canva is a signed token
 * (payload.HMAC) containing codeVerifier, redirectUri, and expiry. This
 * works across multiple Cloud Run instances with no shared memory needed.
 *
 * The redirect URI registered with Canva must match exactly. Set CANVA_REDIRECT_URI
 * in the Cloud Run env to override; otherwise the request host is used.
 */

import { Router, Request, Response } from "express";
import { createHash, createHmac, randomBytes, timingSafeEqual } from "crypto";
import {
  buildCanvaAuthorizeUrl,
  exchangeCanvaAuthCode,
  getCanvaOAuthClientInfo,
  storeCanvaRefreshToken,
} from "../../services/canvaApi";
import { logger } from "../../utils/logger";

const router = Router();

const ADMIN_TOKEN = (process.env.INTERNAL_ADMIN_TOKEN || "").trim();
const CANVA_OAUTH_ALLOW_PUBLIC_START =
  (process.env.CANVA_OAUTH_ALLOW_PUBLIC_START || "").trim().toLowerCase() === "true";

const STATE_TTL_MS = 10 * 60 * 1000; // 10 minutes
const CALLBACK_RESULT_TTL_MS = 15 * 60 * 1000; // 15 minutes

// Use the admin token as HMAC key — it is already a secret in Secret Manager.
// Falls back to a random per-process key (works for single-instance dev).
const HMAC_KEY = ADMIN_TOKEN || randomBytes(32).toString("hex");

interface StatePayload {
  nonce: string;
  codeVerifier: string;
  redirectUri: string;
  exp: number; // Unix ms
}

interface CompletedCallbackResult {
  ok: boolean;
  html: string;
  errorMessage?: string;
  completedAtMs: number;
}

const inFlightByCode = new Map<string, Promise<CompletedCallbackResult>>();
const completedByCode = new Map<string, CompletedCallbackResult>();

function pruneCompletedResults(): void {
  const cutoff = Date.now() - CALLBACK_RESULT_TTL_MS;
  for (const [code, result] of completedByCode) {
    if (result.completedAtMs < cutoff) {
      completedByCode.delete(code);
    }
  }
}

function codeFingerprint(code: string): string {
  return createHash("sha256").update(code).digest("hex").slice(0, 12);
}

function buildSuccessHtml(scope?: string, expiresIn?: number, duplicate = false): string {
  return [
    "<html><body style='font-family:sans-serif;max-width:600px;margin:40px auto'>",
    "<h2>Canva re-consent complete</h2>",
    duplicate
      ? "<p>This callback was already processed successfully. You can close this tab.</p>"
      : "<p>Refresh token stored in Secret Manager. You can close this tab.</p>",
    `<p><b>Scope:</b> ${scope || "(default)"}</p>`,
    `<p><b>Access token expires in:</b> ${typeof expiresIn === "number" ? expiresIn : "unknown"}s</p>`,
    "</body></html>",
  ].join("");
}

function signStateToken(payload: StatePayload): string {
  const data = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const sig = createHmac("sha256", HMAC_KEY).update(data).digest("base64url");
  return `${data}.${sig}`;
}

function verifyStateToken(token: string): StatePayload | null {
  const dot = token.lastIndexOf(".");
  if (dot < 1) return null;
  const data = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  const expected = createHmac("sha256", HMAC_KEY).update(data).digest("base64url");
  // Constant-time comparison to prevent timing attacks.
  const sigBuf = Buffer.from(sig);
  const expBuf = Buffer.from(expected);
  if (sigBuf.length !== expBuf.length || !timingSafeEqual(sigBuf, expBuf)) return null;
  try {
    const payload = JSON.parse(Buffer.from(data, "base64url").toString("utf8")) as StatePayload;
    if (payload.exp < Date.now()) return null;
    return payload;
  } catch {
    return null;
  }
}

function isAdminAuthorized(req: Request): boolean {
  if (!ADMIN_TOKEN) return false;
  const header = req.headers["x-admin-token"];
  if (typeof header === "string" && header === ADMIN_TOKEN) return true;
  // Also allow ?token= query param so admins can paste a single URL into a browser.
  const queryToken = typeof req.query.token === "string" ? req.query.token : "";
  return queryToken === ADMIN_TOKEN;
}

function resolveRedirectUri(req: Request): string {
  const override = (process.env.CANVA_REDIRECT_URI || "").trim();
  if (override) return override;
  const host = req.get("host") || "";
  // Cloud Run terminates TLS, so trust forwarded proto if present.
  const proto =
    (req.headers["x-forwarded-proto"] as string | undefined)?.split(",")[0]?.trim() ||
    req.protocol ||
    "https";
  return `${proto}://${host}/oauth/callback`;
}

router.get("/oauth/start", async (req: Request, res: Response): Promise<void> => {
  if (!CANVA_OAUTH_ALLOW_PUBLIC_START && !isAdminAuthorized(req)) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  try {
    const { clientId } = await getCanvaOAuthClientInfo();
    const redirectUri = resolveRedirectUri(req);
    const codeVerifier = randomBytes(96).toString("base64url");
    const codeChallenge = createHash("sha256").update(codeVerifier).digest("base64url");
    const nonce = randomBytes(16).toString("hex");

    const stateToken = signStateToken({
      nonce,
      codeVerifier,
      redirectUri,
      exp: Date.now() + STATE_TTL_MS,
    });

    const authorizeUrl = buildCanvaAuthorizeUrl({
      clientId,
      redirectUri,
      state: stateToken,
      codeChallenge,
    });

    if (req.query.redirect === "1" || req.query.redirect === "true") {
      res.redirect(302, authorizeUrl);
      return;
    }

    res.json({
      authorizeUrl,
      redirectUri,
      ttlSeconds: STATE_TTL_MS / 1000,
      instructions:
        "Open authorizeUrl in a browser, sign into the Canva account, and click Allow. " +
        "Canva will redirect to redirectUri (this service) which finishes the flow.",
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    logger.error(`/oauth/start failed: ${msg}`);
    res.status(500).json({ error: msg });
  }
});

router.get("/oauth/callback", async (req: Request, res: Response): Promise<void> => {
  const code = typeof req.query.code === "string" ? req.query.code : "";
  const stateToken = typeof req.query.state === "string" ? req.query.state : "";
  const errorParam = typeof req.query.error === "string" ? req.query.error : "";

  if (errorParam) {
    res.status(400).send(`Canva returned error: ${errorParam}`);
    return;
  }
  if (!code || !stateToken) {
    res.status(400).send("Missing code or state");
    return;
  }

  const payload = verifyStateToken(stateToken);
  if (!payload) {
    res.status(400).send("Invalid or expired state. Restart the flow at /oauth/start.");
    return;
  }

  pruneCompletedResults();

  const existingDone = completedByCode.get(code);
  if (existingDone) {
    if (existingDone.ok) {
      res.status(200).send(existingDone.html);
      return;
    }
    res.status(500).send(`Canva auth failed: ${existingDone.errorMessage || "previous attempt failed"}`);
    return;
  }

  let inFlight = inFlightByCode.get(code);
  if (!inFlight) {
    inFlight = (async (): Promise<CompletedCallbackResult> => {
      try {
        const tokens = await exchangeCanvaAuthCode({
          code,
          redirectUri: payload.redirectUri,
          codeVerifier: payload.codeVerifier,
        });
        await storeCanvaRefreshToken(tokens.refreshToken);

        const result: CompletedCallbackResult = {
          ok: true,
          html: buildSuccessHtml(tokens.scope, tokens.expiresIn),
          completedAtMs: Date.now(),
        };
        completedByCode.set(code, result);
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        const stack = err instanceof Error ? err.stack : undefined;
        logger.error("/oauth/callback failed", {
          message: msg,
          stack,
          codeFingerprint: codeFingerprint(code),
          statePrefix: stateToken.slice(0, 24),
          redirectUri: payload.redirectUri,
        });
        const result: CompletedCallbackResult = {
          ok: false,
          html: "",
          errorMessage: msg,
          completedAtMs: Date.now(),
        };
        completedByCode.set(code, result);
        return result;
      } finally {
        inFlightByCode.delete(code);
      }
    })();
    inFlightByCode.set(code, inFlight);
  }

  const result = await inFlight;
  if (result.ok) {
    res.status(200).send(result.html);
    return;
  }

  res.status(500).send(`Canva auth failed: ${result.errorMessage || "unknown error"}`);
});

export default router;
