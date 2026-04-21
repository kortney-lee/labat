/**
 * geminiClient.ts — Gemini structured output for graphic content generation.
 *
 * Takes a prompt/topic and returns structured JSON matching TemplateData.
 * Uses Vertex AI with Application Default Credentials (service account on Cloud Run).
 */

import { VertexAI, SchemaType } from "@google-cloud/vertexai";
import { logger } from "../utils/logger";
import { BrandProfile } from "../config/brand";

const GCP_PROJECT = process.env.GCP_PROJECT || "wihy-ai";
const GCP_LOCATION = process.env.GCP_LOCATION || "us-central1";

const vertexAI = new VertexAI({ project: GCP_PROJECT, location: GCP_LOCATION });

/** Structured output schema for Gemini. */
const GRAPHIC_SCHEMA = {
  type: SchemaType.OBJECT,
  properties: {
    template: {
      type: SchemaType.STRING,
      description: "Template ID: editorial_signal, app_showcase, stat_pulse, wihy_signal_clean, hook_square, hook_vertical, ingredient_breakdown, quote_card, cta_card, stat_card, research_card, photo_overlay, photo_caption, ai_photo, cg_warm_card, cg_recipe_tip, cg_community, cg_fresh_pick, vowels_data_card, vowels_community, vowels_clean_card, vowels_research_tip",
    },
    headline: { type: SchemaType.STRING, description: "Bold primary text (max 8 words)" },
    subtext: { type: SchemaType.STRING, description: "Supporting text (max 15 words)" },
    cta: { type: SchemaType.STRING, description: "Call-to-action text (max 4 words)" },
    theme: {
      type: SchemaType.STRING,
      description: "Visual theme: wihy_default, dark, light, bold",
    },
    artDirection: {
      type: SchemaType.STRING,
      description: "Art direction: editorial, poster, data_lab, lifestyle",
    },

    quote: { type: SchemaType.STRING, description: "Quote text (quote_card or cg_community only)" },
    attribution: { type: SchemaType.STRING, description: "Quote attribution (quote_card or cg_community)" },
    tip: { type: SchemaType.STRING, description: "Short actionable tip text (cg_community only). Shows a tip variant on the right panel. Max 25 words." },
    tipLabel: { type: SchemaType.STRING, description: "Label above the tip, e.g. 'Quick Tip', 'Kitchen Hack', 'Pro Move' (cg_community only)" },
    photoQuery: {
      type: SchemaType.STRING,
      description: "AI image generation prompt for photo_overlay, photo_caption, or ai_photo. Describe a photorealistic scene with NO text, signs, labels, or writing visible. Focus on objects, food, people, and environments. Example: 'A warm family kitchen with a parent and child preparing a colorful salad together, natural light, editorial photography, no text no signs'. Required when template is photo_overlay, photo_caption, or ai_photo.",
    },
    statNumber: {
      type: SchemaType.STRING,
      description: "Big stat/number to display prominently (stat_card only). Include the unit, e.g. '73.6%', '2.3x', '48M', '$4,200'",
    },
    statLabel: {
      type: SchemaType.STRING,
      description: "What the stat represents (stat_card only). Max 12 words, e.g. 'of American adults are overweight or obese'",
    },
    dataPoints: {
      type: SchemaType.ARRAY,
      items: { type: SchemaType.STRING },
      description: "2-3 specific research findings or data points for stat_card and research_card. Each ~15-25 words. Use real numbers and specifics from the knowledge base.",
    },
    source: {
      type: SchemaType.STRING,
      description: "Citation or source for the data (stat_card, research_card). E.g. 'CDC National Health Statistics, 2024' or 'Published in The Lancet, 2023'",
    },
  },
  required: ["template", "headline"],
};

export interface GeminiGraphicResult {
  template: string;
  headline: string;
  subtext?: string;
  cta?: string;
  theme?: string;
  artDirection?: string;

  quote?: string;
  attribution?: string;
  tip?: string;
  tipLabel?: string;
  photoQuery?: string;
  statNumber?: string;
  statLabel?: string;
  dataPoints?: string[];
  source?: string;
}

/**
 * Generate structured graphic content from a prompt.
 */
