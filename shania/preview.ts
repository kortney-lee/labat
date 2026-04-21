/**
 * preview.ts — Render all Shania templates locally with sample data.
 * Generates HTML files + PNG screenshots in shania/preview/
 *
 * Usage:  cd shania && npx ts-node preview.ts
 */

import fs from "fs";
import path from "path";
import { renderTemplate, listTemplateIds } from "./src/renderer/renderHtml";
import { screenshotHtml, closeBrowser } from "./src/renderer/renderImage";
import { TemplateData } from "./src/types";
import { FormatKey } from "./src/config/formats";
import { BRANDS, BrandId } from "./src/config/brand";

const PREVIEW_DIR = path.join(__dirname, "preview");

// ── Brand mapping per template ──────────────────────────────────────────────

function getBrandForTemplate(templateId: string): string | undefined {
  if (templateId.startsWith("cg_")) return "communitygroceries";
  if (templateId.startsWith("vowels_")) return "vowels";
  return undefined; // default WIHY brand
}

// ── Sample data per template ────────────────────────────────────────────────

const SAMPLE_DATA: Record<string, TemplateData> = {
  stat_card: {
    headline: "Eat 6 Small Meals a Day? That's Marketing.",
    statNumber: "0",
    statLabel: "peer-reviewed studies support meal frequency for weight loss",
    dataPoints: [
      "The '6 small meals' myth was popularized by supplement companies selling protein bars",
      "48M+ research records show no metabolic advantage to eating more frequently",
      "Your metabolism does not 'slow down' if you skip a meal — that's been debunked since 2014",
    ],
    source: "PubMed / PMC Meta-Analysis, 48M+ Records",
    cta: "See the Research",
  },

  hook_square: {
    headline: "What If Everything You Were Told About Nutrition Was Wrong?",
    subtext: "The food industry spends $14 billion a year telling you what to eat. We spent 10 years researching what they don't want you to know.",
    cta: "Get the Book",
    productName: "VOWELS",
  },

  research_card: {
    headline: "Facts They Don't Put on the Label",
    dataPoints: [
      "The FDA does not test supplements before sale — 80,000+ products have zero pre-market review",
      "'Natural flavors' is a legal term that can include up to 50+ chemical compounds",
      "Processed meat is classified as a Group 1 carcinogen by IARC — same category as tobacco",
      "The word 'healthy' on food packaging has no regulated definition in the United States",
    ],
    source: "FDA / IARC / PubMed, 48M+ Records",
    cta: "Read the Data",
  },

  quote_card: {
    headline: "Straight From the Research",
    quote: "There is no FDA-approved vitamin. There is no expiration date on food. There is no scientific basis for detox cleanses. Everything you were told — check it.",
    attribution: "What Is Healthy? — The Book",
    subtext: "48 million research records. Zero AI. Zero sponsors. Just evidence.",
  },

  ingredient_breakdown: {
    headline: "What's Really in Your Cereal?",
    subtext: "A closer look at a popular kids' breakfast",
    items: [
      { name: "Whole Grain Oats", score: 92, verdict: "Excellent fiber source" },
      { name: "Sugar", score: 35, verdict: "Second ingredient — 12g per serving" },
      { name: "Trisodium Phosphate", score: 18, verdict: "Industrial cleaner also used as food additive" },
      { name: "BHT (Preservative)", score: 22, verdict: "Banned in several countries" },
      { name: "Natural Flavors", score: 45, verdict: "Vague — could contain 50+ chemicals" },
    ],
    cta: "Scan Your Food",
  },

  photo_overlay: {
    headline: "Farm to Table Isn't Just a Trend",
    subtext: "It's how your grandparents ate every single day.",
    photoUrl: "https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=1080&h=1080&fit=crop",
    cta: "Learn Why It Matters",
  },

  photo_caption: {
    headline: "This Is What 200 Calories Looks Like",
    subtext: "Broccoli vs. candy — same calories, completely different outcomes for your body.",
    photoUrl: "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=1080&h=1080&fit=crop",
    cta: "See the Full Breakdown",
  },

  comparison_split: {
    headline: "Reading Labels Changes Everything",
    subtext: "Same shelf, different story",
    leftLabel: "Avoid",
    rightLabel: "Choose",
    leftItems: [
      "High fructose corn syrup",
      "Partially hydrogenated oils",
      "Artificial colors (Red 40, Yellow 5)",
      "Sodium benzoate",
    ],
    rightItems: [
      "Whole grain flour",
      "Extra virgin olive oil",
      "Turmeric and beet for color",
      "Sea salt",
    ],
    cta: "Learn How to Read Labels",
  },

  cta_card: {
    headline: "Stop Guessing. Start Knowing.",
    subtext: "Scan any product. Get the truth in seconds. No ads, no sponsorships — just science.",
    cta: "Download WIHY Free",
    productName: "WIHY",
  },

  hook_vertical: {
    headline: "Your Grocery Store Has 40,000 Products. Only 12% Are Actually Healthy.",
    subtext: "We analyzed every single one so you don't have to.",
    cta: "See the Data",
    productName: "WIHY",
  },

  // cg_community: quote variant (default — has quote + attribution)
  cg_community: {
    headline: "Dinner in 30 Minutes. For Real.",
    subtext: "Ground beef skillet — one pan, five ingredients, zero stress. Your kids will actually eat it.",
    quote: "I used to spend 45 minutes figuring out what to make. Now I open the app, tap a meal, and the shopping list builds itself.",
    attribution: "Mom of 3, Community Member",
    photoUrl: "https://storage.googleapis.com/wihy-meal-images/meals/30-minute-ground-beef-skillet-1f35a8fafc52.png",
    cta: "Get This Recipe",
  },

  // cg_community: tip variant
  cg_community_tip: {
    headline: "Stop Throwing Away Groceries",
    subtext: "The average family wastes $1,500 in food per year. Plan meals before you shop — not after.",
    tip: "Open Community Groceries on Sunday. Pick 5 meals. The app builds your list and checks what's on sale near you.",
    tipLabel: "Save Time & Money",
    photoUrl: "https://storage.googleapis.com/wihy-meal-images/meals/30-minute-shrimp-tacos-201e39c367de.png",
    cta: "Try It Free",
  },

  // cg_community: default branded variant (no quote/tip/stat)
  cg_community_default: {
    headline: "You Don't Need More Recipes. You Need a Plan.",
    subtext: "Community Groceries turns trending meals into a weekly plan with a shopping list that actually makes sense.",
    photoUrl: "https://storage.googleapis.com/wihy-meal-images/meals/5-ingredient-chili-4e1a09110e32.png",
    cta: "Start Planning",
  },

  cg_fresh_pick: {
    headline: "Trending Now: 30 Minute Chicken Stir-Fry",
    subtext: "One pan. Fresh veggies. Ready before the kids finish homework. This is what 2,400 families made last week.",
    photoUrl: "https://storage.googleapis.com/wihy-meal-images/meals/30-minute-chicken-stir-fry-6f3183766e40.png",
    cta: "See the Recipe",
  },

  cg_recipe_tip: {
    headline: "5 Ingredients. That's It.",
    subtext: "Chicken bake — toss it in, set the timer, go help with homework. Dinner handles itself. No chopping, no stress, no excuses.",
    photoUrl: "https://storage.googleapis.com/wihy-meal-images/meals/5-ingredient-chicken-bake-68364aac92ad.png",
    cta: "Get the Recipe",
  },

  cg_warm_card: {
    headline: "You're Doing Better Than You Think",
    subtext: "Feeding a family is hard. You don't need to be a chef — you just need a plan. Community Groceries builds it for you in under 2 minutes.",
    photoUrl: "https://storage.googleapis.com/wihy-meal-images/meals/acai-bowl-6249cc0b1ae2.png",
    cta: "Plan This Week",
  },

  // ── Vowels Brand Templates — Straight Facts, No Filter ──────────────────
  vowels_data_card: {
    headline: "\"Best By\" Dates Are Not Expiration Dates",
    subtext: "The USDA does not require expiration dates on any food except infant formula. \"Best by,\" \"sell by,\" and \"use by\" are manufacturer marketing suggestions — not safety dates. Americans throw away $161 billion in food annually based on labels that mean nothing.",
    cta: "Get the Facts",
  },

  vowels_community: {
    headline: "The Word \"Vegan\" Was Coined in 1944",
    subtext: "Donald Watson founded The Vegan Society in November 1944 and created the word from the first and last letters of \"vegetarian.\" Today 79.7 million people worldwide follow a plant-based diet — a movement that started with one person rejecting the status quo.",
    cta: "Read the History",
  },

  vowels_clean_card: {
    headline: "Vitamins Are Not FDA Approved",
    subtext: "The FDA does not test or approve dietary supplements before they hit shelves. There are 80,000+ supplements on the market with zero pre-market safety testing. The $56 billion supplement industry operates on an honor system.",
    cta: "Know Before You Buy",
  },

  vowels_research_tip: {
    headline: "\"Detox\" Products Are Medically Unnecessary",
    subtext: "Your liver processes toxins every second of every day. Your kidneys filter 200 liters of blood daily. The $56B detox industry has zero peer-reviewed clinical evidence supporting juice cleanses, charcoal pills, or foot pads. 48M+ research records confirm it.",
    cta: "See What Studies Show",
  },
};

