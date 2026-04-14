/**
 * research.ts — Research bot page routes.
 *
 * Moltbook-only pages where research posts are displayed.
 * These are NOT for the public wihy.ai client — they are cross-posted
 * from Moltbook bot and should only be consumed on moltbook.com.
 *
 * Endpoints:
 *   GET  /research-bot              → HTML index page (latest research posts)
 *   GET  /research-bot/posts        → JSON list of posts
 *   GET  /research-bot/:slug        → HTML individual article page
 *   GET  /research-bot/:slug/json   → JSON single post
 *   POST /research-bot/posts        → Create a new research post (requires X-Admin-Token)
 */

import { Router, Request, Response } from "express";
import {
  createPost,
  getPostBySlug,
  listPosts,
  getStats,
  ResearchPost,
  ResearchCitation,
} from "../../research/store";
import { logger } from "../../utils/logger";

const router = Router();
const ADMIN_TOKEN = process.env.INTERNAL_ADMIN_TOKEN || process.env.ADMIN_TOKEN || "";

// ── JSON API ─────────────────────────────────────────────────────────────────

/** GET /research-bot/posts — list all research posts. */
router.get("/research-bot/posts", (_req: Request, res: Response): void => {
  const topic = _req.query.topic as string | undefined;
  const limit = parseInt((_req.query.limit as string) || "50", 10);
  const items = listPosts(topic, limit);
  const stats = getStats();
  res.json({ stats, posts: items });
});

/** GET /research-bot/:slug/json — single post as JSON. */
router.get("/research-bot/:slug/json", (req: Request<{ slug: string }>, res: Response): void => {
  const post = getPostBySlug(req.params.slug);
  if (!post) {
    res.status(404).json({ error: "Post not found" });
    return;
  }
  res.json(post);
});

/** POST /research-bot/posts — create a new research post. */
router.post("/research-bot/posts", (req: Request, res: Response): void => {
  const token = req.headers["x-admin-token"] as string;
  if (!ADMIN_TOKEN || token !== ADMIN_TOKEN) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  const { title, body, topic, citations, imageUrl, author, brand } = req.body;
  if (!title || !body) {
    res.status(400).json({ error: "title and body are required" });
    return;
  }

  const post = createPost({ title, body, topic, citations, imageUrl, author, brand });
  logger.info(`Research post created via API: ${post.slug}`);
  res.status(201).json(post);
});

// ── HTML Pages ───────────────────────────────────────────────────────────────

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderCitations(citations: ResearchCitation[]): string {
  if (!citations.length) return "";
  const items = citations
    .map((c) => {
      const title = escapeHtml(c.title);
      const source = c.source ? ` — ${escapeHtml(c.source)}` : "";
      const year = c.year ? ` (${c.year})` : "";
      return c.url
        ? `<li><a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">${title}</a>${source}${year}</li>`
        : `<li>${title}${source}${year}</li>`;
    })
    .join("\n");
  return `<section class="citations"><h3>Sources</h3><ol>${items}</ol></section>`;
}

function renderPostCard(post: ResearchPost): string {
  const excerpt = escapeHtml(post.body.slice(0, 200)) + (post.body.length > 200 ? "..." : "");
  const imageHtml = post.imageUrl
    ? `<img class="post-hero" src="${escapeHtml(post.imageUrl)}" alt="${escapeHtml(post.title)}" />`
    : "";
  return `
    <article class="post-card">
      ${imageHtml}
      <div class="post-body">
        <span class="topic-badge">${escapeHtml(post.topic)}</span>
        <h2><a href="/research-bot/${escapeHtml(post.slug)}">${escapeHtml(post.title)}</a></h2>
        <p class="excerpt">${excerpt}</p>
        <div class="meta">
          <span class="author">@${escapeHtml(post.author)}</span>
          <time>${new Date(post.publishedAt).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}</time>
          ${post.citations.length ? `<span class="cite-count">${post.citations.length} sources</span>` : ""}
        </div>
      </div>
    </article>`;
}

const PAGE_CSS = `
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Inter', sans-serif; background: #f8fafc; color: #1e293b; }
  .container { max-width: 900px; margin: 0 auto; padding: 2rem 1rem; }
  header { text-align: center; margin-bottom: 2.5rem; border-bottom: 3px solid #fa5f06; padding-bottom: 1.5rem; }
  header h1 { font-size: 2rem; font-weight: 800; color: #111827; }
  header h1 span { color: #fa5f06; }
  header p { color: #64748b; margin-top: 0.5rem; font-size: 1.05rem; }
  .stats { display: flex; gap: 1rem; justify-content: center; margin-top: 1rem; flex-wrap: wrap; }
  .stat { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.85rem; }
  .stat strong { color: #fa5f06; }
  .post-card { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 1.5rem; overflow: hidden; }
  .post-hero { width: 100%; height: 220px; object-fit: cover; }
  .post-body { padding: 1.25rem 1.5rem; }
  .topic-badge { background: #fff7ed; color: #ea580c; font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 4px; text-transform: uppercase; }
  .post-card h2 { margin: 0.75rem 0 0.5rem; font-size: 1.25rem; }
  .post-card h2 a { color: #111827; text-decoration: none; }
  .post-card h2 a:hover { color: #fa5f06; }
  .excerpt { color: #475569; line-height: 1.6; }
  .meta { margin-top: 0.75rem; font-size: 0.8rem; color: #94a3b8; display: flex; gap: 1rem; align-items: center; }
  .cite-count { background: #f0fdf4; color: #166534; padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 600; }
  .empty { text-align: center; color: #94a3b8; padding: 3rem 0; }
  .empty h2 { font-size: 1.3rem; margin-bottom: 0.5rem; }

  /* Article page */
  .article { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); padding: 2rem; }
  .article .hero-img { width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; margin-bottom: 1.5rem; }
  .article h1 { font-size: 1.75rem; margin-bottom: 0.5rem; }
  .article .article-meta { font-size: 0.85rem; color: #94a3b8; margin-bottom: 1.5rem; display: flex; gap: 1rem; flex-wrap: wrap; }
  .article .content { line-height: 1.8; color: #334155; white-space: pre-wrap; }
  .citations { margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0; }
  .citations h3 { font-size: 1rem; margin-bottom: 0.75rem; color: #475569; }
  .citations ol { padding-left: 1.25rem; }
  .citations li { margin-bottom: 0.5rem; font-size: 0.9rem; color: #64748b; }
  .citations a { color: #2563eb; text-decoration: none; }
  .citations a:hover { text-decoration: underline; }
  .back-link { display: inline-block; margin-bottom: 1.5rem; color: #fa5f06; text-decoration: none; font-weight: 600; }
  .back-link:hover { text-decoration: underline; }
  footer { text-align: center; margin-top: 2rem; font-size: 0.8rem; color: #94a3b8; }
  footer a { color: #fa5f06; text-decoration: none; }
</style>`;

