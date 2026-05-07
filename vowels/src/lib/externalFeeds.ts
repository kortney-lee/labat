import { XMLParser } from "fast-xml-parser";

export interface ExternalFeedArticle {
  id: string;
  title: string;
  link: string;
  source: string;
  publishedAt?: string;
  summary?: string;
  imageUrl?: string;
  author?: string;
  category?: string;
}

interface FeedSource {
  name: string;
  url: string;
}

const DEFAULT_FEEDS: FeedSource[] = [
  { name: "BBC Health", url: "https://feeds.bbci.co.uk/news/health/rss.xml" },
  { name: "NPR Health", url: "https://feeds.npr.org/1128/rss.xml" },
  { name: "Reuters Health", url: "https://www.reutersagency.com/feed/?best-topics=health&post_type=best" },
  { name: "NIH News in Health", url: "https://newsinhealth.nih.gov/rss.xml" },
  { name: "CDC Media", url: "https://tools.cdc.gov/api/v2/resources/media/403372.rss" },
  { name: "WHO News", url: "https://www.who.int/rss-feeds/news-english.xml" },
  { name: "Mayo Clinic", url: "https://newsnetwork.mayoclinic.org/feed/" },
  { name: "Cleveland Clinic", url: "https://health.clevelandclinic.org/feed/" },
  { name: "Harvard Health", url: "https://www.health.harvard.edu/blog/feed" },
  { name: "Yale Medicine", url: "https://www.yalemedicine.org/news/rss" },
  { name: "Johns Hopkins Medicine", url: "https://www.hopkinsmedicine.org/rss/news-releases" },
  { name: "Stanford Medicine", url: "https://med.stanford.edu/news/all-news.rss.xml" },
  { name: "Kaiser Health News", url: "https://kffhealthnews.org/feed/" },
  { name: "Medical News Today", url: "https://www.medicalnewstoday.com/rss" },
  { name: "Healthline", url: "https://www.healthline.com/rss" },
  { name: "ScienceDaily Nutrition", url: "https://www.sciencedaily.com/rss/health_medicine/nutrition.xml" },
  { name: "ScienceDaily Obesity", url: "https://www.sciencedaily.com/rss/health_medicine/obesity.xml" },
  { name: "ScienceDaily Public Health", url: "https://www.sciencedaily.com/rss/health_medicine/public_health.xml" },
  { name: "ScienceDaily Diabetes", url: "https://www.sciencedaily.com/rss/health_medicine/diabetes.xml" },
  { name: "ScienceDaily Heart", url: "https://www.sciencedaily.com/rss/health_medicine/heart_disease.xml" },
  { name: "ACS Nutrition", url: "https://www.acs.org/pressroom/rss/nutrition.xml" },
  { name: "EurekAlert Health", url: "https://www.eurekalert.org/rss/health.xml" },
  { name: "EurekAlert Medicine", url: "https://www.eurekalert.org/rss/medicine.xml" },
  { name: "NutritionFacts", url: "https://nutritionfacts.org/feed/" },
  { name: "Today's Dietitian", url: "https://www.todaysdietitian.com/rss.xml" },
  { name: "Academy Nutrition", url: "https://www.eatright.org/rss" },
  { name: "American Heart Association", url: "https://newsroom.heart.org/rss" },
  { name: "American Diabetes Association", url: "https://diabetes.org/rss.xml" },
  { name: "USDA", url: "https://www.usda.gov/media/press-releases/feed" },
  { name: "FDA Consumer", url: "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/consumer-updates/rss.xml" },
];

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: "",
  trimValues: true,
  parseTagValue: true,
});

function asArray<T>(value: T | T[] | undefined): T[] {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function decodeHtmlEntities(value: string): string {
  const named: Record<string, string> = {
    amp: "&",
    lt: "<",
    gt: ">",
    quot: '"',
    apos: "'",
    nbsp: " ",
  };

  return value
    .replace(/&#(\d+);/g, (_, dec: string) => String.fromCharCode(Number(dec)))
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex: string) => String.fromCharCode(parseInt(hex, 16)))
    .replace(/&([a-zA-Z]+);/g, (full: string, key: string) => named[key] ?? full);
}

