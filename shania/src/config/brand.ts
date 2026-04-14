/** WIHY brand constants — hardcoded for visual consistency. */

import { logger } from "../utils/logger";

export const BRAND = {
  colors: {
    background: "#e0f2fe",
    backgroundDark: "#0c1d2e",
    primary: "#fa5f06",
    success: "#4cbb17",
    white: "#ffffff",
    cardSurface: "#ffffff",
    textDark: "#111827",
    textMuted: "#6b7280",
    textLight: "#f9fafb",
    danger: "#ef4444",
  },
  fonts: {
    headline: "'Montserrat', sans-serif",
    body: "'Inter', sans-serif",
  },
  fontImport: `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@700;800;900&display=swap');`,
  spacing: {
    xs: "8px",
    sm: "16px",
    md: "24px",
    lg: "40px",
    xl: "64px",
    xxl: "96px",
  },
  radius: {
    sm: "8px",
    md: "16px",
    lg: "24px",
  },
  logo: {
    text: "WIHY",
    tagline: "What Is Healthy for You",
  },
  assets: {
    wihy: {
      logo: "https://storage.googleapis.com/wihy-web-assets/images/Logo_wihy.png",
      bucket: "wihy-web-assets",
    },
    cg: {
      logo: "https://storage.googleapis.com/cg-web-assets/images/Logo_CG.png",
      bucket: "cg-web-assets",
    },
    graphics: {
      bucket: "wihy-shania-graphics",
    },
  },
} as const;

// ────────── Multi-Brand Profiles ──────────

export interface BrandProfile {
  id: string;
  name: string;
  tagline: string;
  domain: string;
  logoUrl: string | null;
  colors: { primary: string; accent: string; bg: string; text: string };
  colorWords: string;
  voice: string;
  topics: string[];
  contentFocus: string;
  hashtagPrefix: string;
  facebookPageId: string | null;
  parentBrand?: string; // Sub-brands publish to their parent's Facebook page
  /** When false, all social posting is blocked for this brand (e.g. not yet launched). Defaults to true. */
  postingEnabled?: boolean;
}

export type BrandId = "wihy" | "communitygroceries" | "vowels" | "snackingwell" | "childrennutrition" | "parentingwithchrist" | "otakulounge";

