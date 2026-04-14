/**
 * store.ts — In-memory research post store.
 *
 * Holds research articles published by the Moltbook bot and other agents.
 * Each post gets a slug, stored with title, body, citations, topic, and optional image.
 */

import { logger } from "../utils/logger";

export interface ResearchCitation {
  title: string;
  url: string;
  source?: string;
  year?: number;
}

export interface ResearchPost {
  id: string;
  slug: string;
  title: string;
  body: string;
  topic: string;
  citations: ResearchCitation[];
  imageUrl?: string;
  author: string;
  brand: string;
  publishedAt: string;
  updatedAt: string;
}

// ── In-memory store ──────────────────────────────────────────────────────────

const posts: Map<string, ResearchPost> = new Map();
const slugIndex: Map<string, string> = new Map(); // slug → id
let counter = 0;

function generateSlug(title: string): string {
  const base = title
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 80)
    .replace(/^-|-$/g, "");
  // Ensure uniqueness
  let slug = base || "research";
  let attempt = 0;
  while (slugIndex.has(slug)) {
    attempt++;
    slug = `${base}-${attempt}`;
  }
  return slug;
}

export function createPost(data: {
  title: string;
  body: string;
  topic?: string;
  citations?: ResearchCitation[];
  imageUrl?: string;
  author?: string;
  brand?: string;
}): ResearchPost {
  counter++;
  const id = `rp_${counter}_${Date.now()}`;
  const slug = generateSlug(data.title);
  const now = new Date().toISOString();

  const post: ResearchPost = {
    id,
    slug,
    title: data.title,
    body: data.body,
    topic: data.topic || "general",
    citations: data.citations || [],
    imageUrl: data.imageUrl,
    author: data.author || "wihyhealthbot",
    brand: data.brand || "wihy",
    publishedAt: now,
    updatedAt: now,
  };

  posts.set(id, post);
  slugIndex.set(slug, id);
  logger.info(`Research post created: ${slug} (${id})`);
  return post;
}

export function getPostBySlug(slug: string): ResearchPost | undefined {
  const id = slugIndex.get(slug);
  return id ? posts.get(id) : undefined;
}

export function getPostById(id: string): ResearchPost | undefined {
  return posts.get(id);
}

export function listPosts(topic?: string, limit: number = 50): ResearchPost[] {
  let all = Array.from(posts.values());
  if (topic) {
    all = all.filter((p) => p.topic === topic);
  }
  return all.sort((a, b) => b.publishedAt.localeCompare(a.publishedAt)).slice(0, limit);
}

export function getStats(): { total: number; topics: Record<string, number> } {
  const topics: Record<string, number> = {};
  for (const post of posts.values()) {
    topics[post.topic] = (topics[post.topic] || 0) + 1;
  }
  return { total: posts.size, topics };
}