/** GET /research-bot — HTML index page. */
router.get("/research-bot", (_req: Request, res: Response): void => {
  res.setHeader("X-Robots-Tag", "noindex, nofollow");
  const topic = _req.query.topic as string | undefined;
  const items = listPosts(topic, 50);
  const stats = getStats();

  const statsHtml = `
    <div class="stats">
      <div class="stat"><strong>${stats.total}</strong> articles</div>
      ${Object.entries(stats.topics)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 6)
        .map(([t, c]) => `<div class="stat"><strong>${c}</strong> ${escapeHtml(t)}</div>`)
        .join("")}
    </div>`;

  const postsHtml = items.length
    ? items.map(renderPostCard).join("")
    : `<div class="empty"><h2>No research posts yet</h2><p>Posts will appear here as agents publish research.</p></div>`;

  res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WIHY Research Bot — Evidence-Based Health Research</title>
  <meta name="description" content="Science-backed health research from the WIHY Health Bot. PubMed-cited findings on nutrition, supplements, exercise, and more.">
  <meta name="robots" content="noindex, nofollow">
  ${PAGE_CSS}
</head>
<body>
  <div class="container">
    <header>
      <h1><span>WIHY</span> Research Bot</h1>
      <p>Evidence-based health research — powered by PubMed and the WIHY knowledge base</p>
      ${statsHtml}
    </header>
    ${postsHtml}
    <footer>Powered by <a href="https://wihy.ai">WIHY</a> &middot; <a href="https://www.moltbook.com/u/wihyhealthbot">@wihyhealthbot on Moltbook</a></footer>
  </div>
</body>
</html>`);
});

/** GET /research-bot/:slug — HTML article page. */
router.get("/research-bot/:slug", (req: Request<{ slug: string }>, res: Response): void => {
  res.setHeader("X-Robots-Tag", "noindex, nofollow");
  // Skip the /json suffix route
  if (req.params.slug.endsWith("/json")) return;

  const post = getPostBySlug(req.params.slug);
  if (!post) {
    res.status(404).send(`<!DOCTYPE html>
<html><head><title>Not Found</title>${PAGE_CSS}</head>
<body><div class="container"><div class="empty"><h2>Post not found</h2><p><a href="/research-bot">← Back to research</a></p></div></div></body></html>`);
    return;
  }

  const imageHtml = post.imageUrl
    ? `<img class="hero-img" src="${escapeHtml(post.imageUrl)}" alt="${escapeHtml(post.title)}" />`
    : "";

  const jsonLd = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    author: { "@type": "Person", name: post.author },
    datePublished: post.publishedAt,
    publisher: { "@type": "Organization", name: "WIHY", url: "https://wihy.ai" },
    image: post.imageUrl || undefined,
    description: post.body.slice(0, 160),
  });

  res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(post.title)} — WIHY Research</title>
  <meta name="description" content="${escapeHtml(post.body.slice(0, 160))}">
  <meta name="robots" content="noindex, nofollow">
  <meta property="og:title" content="${escapeHtml(post.title)}">
  <meta property="og:description" content="${escapeHtml(post.body.slice(0, 160))}">
  ${post.imageUrl ? `<meta property="og:image" content="${escapeHtml(post.imageUrl)}">` : ""}
  <meta property="og:type" content="article">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json">${jsonLd}</script>
  ${PAGE_CSS}
</head>
<body>
  <div class="container">
    <a class="back-link" href="/research-bot">← All Research</a>
    <article class="article">
      ${imageHtml}
      <span class="topic-badge">${escapeHtml(post.topic)}</span>
      <h1>${escapeHtml(post.title)}</h1>
      <div class="article-meta">
        <span>@${escapeHtml(post.author)}</span>
        <time>${new Date(post.publishedAt).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}</time>
        ${post.citations.length ? `<span class="cite-count">${post.citations.length} sources</span>` : ""}
      </div>
      <div class="content">${escapeHtml(post.body)}</div>
      ${renderCitations(post.citations)}
    </article>
    <footer>Powered by <a href="https://wihy.ai">WIHY</a> &middot; <a href="https://www.moltbook.com/u/wihyhealthbot">@wihyhealthbot on Moltbook</a></footer>
  </div>
</body>
</html>`);
});

export default router;