export const BRANDS: Record<BrandId, BrandProfile> = {
  wihy: {
    id: "wihy",
    name: "WIHY",
    tagline: "What Is Healthy for You",
    domain: "wihy.ai",
    logoUrl: "https://storage.googleapis.com/wihy-web-assets/images/Logo_wihy.png",
    colors: { primary: "#fa5f06", accent: "#4cbb17", bg: "#e0f2fe", text: "#111827" },
    colorWords: "warm orange and vibrant green on light blue",
    voice: `Bold, ambitious, and science-backed — like a performance coach who reads research papers.
"Become superhuman through science." That's the mission. Not preachy, not gentle — direct and empowering.
Uses strong hooks that stop scrolling. Challenges people to upgrade their biology.
Speaks with authority: cold exposure data, VO2 max studies, longevity research, protein science.
Every claim backed by peer-reviewed research. Tone: "Here's exactly what to do and why it works."
Backed by 48M+ research articles. Inspires action, not just awareness.`,
    topics: [
      "biohacking protocols and daily performance stacks",
      "cold exposure, sauna, and heat/cold therapy science",
      "longevity and anti-aging research breakthroughs",
      "VO2 max, grip strength, and biological age markers",
      "sleep optimization and recovery science",
      "protein timing, creatine, and evidence-based supplementation",
      "zone 2 cardio, strength training, and optimal fitness programming",
      "mitochondrial health and cellular energy production",
      "grounding, red light therapy, and photobiomodulation",
      "dopamine, cortisol, and hormonal optimization",
      "fasting protocols and autophagy activation",
      "body composition and metabolic health transformation",
    ],
    contentFocus: `WIHY is for people who want to become SUPERHUMAN — optimizing biology through science-backed protocols.
WiHY = "Why is Health about You" — built by clinical nutrition researchers, RDs, data scientists, and engineers.
Focus on actionable biohacking: cold exposure, sauna, sleep stacks, grounding, red light therapy, protein optimization.
Tone is bold, ambitious, and empowering: "Do these things and you can become superhuman."
Every post should give a specific protocol, research-backed stat, or actionable health upgrade.
Reference real data: VO2 max, grip strength, dopamine levels, mitochondrial density.
WIHY doesn't preach — it challenges you to upgrade your biology. Think Huberman meets Goggins meets science.
Hard-hitting hooks: "Your body replaces 330 billion cells every day — feed it the right raw materials."
WIHY does NOT do generic wellness or food industry exposés — that's Vowels territory.`,
    hashtagPrefix: "WIHY",
    facebookPageId: "937763702752161",
  },

  communitygroceries: {
    id: "communitygroceries",
    name: "Community Groceries",
    tagline: "Connecting families through food",
    domain: "communitygroceries.com",
    logoUrl: "https://storage.googleapis.com/cg-web-assets/images/Logo_CG.png",
    colors: { primary: "#166534", accent: "#f97316", bg: "#f0fdf4", text: "#14532d" },
    colorWords: "fresh green and warm orange on clean white",
    voice: `Warm, practical, and mouthwatering — like a friend who texts you tonight's dinner recipe.
Speaks in real meals: ingredients, cook times, costs. Makes healthy eating feel achievable and delicious.
Every post should make someone hungry or inspired to cook. Food photography energy — not clinical nutrition.
Celebrates real kitchens, real budgets, real families. Recipes that take 30 minutes or less.
Confident but never pushy. Helpful but never complicated. The meal planning app for real people.`,
    topics: [
      "quick weeknight dinner recipes under 30 minutes",
      "budget-friendly meals under $15 for a family",
      "meal prep ideas for the whole week",
      "easy recipes with 5 ingredients or less",
      "trending meals and viral recipes",
      "one-pot and one-pan meals for easy cleanup",
      "high-protein affordable meals",
      "air fryer recipes families love",
      "slow cooker set-and-forget dinners",
      "healthy school lunch ideas kids will eat",
      "Sunday meal prep routines",
      "grocery hauls and budget shopping strategies",
    ],
    contentFocus: `Community Groceries is a FOOD brand — every post should feature a specific meal, recipe, or food hack.
CG drives commerce through food: recipes that link to meal plans, grocery lists that drive app usage.
Post types: quick recipes with ingredients + cook time + cost, meal prep guides, viral food trends, budget grocery hauls.
Show the FOOD: ingredients laid out, meals plated, prep in progress, grocery carts loaded.
Include specifics: "320 cal, 25g protein, $12 for the family, ready in 25 minutes."
CG is NOT about nutrition science or food industry exposés — it's about getting dinner on the table.
Every post should make someone think: "I'm making that tonight." Then they open the app to get the grocery list.
Never overlap with WIHY (biohacking) or Vowels (nutrition facts). CG is pure food commerce and recipes.`,
    hashtagPrefix: "CommunityGroceries",
    facebookPageId: "2051601018287997",
  },

  vowels: {
    id: "vowels",
    name: "Vowels",
    tagline: "Data that speaks for itself",
    domain: "vowels.org",
    logoUrl: "https://storage.googleapis.com/wihy-web-assets/images/brands/vowels_logo.png",
    colors: { primary: "#1e40af", accent: "#7c3aed", bg: "#eff6ff", text: "#1e293b" },
    colorWords: "deep blue and purple on ice white",
    voice: `Sharp, factual, and unapologetic — the nutrition teacher you never had.
Drops hard truths with data: grams of sugar, ingredient lists, industry spending numbers.
Academic authority meets social media punch. Every post is a mini-lesson backed by real labels and real research.
Challenges what people assume is healthy with specific product callouts and comparisons.
Promotes the "What Is Healthy?" book as the definitive guide to food literacy.`,
    topics: [
      "shocking sugar content in 'healthy' foods",
      "food label deception and ingredient tricks",
      "ultra-processed food and its health consequences",
      "food industry marketing spending vs nutrition education",
      "kids' food products that are worse than candy",
      "comparing nutrition labels: marketed health vs reality",
      "hidden ingredients in everyday grocery products",
      "school lunch nutrition failures",
      "sports drink and juice industry deception",
      "organic marketing myths and label loopholes",
    ],
    contentFocus: `Vowels is the nutrition education brand — every post teaches a specific, surprising nutrition fact.
The tone is "a bowl of Lucky Charms has no nutrition value" — direct, data-backed, eye-opening.
Call out specific products by name with real nutrition data: sugar grams, ingredient lists, marketing claims vs reality.
Promote the "What Is Healthy?" book as the source of truth for food literacy.
Style: investigative journalism meets nutrition science. Show the label. Show the data. Let people decide.
Vowels does NOT do recipes (that's CG) or biohacking (that's WIHY). Vowels is pure nutrition EDUCATION.
Every post should make someone look at their pantry differently. "I didn't know that was in there."
Reference real numbers: $14B food marketing, 19 hours of med school nutrition, 77g daily sugar average.`,
    hashtagPrefix: "Vowels",
    facebookPageId: "100193518975897",
  },

  snackingwell: {
    id: "snackingwell",
    name: "Snacking Well",
    tagline: "Smart snacks, healthier habits",
    domain: "snackingwell.com",
    logoUrl: null, // Sub-brand of Vowels — uses Vowels page
    colors: { primary: "#ea580c", accent: "#65a30d", bg: "#fff7ed", text: "#431407" },
    colorWords: "burnt orange and lime green on warm cream",
    voice: `Fun, approachable, and practical. Family-friendly.
Makes healthy snacking feel exciting, not restrictive. Celebrates smart swaps and better choices.
Speaks to parents, students, and anyone who snacks (everyone).`,
    parentBrand: "vowels",
    topics: [
      "healthy snack alternatives and smart swaps",
      "after-school and on-the-go snack ideas",
      "hidden sugar and sodium in popular snacks",
      "reading snack labels like a pro",
      "portion control without deprivation",
      "kids' snacking habits and solutions",
      "protein-rich and fiber-rich snack options",
      "snack meal prep and batch preparation",
      "workplace and school vending machine alternatives",
      "snack industry marketing tactics exposed",
    ],
    contentFocus: `Snacking Well makes healthy snacking fun, practical, and accessible for everyone.
Focus on real snack foods — comparisons, swaps, recipes, label reads.
Show actual food photography: colorful fruits, nuts, whole grain crackers, trail mixes.
Every post should give a specific, actionable snack tip or swap.`,
    hashtagPrefix: "SnackingWell",
    facebookPageId: "100193518975897", // Publishes to Vowels page
  },

  childrennutrition: {
    id: "childrennutrition",
    name: "Children's Nutrition Education",
    tagline: "Raising healthier kids through smarter food choices",
    domain: "whatishealthy.org",
    logoUrl: null,
    parentBrand: "vowels",
    colors: { primary: "#059669", accent: "#f59e0b", bg: "#ecfdf5", text: "#064e3b" },
    colorWords: "emerald green and warm amber on soft mint",
    voice: `Caring, educational, and empowering — like a trusted teacher who makes nutrition fun.
Speaks to parents, caregivers, and educators about feeding kids well.
Evidence-based but never preachy. Practical tips that busy families can actually use.
Celebrates small wins: packing a better lunch box, trying a new veggie, reading a label together.
Promotes the "What Is Healthy?" book as a family resource for food literacy.`,
    topics: [
      "children's nutrition education and food literacy",
      "teaching kids to read food labels",
      "healthy school lunch ideas and meal prep",
      "reducing sugar in children's diets",
      "picky eater strategies backed by research",
      "childhood obesity prevention through nutrition awareness",
      "age-appropriate nutrition conversations with kids",
      "hidden ingredients in kids' favorite foods",
      "family meal planning for better child nutrition",
      "the What Is Healthy book — a guide for families",
    ],
    contentFocus: `Children's Nutrition Education helps parents and educators raise food-literate kids.
Focus on practical, evidence-based nutrition tips for children and families.
Promote the "What Is Healthy?" book (whatishealthy.org) as a free resource for food label education.
Show real family moments: kids helping in the kitchen, reading labels at the store, trying new foods.
Every post should teach ONE actionable thing a parent can do today to improve their child's nutrition.
Tone: supportive and encouraging, never guilt-tripping. Celebrate progress over perfection.`,
    hashtagPrefix: "ChildrensNutrition",
    facebookPageId: "269598952893508",
  },

  parentingwithchrist: {
    id: "parentingwithchrist",
    name: "Parenting with Christ",
    tagline: "Faith-centered parenting for modern families",
    domain: "", // TBD
    logoUrl: null,
    parentBrand: "vowels",
    colors: { primary: "#7c3aed", accent: "#f59e0b", bg: "#faf5ff", text: "#1e1b4b" },
    colorWords: "soft purple and warm amber on lavender white",
    voice: `Gentle, faith-driven, and encouraging.
Speaks to Christian parents navigating modern challenges with biblical wisdom.
Warm and supportive — never judgmental. Celebrates the journey of raising children with purpose.`,
    topics: [
      "faith-based parenting strategies",
      "teaching children biblical values",
      "balancing faith and modern parenting challenges",
      "family devotionals and prayer habits",
      "Christian perspectives on child development",
    ],
    contentFocus: `Parenting with Christ supports faith-centered families with practical, biblical parenting wisdom.
Focus on real-life parenting moments viewed through a faith lens.
Every post should encourage and equip parents to raise children with purpose and love.`,
    hashtagPrefix: "ParentingWithChrist",
    facebookPageId: "329626030226536",
  },

  otakulounge: {
    id: "otakulounge",
    name: "Otaku Lounge",
    tagline: "Your chill spot for anime and manga culture",
    domain: "", // TBD
    logoUrl: null,
    colors: { primary: "#ef4444", accent: "#3b82f6", bg: "#0f172a", text: "#f1f5f9" },
    colorWords: "vibrant red and electric blue on dark slate",
    voice: `Energetic, passionate, and community-driven.
Speaks the language of anime and manga fans — casual, fun, and deeply knowledgeable.
Celebrates otaku culture without gatekeeping. Inclusive and welcoming to all fan levels.`,
    topics: [
      "anime reviews and seasonal watchlists",
      "manga recommendations and new releases",
      "cosplay inspiration and community spotlights",
      "Japanese culture and its influence on anime",
      "fan theories and deep dives into popular series",
    ],
    contentFocus: `Otaku Lounge is the go-to community hub for anime and manga enthusiasts.
Focus on engaging fan content: reviews, recommendations, memes, and discussion starters.
Visual style: bold, colorful, anime-inspired graphics with dynamic compositions.
Every post should spark conversation or give fans something to share.`,
    hashtagPrefix: "OtakuLounge",
    facebookPageId: "244564118751271",
    postingEnabled: false, // Brand not yet launched — block all social posting
  },
};

