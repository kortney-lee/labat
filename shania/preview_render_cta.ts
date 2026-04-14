import fs from "fs";
import path from "path";
import { renderTemplate } from "./src/renderer/renderHtml";
import { screenshotHtml, closeBrowser } from "./src/renderer/renderImage";

async function main() {
  const data = {
    headline: "Your 'Eco-Friendly' Packaging Isn't.",
    subtext: "What brands don't want you to know.",
    cta: "Read the Article",
    productName: "WIHY",
    badge: "NEW",
    showLogo: true,
    logoUrl: "https://storage.googleapis.com/wihy-web-assets/images/Logo_wihy.png",
    logoAlt: "WIHY logo",
    logoText: "WIHY",
    backgroundImageUrl: "https://images.unsplash.com/photo-1523374228107-6e44bd2b524e?w=1080&h=1080&fit=crop"
  };

  const html = renderTemplate("cta_card", data, "feed_square", "wihy");
  const outDir = path.join(process.cwd(), "preview");

  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  const png = await screenshotHtml({ html, outputSize: "feed_square", format: "png" });
  const pngPath = path.join(outDir, "cta_card_wihy_new.png");
  const htmlPath = path.join(outDir, "cta_card_wihy_new.html");

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
