/**
 * health.ts — GET /health endpoint.
 */

import { Router, Request, Response } from "express";

const router = Router();

router.get("/health", (_req: Request, res: Response): void => {
  res.json({ status: "healthy" });
});

router.get("/", (_req: Request, res: Response): void => {
  res.json({ service: "wihy-shania-graphics" });
});

export default router;