function stripHtml(value: string | undefined): string {
  if (!value) return "";
  return decodeHtmlEntities(value)
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function parseDate(value: unknown): string | undefined {
  if (!value) return undefined;
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toISOString();
}

function itemId(link: string, title: string): string {
  return `${link}::${title}`.toLowerCase();
}

function pickImageFromHtml(html: string | undefined): string | undefined {
  if (!html) return undefined;
  const match = html.match(/<img[^>]+src=["']([^"']+)["']/i);
  return match?.[1];
}

function pickImageFromRssItem(item: Record<string, unknown>): string | undefined {
  const mediaContent = item["media:content"] as Record<string, unknown> | Record<string, unknown>[] | undefined;
  const mediaThumb = item["media:thumbnail"] as Record<string, unknown> | Record<string, unknown>[] | undefined;
  const enclosure = item.enclosure as Record<string, unknown> | Record<string, unknown>[] | undefined;

  const media = [...asArray(mediaContent), ...asArray(mediaThumb), ...asArray(enclosure)].find(
    (m) => typeof m?.url === "string" || typeof m?.href === "string",
  );

  const direct = (media?.url as string | undefined) || (media?.href as string | undefined);
  if (direct) return direct;

  return pickImageFromHtml(String(item["content:encoded"] || item.description || item.summary || ""));
}

function pickImageFromAtomEntry(entry: Record<string, unknown>): string | undefined {
  const links = asArray(entry.link as Record<string, unknown> | Record<string, unknown>[]);
  const enclosure = links.find((l) => l?.rel === "enclosure" && typeof l?.href === "string")?.href as string | undefined;
  if (enclosure) return enclosure;
  return pickImageFromHtml(String(entry.content || entry.summary || ""));
}

function fromRss(source: string, xml: string): ExternalFeedArticle[] {
  const data = parser.parse(xml);
  const items = asArray(data?.rss?.channel?.item);
  const rows: ExternalFeedArticle[] = [];

  for (const item of items as Record<string, unknown>[]) {
    const title = stripHtml(String(item?.title || ""));
    const link = String(item?.link || item?.guid || "").trim();
    if (!title || !link) continue;

    const summary = stripHtml(String(item?.description || item?.summary || ""));
    const publishedAt = parseDate(item?.pubDate || item?.published || item?.updated);
    const imageUrl = pickImageFromRssItem(item);
    const author = stripHtml(String(item?.author || item?.creator || "")) || undefined;
    const category = stripHtml(String(item?.category || "")) || undefined;

    if (link.includes("vowels.org")) continue;

    rows.push({
      id: itemId(link, title),
      title,
      link,
      source,
      publishedAt,
      summary,
      imageUrl,
      author,
      category,
    });
  }

  return rows;
}

function fromAtom(source: string, xml: string): ExternalFeedArticle[] {
  const data = parser.parse(xml);
  const entries = asArray(data?.feed?.entry);
  const rows: ExternalFeedArticle[] = [];

  for (const entry of entries as Record<string, unknown>[]) {
    const title = stripHtml(String(entry?.title || ""));
    const links = asArray(entry?.link as Record<string, unknown> | Record<string, unknown>[]);
    const href = links.find((l) => l?.rel === "alternate")?.href || links[0]?.href;
    const link = String(href || "").trim();
    if (!title || !link) continue;

    const summary = stripHtml(String(entry?.summary || entry?.content || ""));
    const publishedAt = parseDate(entry?.updated || entry?.published);
    const imageUrl = pickImageFromAtomEntry(entry);
    const authorField = entry.author as Record<string, unknown> | undefined;
    const author = stripHtml(String(authorField?.name || entry.author || "")) || undefined;
    const category = stripHtml(String(entry?.category || "")) || undefined;

    if (link.includes("vowels.org")) continue;

    rows.push({
      id: itemId(link, title),
      title,
      link,
      source,
      publishedAt,
      summary,
      imageUrl,
      author,
      category,
    });
  }

  return rows;
}

async function fetchOne(source: FeedSource): Promise<ExternalFeedArticle[]> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 7000);

  try {
    const res = await fetch(source.url, {
      method: "GET",
      headers: {
        "User-Agent": "vowels.org rss aggregator",
        Accept: "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
      },
      cache: "no-store",
      signal: controller.signal,
    });

    if (!res.ok) return [];
    const xml = await res.text();
    if (!xml) return [];

    if (xml.includes("<rss") || xml.includes("<channel")) {
      return fromRss(source.name, xml);
    }

    if (xml.includes("<feed") && xml.includes("<entry")) {
      return fromAtom(source.name, xml);
    }

    return [];
  } catch {
    return [];
  } finally {
    clearTimeout(timeout);
  }
}

function feedSources(): FeedSource[] {
  const extra = (process.env.EXTERNAL_RSS_FEEDS || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean)
    .map((url) => ({ name: "External", url }));
  return [...DEFAULT_FEEDS, ...extra];
}

function diversifyBySource(items: ExternalFeedArticle[], maxRun = 2): ExternalFeedArticle[] {
  const remaining = [...items];
  const arranged: ExternalFeedArticle[] = [];
  let lastSource = "";
  let run = 0;

  while (remaining.length) {
    let pickIndex = 0;
    if (run >= maxRun) {
      const nextDifferent = remaining.findIndex((item) => item.source !== lastSource);
      if (nextDifferent >= 0) pickIndex = nextDifferent;
    }

    const [picked] = remaining.splice(pickIndex, 1);
    arranged.push(picked);

    if (picked.source === lastSource) {
      run += 1;
    } else {
      lastSource = picked.source;
      run = 1;
    }
  }

  return arranged;
}

export async function getExternalFeedArticles(limit = 120): Promise<ExternalFeedArticle[]> {
  const batches = feedSources();
  const responses = await Promise.allSettled(batches.map((source) => fetchOne(source)));

  const all = responses
    .filter((r): r is PromiseFulfilledResult<ExternalFeedArticle[]> => r.status === "fulfilled")
    .flatMap((r) => r.value);

  const dedup = new Map<string, ExternalFeedArticle>();
  for (const article of all) {
    if (!dedup.has(article.id)) dedup.set(article.id, article);
  }

  const sorted = Array.from(dedup.values())
    .sort((a, b) => +new Date(b.publishedAt || 0) - +new Date(a.publishedAt || 0))
    .slice(0, limit * 2);

  return diversifyBySource(sorted).slice(0, limit);
}