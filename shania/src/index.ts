/**
 * Shania Graphics — WIHY template-driven graphic generation service.
 *
 * Flow: ALEX/LABAT → Gemini → Canva design → Canva export → Cloud Storage
 *
 * Cloud Run: wihy-shania-graphics
 *
 * 100% powered by Canva API (no more custom HTML templates)
 */

import express from "express";
import { closeBrowser } from "./renderer/renderImage";
import { ensureBucket } from "./storage/gcs";
import { logger } from "./utils/logger";
import { initCanvaClient } from "./services/canvaService";
import { loadCanvaCredentials, updateRefreshToken } from "./utils/canvaSecrets";

import healthRoutes from "./api/routes/health";
import generateRoutes from "./api/routes/generate";
import templateRoutes from "./api/routes/templates";
import assetRoutes from "./api/routes/assets";
import deliveryRoutes from "./api/routes/delivery";
import researchRoutes from "./api/routes/research";
import nurtureRoutes from "./api/routes/nurture";

const app = express();
const PORT = parseInt(process.env.PORT || "8080", 10);

// ── Middleware ───────────────────────────────────────────────────────────────

app.use(express.json({ limit: "10mb" }));

// CORS
app.use((_req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Admin-Token");
  if (_req.method === "OPTIONS") {
    res.sendStatus(204);
    return;
  }
  next();
});

// ── Routes ──────────────────────────────────────────────────────────────────

app.get("/oauth/callback", (req, res) => {
  const hasCode = typeof req.query.code === "string" && req.query.code.length > 0;
  const hasError = typeof req.query.error === "string" && req.query.error.length > 0;

  if (hasError) {
    res.status(400).send("Canva OAuth callback received an error. Check Shania logs for details.");
    return;
  }

  if (hasCode) {
    res
      .status(200)
      .send(
        "Canva authorization received by Shania. You can close this window and complete token exchange from your setup flow.",
      );
    return;
  }

  res.status(400).send("Missing OAuth code in callback request.");
});

app.use(healthRoutes);
app.use(generateRoutes);
app.use(templateRoutes);
app.use(assetRoutes);
app.use(deliveryRoutes);
app.use(researchRoutes);
app.use(nurtureRoutes);

// ── Startup ─────────────────────────────────────────────────────────────────

async function start(): Promise<void> {
  // Initialize GCS
  await ensureBucket();

  // Initialize Canva integration
  try {
    logger.info("🚀 Initializing Canva integration...");
    const creds = await loadCanvaCredentials();
    initCanvaClient({
      clientId: creds.clientId,
      clientSecret: creds.clientSecret,
      refreshToken: creds.refreshToken,
      onTokenRefresh: updateRefreshToken,
    });
    logger.info("✅ Canva integration initialized successfully");
  } catch (error) {
    logger.error(`⚠️  Canva initialization warning (non-fatal): ${error}`);
    logger.info("   Canva will not be available until credentials are configured");
    logger.info("   Run shania/scripts/canva-oauth-setup.ts for first-time OAuth setup");
  }

  app.listen(PORT, "0.0.0.0", () => {
    logger.info(`✅ Shania Graphics running on port ${PORT}`);
  });
}

// ── Graceful shutdown ───────────────────────────────────────────────────────

async function shutdown(): Promise<void> {
  logger.info("Shutting down Shania Graphics");
  await closeBrowser();
  process.exit(0);
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

start().catch((err) => {
  logger.error(`Failed to start: ${err}`);
  process.exit(1);
});