export function getBrand(brandId?: string): BrandProfile {
  if (brandId && brandId in BRANDS) return BRANDS[brandId as BrandId];
  if (brandId) {
    const mode = (process.env.BRAND_ENFORCEMENT_MODE || "warn").toLowerCase();
    if (mode === "enforce") {
      throw new Error(`Unknown brand "${brandId}" — rejected in enforce mode`);
    }
    logger.warn(`Unknown brand "${brandId}", falling back to wihy (warn mode)`);
  }
  return BRANDS.wihy;
}

/** Validate that a template is compatible with a brand. Branded templates require matching brand. */
export function validateTemplateBrand(templateId: string, brandId?: string): { valid: boolean; reason?: string } {
  const isCGTemplate = templateId.startsWith("cg_");
  const isCGBrand = brandId === "communitygroceries";
  const isVowelsTemplate = templateId.startsWith("vowels_");
  const isVowelsBrand = brandId === "vowels" || (brandId && BRANDS[brandId as BrandId]?.parentBrand === "vowels");

  if (isCGTemplate && !isCGBrand) {
    return { valid: false, reason: `Template "${templateId}" is a Community Groceries template but brand is "${brandId || "wihy"}". Use brand="communitygroceries".` };
  }
  if (isCGBrand && !isCGTemplate) {
    return { valid: false, reason: `Brand "communitygroceries" should use cg_* templates, not "${templateId}".` };
  }
  if (isVowelsTemplate && !isVowelsBrand) {
    return { valid: false, reason: `Template "${templateId}" is a Vowels template but brand is "${brandId || "wihy"}". Use brand="vowels" (or a Vowels sub-brand).` };
  }
  if (isVowelsBrand && !isVowelsTemplate) {
    return { valid: false, reason: `Brand "${brandId}" (Vowels family) should use vowels_* templates, not "${templateId}".` };
  }
  return { valid: true };
}

