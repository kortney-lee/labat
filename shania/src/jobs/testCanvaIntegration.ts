/**
 * jobs/testCanvaIntegration.ts — Test Canva integration
 *
 * Usage:
 *   npm run build && node dist/jobs/testCanvaIntegration.js
 */

import { initCanvaClient, getCanvaClient } from "../services/canvaService";
import { loadCanvaCredentials, updateRefreshToken } from "../utils/canvaSecrets";
import { BRAND_CANVA_TEMPLATES } from "../config/canva";
import { logger } from "../utils/logger";
import type { BrandId } from "../config/brand";

const BRANDS_TO_TEST: BrandId[] = [
  "wihy",
  "communitygroceries",
  "vowels",
  "snackingwell",
  "childrennutrition",
  "parentingwithchrist",
  "otakulounge",
];

async function main() {
  console.log("Testing Canva Integration\n");

  // Step 1: Load credentials
  console.log("Loading Canva credentials...");
  const creds = await loadCanvaCredentials();
  console.log(`  clientId: ${creds.clientId.slice(0, 12)}...`);
  console.log(`  brandTemplates: ${Object.keys(creds.brandTemplates).length} configured\n`);

  // Step 2: Initialize client
  initCanvaClient({
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    refreshToken: creds.refreshToken,
    onTokenRefresh: updateRefreshToken,
  });
  const canva = getCanvaClient();
  console.log("Canva client initialized\n");

  // Step 3: List brand templates
  console.log("Listing available brand templates...");
  try {
    const templates = await canva.listBrandTemplates();
    console.log(`  Found ${templates.length} brand template(s)`);
    templates.forEach((t) => console.log(`    ID: ${t.id}  |  ${t.title}`));
    console.log();
  } catch (err) {
    logger.warn(`Could not list brand templates: ${err}`);
    console.log("  (Requires Canva Enterprise or approved dev access)\n");
  }

  // Step 4: Test design creation per brand
  console.log("Testing design generation per brand...\n");

  for (const brandId of BRANDS_TO_TEST) {
    const templateId = BRAND_CANVA_TEMPLATES[brandId];
    if (!templateId) {
      console.log(`  SKIP ${brandId} — no template ID configured`);
      continue;
    }

    console.log(`  Testing ${brandId} (template: ${templateId})...`);
    try {
      const imageBuffer = await canva.generateDesignImage(brandId, {
        headline: `${brandId} — Test Headline`,
        subtext: `This is a test post for ${brandId}`,
        cta: "Learn More",
        statNumber: "42",
        statLabel: "Health Score",
        tip: "Tip: Stay healthy and hydrated!",
        source: "WIHY Research",
      });
      console.log(`    OK — ${imageBuffer.length} bytes`);
    } catch (err) {
      console.log(`    ERROR — ${err instanceof Error ? err.message : String(err)}`);
    }
  }
}

main().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});
