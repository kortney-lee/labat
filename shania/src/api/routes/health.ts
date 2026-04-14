/**
 * health.ts — GET /health endpoint.
 */

import { Router, Request, Response } from "express";
import { listTemplateIds } from "../../renderer/renderHtml";
import { BRANDS } from "../../config/brand";

const router = Router();

router.get("/health", (_req: Request, res: Response): void => {
  res.json({
    status: "healthy",
    service: "wihy-shania-graphics",
    templates: listTemplateIds().length,
    gemini: true,  // Vertex AI (ADC)
    imagen: true,  // Vertex AI (ADC)
    gcs: !!process.env.GCS_BUCKET || true,
    brands: Object.keys(BRANDS),
    uptime: process.uptime(),
  });
});

router.get("/", (_req: Request, res: Response): void => {
  res.json({
    service: "wihy-shania-graphics",
    docs: "POST /generate, POST /generate-post, GET /templates, POST /generate-from-prompt",
    brands: Object.keys(BRANDS),
  });
});

export default router;
