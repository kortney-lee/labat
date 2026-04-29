/**
 * Shania Graphics — WIHY Gemini/Imagen generation service.
 *
 * Cloud Run: wihy-shania-graphics
 */

import express from "express";
import { ensureBucket } from "./storage/gcs";
import { logger } from "./utils/logger";

import healthRoutes from "./api/routes/health";
import generateRoutes from "./api/routes/generate";
import assetRoutes from "./api/routes/assets";
import deliveryRoutes from "./api/routes/delivery";
import researchRoutes from "./api/routes/research";
import authRoutes from "./api/routes/auth";

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

app.use(healthRoutes);
app.use(generateRoutes);
app.use(assetRoutes);
app.use(deliveryRoutes);
app.use(researchRoutes);
app.use(authRoutes);

// ── Startup ─────────────────────────────────────────────────────────────────

async function start(): Promise<void> {
  // Initialize GCS
  await ensureBucket();

  app.listen(PORT, "0.0.0.0", () => {
    logger.info(`✅ Shania Graphics running on port ${PORT}`);
  });
}

// ── Graceful shutdown ───────────────────────────────────────────────────────

async function shutdown(): Promise<void> {
  logger.info("Shutting down Shania Graphics");
  process.exit(0);
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

start().catch((err) => {
  logger.error(`Failed to start: ${err}`);
  process.exit(1);
});
