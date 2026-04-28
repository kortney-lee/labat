import { listLibraryAssets } from "./gcs";
import { logger } from "../utils/logger";

const ASSET_LIBRARY_PROVIDER = (
  process.env.ASSET_LIBRARY_PROVIDER || "gcp"
).toLowerCase();

const DRIVE_API_BASE = "https://www.googleapis.com/drive/v3/files";
const DEFAULT_LIBRARY_FOLDER = process.env.ASSET_LIBRARY_FOLDER || "images";
const DEFAULT_PICK_LIMIT = Math.max(
  1,
  Math.min(Number(process.env.ASSET_LIBRARY_PICK_LIMIT || "60"), 200),
);

const _recentUrlsByBrand: Record<string, string[]> = {};
const _maxRecentPerBrand = 12;

export interface AssetLibraryImage {
  provider: "gcp" | "google_drive";
  url: string;
  id: string;
  label: string;
  metadata?: Record<string, string>;
}

interface GoogleDriveFile {
  id: string;
  name: string;
  mimeType: string;
  modifiedTime?: string;
  webViewLink?: string;
}

function normalizeBrand(brand: string): string {
  return (brand || "").trim().toLowerCase() || "wihy";
}

function scoreLabel(label: string, topicHint: string): number {
  if (!topicHint) return 0;
  const labelL = (label || "").toLowerCase();
  const words = topicHint
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((w) => w.length >= 4);
  let score = 0;
  for (const word of words) {
    if (labelL.includes(word)) score += 1;
  }
  return score;
}

function scoreTags(tagsRaw: string, topicHint: string): number {
  if (!topicHint || !tagsRaw) return 0;
  const tags = tagsRaw.toLowerCase();
  const words = topicHint
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((w) => w.length >= 4);
  let score = 0;
  for (const word of words) {
    if (tags.includes(word)) score += 2;
  }
  return score;
}

function chooseNonRecent(brand: string, candidates: AssetLibraryImage[]): AssetLibraryImage | null {
  if (!candidates.length) return null;
  const recent = _recentUrlsByBrand[brand] || [];
  const nonRecent = candidates.filter((item) => !recent.includes(item.url));
  const pool = nonRecent.length ? nonRecent : candidates;
  const pick = pool[Math.floor(Math.random() * pool.length)];

  const nextRecent = [...recent.filter((url) => url !== pick.url), pick.url];
  _recentUrlsByBrand[brand] = nextRecent.slice(-_maxRecentPerBrand);
  return pick;
}

function resolveGoogleDriveFolder(brand: string): string {
  const byBrandRaw = process.env.ASSET_LIBRARY_GOOGLE_DRIVE_FOLDERS || "";
  if (byBrandRaw) {
    try {
      const parsed = JSON.parse(byBrandRaw) as Record<string, string>;
      const folder = parsed[brand] || parsed.default || "";
      if (folder) return folder;
    } catch (err) {
      logger.warn(`Invalid ASSET_LIBRARY_GOOGLE_DRIVE_FOLDERS JSON: ${String(err)}`);
    }
  }
  return process.env.ASSET_LIBRARY_GOOGLE_DRIVE_FOLDER_ID || "";
}

async function listGoogleDriveImages(
  folderId: string,
  apiKey: string,
  limit: number,
): Promise<GoogleDriveFile[]> {
  const q = `'${folderId}' in parents and trashed=false and mimeType contains 'image/'`;
  const params = new URLSearchParams({
    q,
    pageSize: String(limit),
    fields: "files(id,name,mimeType,modifiedTime,webViewLink)",
    includeItemsFromAllDrives: "true",
    supportsAllDrives: "true",
    orderBy: "modifiedTime desc",
    key: apiKey,
  });

  const response = await fetch(`${DRIVE_API_BASE}?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Google Drive list failed: ${response.status} ${await response.text()}`);
  }

  const data = (await response.json()) as { files?: GoogleDriveFile[] };
  return Array.isArray(data.files) ? data.files : [];
}

async function pickFromGoogleDrive(brand: string, topicHint: string): Promise<AssetLibraryImage | null> {
  const apiKey = process.env.ASSET_LIBRARY_GOOGLE_DRIVE_API_KEY || "";
  const folderId = resolveGoogleDriveFolder(brand);
  if (!apiKey || !folderId) {
    logger.warn("Google Drive asset library is enabled but missing API key or folder id");
    return null;
  }

  const files = await listGoogleDriveImages(folderId, apiKey, DEFAULT_PICK_LIMIT);
  if (!files.length) {
    return null;
  }

  const ranked = files
    .map((file) => ({
      file,
      score: scoreLabel(file.name, topicHint),
    }))
    .sort((a, b) => b.score - a.score);

  const mapped: AssetLibraryImage[] = ranked.map(({ file }) => ({
    provider: "google_drive",
    id: file.id,
    label: file.name,
    url: `https://drive.google.com/uc?export=download&id=${file.id}`,
  }));

  return chooseNonRecent(brand, mapped);
}

async function pickFromGcpLibrary(brand: string, topicHint: string): Promise<AssetLibraryImage | null> {
  const items = await listLibraryAssets({
    brand,
    folder: DEFAULT_LIBRARY_FOLDER,
    limit: DEFAULT_PICK_LIMIT,
  });
  if (!items.length) return null;

  const ranked = items
    .map((item) => {
      const tags = (item.metadata?.tags || "") as string;
      const score = scoreLabel(item.path, topicHint) + scoreTags(tags, topicHint);
      return { item, score };
    })
    .sort((a, b) => b.score - a.score);

  const mapped: AssetLibraryImage[] = ranked.map(({ item }) => ({
    provider: "gcp",
    id: item.path,
    label: item.path,
    url: item.publicUrl,
    metadata: item.metadata,
  }));

  return chooseNonRecent(brand, mapped);
}

export async function pickAssetLibraryImage(
  brandInput: string,
  topicHint: string = "",
): Promise<AssetLibraryImage | null> {
  const brand = normalizeBrand(brandInput);

  try {
    if (ASSET_LIBRARY_PROVIDER === "google_drive") {
      return await pickFromGoogleDrive(brand, topicHint);
    }
    return await pickFromGcpLibrary(brand, topicHint);
  } catch (err) {
    logger.warn(`Asset library pick failed for brand=${brand}: ${String(err)}`);
    return null;
  }
}
