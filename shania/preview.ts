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
    headline: "The Hidden Cost of Convenience",
    statNumber: "73%",
    statLabel: "of packaged foods contain additives linked to inflammation",
    dataPoints: [
      "Ultra-processed foods now make up 60% of the American diet",
      "The average child consumes 17 teaspoons of added sugar daily",
      "Only 1 in 10 adults meets daily vegetable intake recommendations",
    ],
    source: "CDC National Health Report, 2025",
    cta: "Learn More",
  },

  hook_square: {
    headline: "What If Everything You Were Told About Nutrition Was Wrong?",
    subtext: "The food industry spends $14 billion a year telling you what to eat. We spent 10 years researching what they don't want you to know.",
    cta: "Get the Book",
    productName: "VOWELS",
  },

  research_card: {
    headline: "What the Research Actually Shows",
    dataPoints: [
      "Artificial sweeteners may alter gut bacteria within 7 days of regular use",
      "Food dyes banned in the EU are still approved in 87% of US children's cereals",
      "Organic produce contains 48% fewer pesticide residues on average",
      "Ultra-processed food consumption correlates with 31% higher all-cause mortality",
    ],
    source: "NIH / Lancet Public Health, 2024",
    cta: "Read the Data",
  },

  quote_card: {
    headline: "A Decade of Research in One Line",
    quote: "We didn't lose our health — we replaced it with convenience.",
    attribution: "WIHY Research Team",
    subtext: "10 years of data. 48 million research articles. One conclusion.",
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

  cg_community: {
    headline: "Dinner Doesn't Have to Be Complicated",
    subtext: "5 ingredients. 20 minutes. A meal your whole family will love.",
    cta: "Get the Recipe",
  },

  cg_fresh_pick: {
    headline: "This Week's Fresh Pick: Sweet Potatoes",
    subtext: "Packed with vitamin A, fiber, and natural sweetness. Perfect for fall family dinners.",
    cta: "See Recipes",
  },

  cg_recipe_tip: {
    headline: "Meal Prep Tip: Batch Your Grains",
    subtext: "Cook rice, quinoa, and oats on Sunday. Use them all week for faster dinners and school lunches.",
    cta: "Get the Full Plan",
  },

  cg_warm_card: {
    headline: "Small Changes, Big Impact",
    subtext: "Swapping one processed snack a day for whole fruit can reduce a child's sugar intake by 40%.",
    cta: "Start Today",
  },

  // ── Vowels Brand Templates ──────────────────────────────────────────────
  vowels_data_card: {
    headline: "73% of School Lunches Exceed Sugar Limits",
    subtext: "New USDA data reveals a widening gap between nutrition guidelines and cafeteria reality.",
    cta: "See the Data",
  },

  vowels_community: {
    headline: "The Data Doesn't Lie",
    subtext: "Childhood obesity rates have tripled since 1975. Research shows exactly what changed.",
    cta: "Read the Study",
  },

  vowels_clean_card: {
    headline: "1 in 3 Children Is Now Overweight",
    subtext: "CDC data shows diet-related illness is the #1 preventable cause of childhood morbidity.",
    cta: "Learn More",
  },

  vowels_research_tip: {
    headline: "Food Subsidies Favor Junk Over Produce",
    subtext: "$19B in annual subsidies go to corn and soy — staples of ultra-processed food manufacturing.",
    cta: "See the Breakdown",
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
              <h3>${templateId} — ${format}${suffix ? ` (${brandLabel})` : ""}</h3>
              <img src="${label}.png" alt="${label}" />
              <a href="${label}.html" target="_blank">Open HTML</a>
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
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 32px; }
    .preview-item { background: #1a1a1a; border-radius: 12px; padding: 20px; }
    .preview-item h3 { margin: 0 0 12px; font-size: 14px; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
    .preview-item img { width: 100%; border-radius: 8px; }
    .preview-item a { display: inline-block; margin-top: 8px; color: #38bdf8; text-decoration: none; font-size: 13px; }
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