export async function generateGraphicContent(
  prompt: string,
  templateHint?: string,
  brand?: BrandProfile,
  ragFacts?: string | null,
): Promise<GeminiGraphicResult> {
  const model = vertexAI.getGenerativeModel({
    model: "gemini-2.5-flash",
    generationConfig: {
      responseMimeType: "application/json",
      responseSchema: GRAPHIC_SCHEMA,
      temperature: 0.8,
    },
  });

  const systemPrompt = buildSystemPrompt(templateHint, brand, ragFacts);
  const result = await model.generateContent({
    contents: [{ role: "user", parts: [{ text: systemPrompt + "\n\n" + prompt }] }],
  });
  const text = result.response?.candidates?.[0]?.content?.parts?.[0]?.text || "";

  const parsed: GeminiGraphicResult = JSON.parse(text);
  logger.info(`Gemini generated content for template: ${parsed.template}`);
  return parsed;
}

function buildSystemPrompt(templateHint?: string, brand?: BrandProfile, ragFacts?: string | null): string {
  const brandName = brand?.name || "WIHY";
  const brandVoice = brand?.voice || "Bold, science-backed, slightly provocative";
  const brandFocus = brand?.contentFocus || "";

  const isCG = brand?.id === "communitygroceries";
  const isVowelsFamily = brand?.id === "vowels" || brand?.parentBrand === "vowels";

  let prompt = `You are a creative director for ${brandName}.

BRAND VOICE:
${brandVoice}

CONTENT FOCUS:
${brandFocus}

Generate social media graphic content that is:
- DATA-DRIVEN with specific numbers, percentages, and research findings
- Aligned with ${brandName}'s specific brand identity (NOT generic health content)
- Uses real statistics and evidence from the knowledge base
- Never misleading or making medical claims
`;

  if (ragFacts) {
    prompt += `
KNOWLEDGE BASE (use specific data from this for your content — extract real numbers, stats, and findings):
${ragFacts}

CRITICAL: Use actual data points from this knowledge base. Do NOT generate vague headlines. Pull specific statistics, percentages, findings, and cite real sources.
`;
  }

  if (isCG) {
    prompt += `
COMMUNITY GROCERIES TEMPLATES (use ONLY these for CG):
- cg_warm_card: Clean card with organic blob shapes, tag label — PREFERRED for most CG posts
- cg_recipe_tip: Split layout with colored side panel + content area — great for tips, recipes, advice
- cg_community: Split panel with community feel — adapts based on context:
  * Provide quote + attribution for community testimonial/quote variant
  * Provide tip + tipLabel for quick tip / kitchen hack variant
  * Provide none of the above for clean branded default (stats/percentages should use stat_card or photo_overlay instead)
- cg_fresh_pick: Clean card with leaf decorations — use for product picks, seasonal content, featured items

DO NOT use hook_square, hook_vertical, quote_card, cta_card, stat_card, research_card, or ingredient_breakdown — those are WIHY-style templates.
DO NOT use vowels_data_card, vowels_community, vowels_clean_card, or vowels_research_tip — those are Vowels templates.
CG templates have LIGHT backgrounds (cream, ivory, soft green) with WARM colors. They feel personal and inviting, not dark and techy.

CRITICAL FOR CG: Always provide a strong meal-focused photoQuery for EVERY post, even when using a non-photo template.
Photo direction should show plated meals, prep containers, family dinner scenes, grocery ingredients, or cooking-in-progress.
Avoid sterile studio shots; favor warm, realistic kitchen/editorial food photography.

For ai_photo (use sparingly, ~20% of posts) — standalone AI-generated image, NO template:
Show diverse families, real kitchens, farmers markets, packed lunch boxes, dinner tables, parent-child cooking moments. Warm and inviting. NEVER clinical or sterile.
Provide a photoQuery. Example: "A warm family kitchen with a parent and child preparing a colorful salad together, natural light, editorial photography"
`;
  } else {
    prompt += `
WIHY DATA-DRIVEN TEMPLATES (prefer stat_card and research_card for data-rich topics):
- wihy_signal_clean: Clean premium WIHY layout with strong headline + metric + insight cards. Use for most WIHY feed posts.
- editorial_signal: Editorial WIHY layout with split media panel and concise bullet findings.
- app_showcase: Product-forward WIHY layout with phone mockup and app narrative.
- stat_pulse: Data-forward WIHY layout for metric + findings content.
- stat_card: BIG stat number (73.6%, 2.3x, 48M) with supporting data points — USE when the topic has a striking statistic. Provide statNumber, statLabel, dataPoints (2-3 specific findings), and source.
- research_card: Research headline + 3 numbered findings with sources — USE for multi-finding topics. Provide headline, dataPoints (3 specific findings with numbers), and source.
- hook_square: Bold statement post (1080x1080) — use for provocative hooks WITHOUT heavy data
- hook_vertical: Vertical story hook (1080x1920)
- quote_card: Inspirational/educational quote
- cta_card: Strong call-to-action post
- ingredient_breakdown: Score-based ingredient analysis (only when listing scored items)
- photo_overlay: Full-bleed AI photo background with branded overlay (gradient, headline, logo) — USE for visually stunning food, ingredients, or lifestyle photos where you want branded text on top. Provide a photoQuery AND headline/subtext.
- photo_caption: AI photo top half + branded text bottom half — USE for lifestyle topics, family moments, cooking scenes. Provide a photoQuery AND headline/subtext.
- ai_photo: Standalone AI-generated photo with NO template overlay at all. Use sparingly for purely visual content. Provide a photoQuery only.

TEMPLATE SELECTION GUIDE:
- General WIHY feed post with headline + supporting copy? → wihy_signal_clean (DEFAULT)
- Need product/app storytelling? → app_showcase
- Need concise editorial split with media? → editorial_signal
- Metric + findings with strong number? → stat_pulse or stat_card
- Topic mentions a specific number/percentage/stat? → stat_card (PREFERRED)
- Topic has multiple research findings? → research_card
- Simple provocative hook? → hook_square
- Visual food/ingredient/lifestyle topic? → photo_overlay (PRIMARY default unless stat-heavy)
- Lifestyle/family topic with photo + caption? → photo_caption
- Purely visual, no text needed? → ai_photo (standalone, rare)
- Target distribution: ~45% photo templates, ~35% data templates (stat/research), ~20% hook templates

DO NOT use cg_warm_card, cg_recipe_tip, cg_community, or cg_fresh_pick — those are Community Groceries templates.
DO NOT use vowels_data_card, vowels_community, vowels_clean_card, or vowels_research_tip — those are Vowels templates.

Always provide a detailed photoQuery for Imagen 4.0, even when choosing non-photo templates (used as fallback/variation input).
CRITICAL: photoQuery must NEVER describe text, signs, labels, writing, or price tags — Imagen generates garbled text artifacts. Describe ONLY visual scenes, objects, food, people, environments.
For WIHY photos: show real food close-ups, ingredient layouts, grocery aisles, food science, sugar in foods, processed ingredients.
Example photoQuery: "Close-up of everyday foods with sugar cubes spilling out showing hidden sugar content, dramatic lighting, editorial food photography, no text no signs no labels"
`;
  }

  if (isVowelsFamily) {
    prompt += `
VOWELS TEMPLATES (use ONLY these for Vowels and Vowels sub-brands like Snacking Well, Children's Nutrition, Parenting with Christ):
- vowels_data_card: Clean card with top accent bar and corner mark — PREFERRED for data-backed posts, research insights
- vowels_community: Centered layout with grid dots, logo at top — use for quotes, community messages, data stories
- vowels_clean_card: Minimal card with accent bar and vertical line — use for simple facts, clean messages
- vowels_research_tip: Split layout with flat accent side panel + content area — great for research tips, data breakdowns

DO NOT use WIHY templates (hook_square, stat_card, etc.) — those have dark backgrounds.
DO NOT use CG templates (cg_warm_card, etc.) — those are Community Groceries.
Vowels templates have LIGHT backgrounds (ice white, lavender, soft blue) with BLUE/PURPLE accents. They feel academic, clean, and data-driven. No gradients.
`;
  }

  prompt += `
CONTENT RULES:
- Keep headlines under 8 words
- Keep subtext under 15 words
- CTAs under 4 words
- dataPoints: each finding should be 15-25 words with SPECIFIC numbers/data
- statNumber: include the unit (%, x, M, $)
- source: cite real publications, agencies, or databases (CDC, WHO, The Lancet, NHANES, etc.)
`;

  if (templateHint) {
    prompt += `\n\nUse the "${templateHint}" template specifically.`;
  }

  return prompt;
}
