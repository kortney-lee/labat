import fs from "fs";
import path from "path";
import { renderTemplate } from "./src/renderer/renderHtml";
import { screenshotHtml, closeBrowser } from "./src/renderer/renderImage";

async function main() {
  const data = {
    headline: "Stop Guessing. Start Knowing.",
    subtext: "Scan any product. Get the truth in seconds. No ads, no sponsorships - just science.",
    cta: "Download WIHY Free",
    productName: "WIHY"
  };

  const html = renderTemplate("cta_card", data, "feed_square");
  const outDir = path.join(process.cwd(), "preview");

  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  const png = await screenshotHtml({ html, outputSize: "feed_square", format: "png" });
  const pngPath = path.join(outDir, "cta_card_feed_square_fixed.png");
  const htmlPath = path.join(outDir, "cta_card_feed_square_fixed.html");

  fs.writeFileSync(pngPath, png);
  fs.writeFileSync(htmlPath, html, "utf-8");

  await closeBrowser();
  console.log(`Created ${pngPath}`);
  console.log(`Created ${htmlPath}`);
}

main().catch(async (err) => {
  console.error(err);
  await closeBrowser();
  process.exit(1);
});
