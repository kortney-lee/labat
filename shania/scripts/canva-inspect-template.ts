import { initCanvaClient, getCanvaClient } from "../src/services/canvaService";
import { loadCanvaCredentials, updateRefreshToken } from "../src/utils/canvaSecrets";

async function main(): Promise<void> {
  const templateId = process.argv[2];
  if (!templateId) {
    throw new Error("Usage: npx ts-node scripts/canva-inspect-template.ts <template-id>");
  }

  const creds = await loadCanvaCredentials();
  initCanvaClient({
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    refreshToken: creds.refreshToken,
    onTokenRefresh: updateRefreshToken,
  });

  const canva = getCanvaClient();
  console.log(`Inspecting template: ${templateId}`);

  const dataset = await canva.getBrandTemplateDataset(templateId);
  const keys = Object.keys(dataset);

  console.log(`Autofill field count: ${keys.length}`);
  if (!keys.length) {
    console.log("No Data Autofill fields are configured on this template.");
    return;
  }

  for (const key of keys) {
    console.log(`${key}: ${dataset[key].type}`);
  }
}

main().catch((err) => {
  console.error("Template inspection failed:", err instanceof Error ? err.message : String(err));
  process.exit(1);
});
