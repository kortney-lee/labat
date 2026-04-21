import fs from "fs";
import path from "path";
import { initCanvaClient, getCanvaClient } from "../src/services/canvaService";
import { loadCanvaCredentials, updateRefreshToken } from "../src/utils/canvaSecrets";
import type { BrandId } from "../src/config/brand";

async function main(): Promise<void> {
  const brandId = (process.argv[2] || "wihy") as BrandId;
  const outArg = process.argv[3];

  console.log(`Generating Canva image locally for brand: ${brandId}`);

  const creds = await loadCanvaCredentials();
  initCanvaClient({
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    refreshToken: creds.refreshToken,
    onTokenRefresh: updateRefreshToken,
  });

  const canva = getCanvaClient();

  const image = await canva.generateDesignImage(brandId, {
    headline: "What Is Healthy?",
  });

  const outputPath = outArg
    ? path.resolve(outArg)
    : path.resolve("preview", `canva-local-${brandId}-${Date.now()}.png`);

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, image);

  console.log(`Saved image: ${outputPath}`);
  console.log(`Bytes: ${image.length}`);
}

main().catch((err) => {
  console.error("Local Canva generation failed:", err instanceof Error ? err.message : String(err));
  process.exit(1);
});
