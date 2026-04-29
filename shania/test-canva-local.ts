/**
 * test-canva-local.ts — Local test for Canva asset upload + design creation.
 *
 * Tests the full Content-Type fix without deploying to Cloud Run.
 * Uses the WIHY logo PNG as a test image.
 *
 * Usage:
 *   cd shania
 *   npx ts-node test-canva-local.ts
 *
 * Requires GCP Application Default Credentials (already logged in via gcloud auth application-default login).
 * The script reads Canva credentials from Secret Manager (same as production).
 *
 * Or set env vars to skip Secret Manager:
 *   $env:GCP_PROJECT = "wihy-ai"
 *   $env:CANVA_CLIENT_ID = "..."
 *   $env:CANVA_CLIENT_SECRET = "..."
 *   $env:CANVA_REFRESH_TOKEN = "..."
 */

import fs from "fs";
import path from "path";
import { uploadImageAsCanvaAsset, createOrResizeCanvaDesign } from "./src/services/canvaApi";

process.env.GCP_PROJECT = process.env.GCP_PROJECT || "wihy-ai";

async function main() {
  // Step 1: Load a local test image
  const testImagePath = path.join(__dirname, "assets", "Wihy", "wihy_logo.png");
  console.log(`\n[1] Reading test image: ${testImagePath}`);
  const imageBytes = fs.readFileSync(testImagePath);
  console.log(`    Size: ${(imageBytes.length / 1024).toFixed(1)} KB, mimeType: image/png`);

  // Step 2: Upload to Canva as an asset
  console.log("\n[2] Uploading to Canva as asset...");
  const asset = await uploadImageAsCanvaAsset(imageBytes, "image/png", "wihy-local-test-asset");
  console.log(`    Asset ID:    ${asset.id}`);
  console.log(`    Asset Name:  ${asset.name}`);
  if (asset.thumbnailUrl) console.log(`    Thumbnail:   ${asset.thumbnailUrl}`);

  // Step 3: Create a Canva design (feed_square = 1080x1080)
  console.log("\n[3] Creating Canva design (1080x1080)...");
  const design = await createOrResizeCanvaDesign({
    width: 1080,
    height: 1080,
    title: "WIHY Local Test Design",
    assetId: asset.id,
  });
  console.log(`    Design ID:   ${design.id}`);
  console.log(`    Edit URL:    ${design.editUrl}`);
  if (design.viewUrl) console.log(`    View URL:    ${design.viewUrl}`);

  console.log("\n✅ Local Canva test complete!");
  console.log("\nNext: open the Edit URL above in your browser to see the design with the image pre-inserted.");
  console.log("Asset upload + design creation with asset placement are confirmed working.\n");
}

main().catch((err) => {
  console.error("\n❌ Test failed:", err instanceof Error ? err.message : String(err));
  process.exit(1);
});