/** Resolve the effective logo URL for a brand, inheriting from parent when logoUrl is null. */
export function resolveLogoUrl(brand: BrandProfile): string {
  if (brand.logoUrl) return brand.logoUrl;
  if (brand.parentBrand && brand.parentBrand in BRANDS) {
    const parent = BRANDS[brand.parentBrand as BrandId];
    if (parent.logoUrl) return parent.logoUrl;
  }
  return BRAND.assets.wihy.logo;
}

/** CSS custom properties injected into every template. */
export function brandCSSVars(): string {
  return `
    :root {
      --bg: ${BRAND.colors.background};
      --bg-dark: ${BRAND.colors.backgroundDark};
      --primary: ${BRAND.colors.primary};
      --success: ${BRAND.colors.success};
      --white: ${BRAND.colors.white};
      --card: ${BRAND.colors.cardSurface};
      --text-dark: ${BRAND.colors.textDark};
      --text-muted: ${BRAND.colors.textMuted};
      --text-light: ${BRAND.colors.textLight};
      --danger: ${BRAND.colors.danger};
      --font-headline: ${BRAND.fonts.headline};
      --font-body: ${BRAND.fonts.body};
      --sp-xs: ${BRAND.spacing.xs};
      --sp-sm: ${BRAND.spacing.sm};
      --sp-md: ${BRAND.spacing.md};
      --sp-lg: ${BRAND.spacing.lg};
      --sp-xl: ${BRAND.spacing.xl};
      --sp-xxl: ${BRAND.spacing.xxl};
      --radius-sm: ${BRAND.radius.sm};
      --radius-md: ${BRAND.radius.md};
      --radius-lg: ${BRAND.radius.lg};
    }
  `;
}
