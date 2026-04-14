/**
 * templates.ts — GET /templates and POST /templates endpoints.
 */

import { Router, Request, Response } from "express";
import { listTemplateIds } from "../../renderer/renderHtml";
import { FORMATS } from "../../config/formats";
import { TemplateMeta } from "../../types";

const router = Router();

/** Static metadata for each template. */
const TEMPLATE_META: Record<string, Omit<TemplateMeta, "id">> = {
  hook_square: {
    name: "Hook Square",
    description: "Bold statement post for feed (1:1). Grabs attention with a punchy headline.",
    defaultFormat: "feed_square",
    requiredFields: ["headline"],
    optionalFields: ["subtext", "cta", "badge", "productName", "theme", "artDirection", "showLogo"],
  },
  hook_vertical: {
    name: "Hook Vertical",
    description: "Vertical story/reel hook (9:16). Full-screen attention grabber.",
    defaultFormat: "story_vertical",
    requiredFields: ["headline"],
    optionalFields: ["subtext", "cta", "badge", "productName", "theme", "artDirection", "showLogo"],
  },
  ingredient_breakdown: {
    name: "Ingredient Breakdown",
    description: "Score-based ingredient analysis with color-coded ratings.",
    defaultFormat: "feed_square",
    requiredFields: ["headline", "items"],
    optionalFields: ["subtext", "cta", "productName", "showLogo"],
  },
  comparison_split: {
    name: "Comparison Split",
    description: "Side-by-side comparison (bad vs good / avoid vs choose).",
    defaultFormat: "feed_square",
    requiredFields: ["headline", "leftItems", "rightItems"],
    optionalFields: ["subtext", "cta", "leftLabel", "rightLabel", "showLogo"],
  },
  quote_card: {
    name: "Quote Card",
    description: "Inspirational or educational quote with elegant typography.",
    defaultFormat: "feed_square",
    requiredFields: ["headline"],
    optionalFields: ["quote", "attribution", "subtext", "showLogo"],
  },
  cta_card: {
    name: "CTA Card",
    description: "Strong call-to-action post with bold branding.",
    defaultFormat: "feed_square",
    requiredFields: ["headline", "cta"],
    optionalFields: ["subtext", "badge", "productName", "showLogo"],
  },
};

/**
 * GET /templates
 * List all available templates with metadata.
 */
router.get("/templates", (_req: Request, res: Response): void => {
  const ids = listTemplateIds();
  const templates: TemplateMeta[] = ids.map((id) => {
    const meta = TEMPLATE_META[id];
    return {
      id,
      name: meta?.name || id,
      description: meta?.description || "",
      defaultFormat: meta?.defaultFormat || "feed_square",
      requiredFields: meta?.requiredFields || ["headline"],
      optionalFields: meta?.optionalFields || [],
    };
  });

  res.json({
    templates,
    formats: Object.entries(FORMATS).map(([key, spec]) => ({
      id: key,
      ...spec,
    })),
  });
});

/**
 * GET /templates/:id
 * Get metadata for a single template.
 */
router.get("/templates/:id", (req: Request<{id: string}>, res: Response): void => {
  const id = req.params.id;
  const ids = listTemplateIds();

  if (!ids.includes(id)) {
    res.status(404).json({ error: `Template not found: ${id}`, available: ids });
    return;
  }

  const meta = TEMPLATE_META[id];
  res.json({
    id,
    name: meta?.name || id,
    description: meta?.description || "",
    defaultFormat: meta?.defaultFormat || "feed_square",
    requiredFields: meta?.requiredFields || ["headline"],
    optionalFields: meta?.optionalFields || [],
    formats: Object.entries(FORMATS).map(([key, spec]) => ({ id: key, ...spec })),
  });
});

export default router;