// ── Formats to preview ──────────────────────────────────────────────────────

const PREVIEW_FORMATS: FormatKey[] = ["feed_square", "story_vertical"];

// ── Main ────────────────────────────────────────────────────────────────────

async function main() {
  // Create preview directory
  if (!fs.existsSync(PREVIEW_DIR)) {
    fs.mkdirSync(PREVIEW_DIR, { recursive: true });
  }

  const templateIds = listTemplateIds();
  console.log(`\nFound ${templateIds.length} templates: ${templateIds.join(", ")}\n`);

  const indexEntries: string[] = [];

  // Sub-brands that use vowels_ templates
  const VOWELS_SUB_BRANDS: BrandId[] = ["snackingwell", "childrennutrition", "parentingwithchrist"];

  // Generic templates (no prefix) should render for ALL brands
  const ALL_BRAND_VARIANTS: { brandId: string | undefined; suffix: string }[] = [
    { brandId: undefined, suffix: "" },                    // WIHY (default)
    { brandId: "communitygroceries", suffix: "_cg" },      // CG
    { brandId: "vowels", suffix: "_vowels" },               // Vowels
  ];

  for (const templateId of templateIds) {
    const data = SAMPLE_DATA[templateId];
    if (!data) {
      console.log(`⚠  No sample data for "${templateId}" — skipping`);
      continue;
    }

    // Determine which brand variants to render for this template
    let brandVariants: { brandId: string | undefined; suffix: string }[];

    if (templateId.startsWith("cg_")) {
      // CG-specific templates → CG only
      brandVariants = [{ brandId: "communitygroceries", suffix: "" }];
    } else if (templateId.startsWith("vowels_")) {
      // Vowels-specific templates → vowels + sub-brands
      brandVariants = [
        { brandId: "vowels", suffix: "" },
        ...VOWELS_SUB_BRANDS.map(sb => ({ brandId: sb as string, suffix: `_${sb}` })),
      ];
    } else {
      // Generic templates → render for WIHY, CG, and Vowels
      brandVariants = ALL_BRAND_VARIANTS;
    }

    for (const { brandId, suffix } of brandVariants) {
      for (const format of PREVIEW_FORMATS) {
        const label = `${templateId}_${format}${suffix}`;
        const brandLabel = brandId || "wihy";
        console.log(`Rendering ${label} (brand: ${brandLabel})...`);

        try {
          const html = renderTemplate(templateId, data, format, brandId);
          const htmlPath = path.join(PREVIEW_DIR, `${label}.html`);
          fs.writeFileSync(htmlPath, html, "utf-8");

          const pngBuffer = await screenshotHtml({ html, outputSize: format, format: "png" });
          const pngPath = path.join(PREVIEW_DIR, `${label}.png`);
          fs.writeFileSync(pngPath, pngBuffer);

          console.log(`  ✓ ${pngPath} (${(pngBuffer.length / 1024).toFixed(0)} KB)`);

          indexEntries.push(`
            <div class="preview-item">
              <h3>${label}.png</h3>
              <img src="${label}.png" alt="${label}" />
              <div class="links">
                <a href="${label}.html" target="_blank">Open HTML</a>
                <a href="${label}.png" target="_blank">Full Size</a>
              </div>
            </div>
          `);
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          console.error(`  ✗ ${label}: ${msg}`);
        }
      }
    }
  }

  // 3. Build index.html
  const indexHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Shania Template Preview</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #111; color: #eee; padding: 40px; }
    h1 { margin-bottom: 8px; }
    .subtitle { color: #888; margin-bottom: 40px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(520px, 1fr)); gap: 32px; }
    .preview-item { background: #1a1a1a; border-radius: 12px; padding: 20px; }
    .preview-item h3 { margin: 0 0 12px; font-size: 13px; color: #ccc; font-family: monospace; word-break: break-all; }
    .preview-item img { width: 100%; height: auto; border-radius: 8px; display: block; }
    .preview-item .links { display: flex; gap: 16px; margin-top: 8px; }
    .preview-item a { color: #38bdf8; text-decoration: none; font-size: 13px; }
    .preview-item a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>Shania Template Preview</h1>
  <p class="subtitle">Generated ${new Date().toISOString()} — ${indexEntries.length} renders</p>
  <div class="grid">
    ${indexEntries.join("\n")}
  </div>
</body>
</html>`;

  const indexPath = path.join(PREVIEW_DIR, "index.html");
  fs.writeFileSync(indexPath, indexHtml, "utf-8");
  console.log(`\n✓ Index: ${indexPath}`);
  console.log(`  Open in browser to see all previews.\n`);

  await closeBrowser();
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
