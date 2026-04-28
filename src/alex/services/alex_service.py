"""
alex/services/alex_service.py — ALEX background service.

Runs autonomous SEO cycles: keyword discovery, page generation,
opportunity scanning, analytics ingestion, and content refresh.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

import httpx

from src.alex.config import (
    SERVICES_URL,
    LABAT_URL,
    WIHY_ML_CLIENT_ID,
    WIHY_ML_CLIENT_SECRET,
    OPENAI_API_KEY,
    ALEX_LLM_MODEL,
    ALEX_LLM_TEMPERATURE,
    AUTO_GENERATE_MIN_PRIORITY,
    MAX_PAGES_PER_CYCLE,
    MAX_KEYWORDS_PER_CYCLE,
    PAGE_CTR_REFRESH_THRESHOLD,
    PEER_SERVICES,
    INTERNAL_ADMIN_TOKEN,
    X_BEARER_TOKEN,
    ENABLE_GOOGLE_TRENDS,
    ENABLE_REDDIT_TRENDS,
    ENABLE_X_TRENDS,
    HASHTAG_TIER_HIGH_COUNT,
    HASHTAG_TIER_MID_COUNT,
    HASHTAG_TIER_NICHE_COUNT,
    ALEX_BRAND_SCOPE,
    BRAND_DOMAINS,
    BRAND_DISPLAY_NAMES,
    BRAND_SITE_URLS,
)
from src.labat.services.notify import send_notification

logger = logging.getLogger("alex.service")


class AlexService:
    """Autonomous SEO and content service."""

    def __init__(self):
        self.last_keyword_run: Optional[datetime] = None
        self.last_page_refresh: Optional[datetime] = None
        self.last_opportunity_scan: Optional[datetime] = None
        self.last_analytics_pull: Optional[datetime] = None
        self.last_content_queue_run: Optional[datetime] = None
        self.cycle_stats: Dict[str, int] = {
            "keywords_discovered": 0,
            "pages_generated": 0,
            "pages_refreshed": 0,
            "opportunities_found": 0,
            "analytics_ingested": 0,
        }
        # Keep short runtime memory to avoid repeating the exact same hashtag set.
        self._recent_hashtag_sets: List[List[str]] = []

    # ── HTTP helpers ──────────────────────────────────────────────────────

    def _service_headers(self) -> Dict[str, str]:
        return {
            "X-Client-ID": WIHY_ML_CLIENT_ID,
            "X-Client-Secret": WIHY_ML_CLIENT_SECRET,
            "Content-Type": "application/json",
        }

    async def _services_get(
        self, path: str, params: Optional[Dict[str, str]] = None
    ) -> Any:
        """GET from services.wihy.ai."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{SERVICES_URL}{path}",
                headers=self._service_headers(),
                params=params,
            )
            if r.status_code == 200:
                return r.json()
            logger.warning("services GET %s → %s", path, r.status_code)
            return None

    async def _services_post(self, path: str, data: Dict[str, Any]) -> Any:
        """POST to services.wihy.ai."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{SERVICES_URL}{path}",
                headers=self._service_headers(),
                json=data,
            )
            if r.status_code in (200, 201):
                return r.json()
            logger.warning("services POST %s → %s %s", path, r.status_code, r.text[:200])
            return None

    def _labat_headers(self) -> Dict[str, str]:
        return {
            "X-Admin-Token": INTERNAL_ADMIN_TOKEN,
            "Content-Type": "application/json",
        }

    async def _labat_get(
        self, path: str, params: Optional[Dict[str, str]] = None
    ) -> Any:
        """GET from labat (master agent) — /api/content/* endpoints."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{LABAT_URL}{path}",
                headers=self._labat_headers(),
                params=params,
            )
            if r.status_code == 200:
                return r.json()
            logger.warning("labat GET %s → %s", path, r.status_code)
            return None

    async def _labat_post(self, path: str, data: Dict[str, Any]) -> Any:
        """POST to labat (master agent) — /api/content/* endpoints."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{LABAT_URL}{path}",
                headers=self._labat_headers(),
                json=data,
            )
            if r.status_code in (200, 201):
                return r.json()
            logger.warning("labat POST %s → %s %s", path, r.status_code, r.text[:200])
            return None

    async def _llm_generate(self, system: str, user_msg: str) -> Optional[str]:
        """Call OpenAI to generate content."""
        if not OPENAI_API_KEY:
            logger.error("No OPENAI_API_KEY — cannot generate content")
            return None

        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": ALEX_LLM_MODEL,
                    "temperature": ALEX_LLM_TEMPERATURE,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                },
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            logger.error("LLM call failed: %s %s", r.status_code, r.text[:200])
            return None

    # ── Core Cycles ───────────────────────────────────────────────────────

    async def run_keyword_discovery(self) -> Dict[str, Any]:
        """Discover new keywords from WIHY topics, trends, and user patterns."""
        logger.info("ALEX: Starting keyword discovery cycle")
        result = {"discovered": 0, "saved": 0, "errors": []}

        # Fetch existing keywords to avoid duplicates
        existing = await self._labat_get(
            "/api/content/keywords", params={"limit": "200"}
        )
        existing_words = set()
        if existing and isinstance(existing, list):
            existing_words = {k.get("keyword", "").lower() for k in existing}
        elif existing and isinstance(existing, dict):
            for k in existing.get("data", existing.get("keywords", [])):
                existing_words.add(k.get("keyword", "").lower())

        # Try enriching with external data (optional — may not be available)
        search_queries = await self._services_get(
            "/api/content/search-queries", params={"period": "7d", "limit": "50"}
        )
        scan_trends = await self._services_get(
            "/api/scan/trends", params={"period": "7d", "limit": "30"}
        )

        # Build context — use brand-specific domains when scoped
        _brand = ALEX_BRAND_SCOPE or "wihy"
        _brand_name = BRAND_DISPLAY_NAMES.get(_brand, "WIHY")
        data_context = BRAND_DOMAINS.get(_brand, BRAND_DOMAINS["wihy"]) + "\n"
        if search_queries:
            data_context += f"RECENT SEARCH QUERIES:\n{json.dumps(search_queries, default=str)[:3000]}\n\n"
        if scan_trends:
            data_context += f"SCAN TRENDS:\n{json.dumps(scan_trends, default=str)[:2000]}\n\n"
        if existing_words:
            data_context += f"ALREADY TRACKED KEYWORDS (skip these):\n{', '.join(list(existing_words)[:80])}\n\n"

        system = (
            f"You are ALEX, the SEO keyword discovery engine for {_brand_name}. "
            f"Discover NEW long-tail keywords that {_brand_name} should target for organic search. "
            f"Focus on the brand's core domains listed in the context. "
            "Prioritize 'is X healthy' style queries, ingredient lookups, and comparison queries. "
            "Return ONLY a JSON array of keyword objects. Each object: "
            '{"keyword": "...", "source": "topic_expansion", '
            '"intent": "informational|transactional|navigational", "priority_score": 1-10, '
            '"suggested_page_type": "is_it_healthy|ingredient|alternative|topic"}'
        )
        user_msg = f"Discover up to {MAX_KEYWORDS_PER_CYCLE} new keywords from this data:\n\n{data_context}"

        llm_out = await self._llm_generate(system, user_msg)
        if not llm_out:
            result["errors"].append("LLM generation failed")
            self.last_keyword_run = datetime.utcnow()
            return result

        # Parse keywords from LLM output
        try:
            # Strip markdown code fences if present
            text = llm_out.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            keywords = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("ALEX: Could not parse keyword JSON from LLM")
            result["errors"].append("JSON parse error")
            self.last_keyword_run = datetime.utcnow()
            return result

        # Save new keywords
        for kw in keywords[:MAX_KEYWORDS_PER_CYCLE]:
            word = kw.get("keyword", "").lower().strip()
            if not word or word in existing_words:
                continue
            result["discovered"] += 1
            saved = await self._labat_post("/api/content/keywords", {
                "keyword": word,
                "source": kw.get("source", "auto_discovery"),
                "intent": kw.get("intent", "informational"),
                "priority_score": kw.get("priority_score", 5),
                "suggested_page_type": kw.get("suggested_page_type", "topic"),
                "discovered_by": "alex_background",
            })
            if saved:
                result["saved"] += 1

        self.cycle_stats["keywords_discovered"] += result["discovered"]
        self.last_keyword_run = datetime.utcnow()
        logger.info("ALEX: Keyword discovery complete — %d discovered, %d saved", result["discovered"], result["saved"])
        return result

    async def run_content_queue(self) -> Dict[str, Any]:
        """Process the keyword queue — generate page drafts for high-priority keywords."""
        logger.info("ALEX: Starting content queue processing")
        result = {"processed": 0, "generated": 0, "errors": []}

        # Fetch high-priority pending keywords
        pending = await self._labat_get(
            "/api/content/keywords",
            params={"status": "pending", "min_priority": str(AUTO_GENERATE_MIN_PRIORITY), "limit": str(MAX_PAGES_PER_CYCLE)},
        )

        keywords_list = []
        if isinstance(pending, list):
            keywords_list = pending
        elif isinstance(pending, dict):
            keywords_list = pending.get("data", pending.get("keywords", []))

        if not keywords_list:
            logger.info("ALEX: No high-priority keywords in queue")
            self.last_content_queue_run = datetime.utcnow()
            return result

        # Fetch existing pages for internal linking
        existing_pages = await self._labat_get(
            "/api/content/pages", params={"status": "published", "limit": "30"}
        )

        for kw in keywords_list[:MAX_PAGES_PER_CYCLE]:
            keyword = kw.get("keyword", "")
            page_type = kw.get("suggested_page_type", "topic")
            result["processed"] += 1

            _brand = ALEX_BRAND_SCOPE or "wihy"
            _brand_name = BRAND_DISPLAY_NAMES.get(_brand, "WIHY")
            _brand_site = BRAND_SITE_URLS.get(_brand, "wihy.ai")

            system = (
                f"You are ALEX, the content generation engine for {_brand_name}. "
                "Create a complete, high-quality SEO blog post. "
                "Use Kortney's voice — approachable, knowledgeable, real. Not clinical or corporate. "
                "Return a JSON object with these EXACT fields:\n"
                "- slug (url-safe, lowercase, hyphenated)\n"
                "- title (SEO-optimized headline)\n"
                "- body (full article in markdown — H2s, H3s, lists, bold)\n"
                "- meta_description (155 chars max)\n"
                f"- topic_slug (one of: nutrition, fitness, supplements, fasting, sugar-and-blood-health, alcohol-and-health, processed-foods, protein-and-muscle, hydration)\n"
                "- seo_keywords (array of 8-12 long-tail keyword strings)\n"
                "- faq_items (array of {{question, answer}} — 3-5 items)\n"
                "- key_takeaways (array of 3-5 one-sentence takeaways)\n"
                "- citations (array of {{title, journal, year, url}} — use real PubMed/PMC when possible)\n"
                "- related_posts (array of {{slug, title}} — suggest related articles)\n\n"
                "EVERY POST MUST INCLUDE:\n"
                "- Quick answer (2-3 sentences at top)\n"
                "- Detailed explanation with research citations\n"
                "- 'Why This Matters' section\n"
                "- Better alternatives (when applicable)\n"
                f"- {_brand_name} CTA (link to {_brand_site})\n"
                "- FAQ section (3-5 questions)\n"
            )

            link_context = ""
            if existing_pages:
                pages_data = existing_pages if isinstance(existing_pages, list) else existing_pages.get("data", [])
                slugs = [p.get("slug", "") for p in pages_data[:20] if p.get("slug")]
                if slugs:
                    link_context = f"\nEXISTING PAGES FOR INTERNAL LINKING:\n{', '.join(slugs)}\n"

            user_msg = (
                f"Create a {page_type} page for the keyword: '{keyword}'\n"
                f"Intent: {kw.get('intent', 'informational')}\n"
                f"{link_context}"
            )

            llm_out = await self._llm_generate(system, user_msg)
            if not llm_out:
                result["errors"].append(f"LLM failed for keyword: {keyword}")
                continue

            # Parse page draft
            try:
                text = llm_out.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    text = text.rsplit("```", 1)[0]
                page_data = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("ALEX: Could not parse page JSON for keyword: %s", keyword)
                result["errors"].append(f"JSON parse error for: {keyword}")
                continue

            # Save the draft
            page_data["status"] = "draft"
            page_data["generated_by"] = "alex_background"
            page_data["source_keyword"] = keyword
            page_data["generated_at"] = datetime.utcnow().isoformat()
            page_data.setdefault("author", "Kortney")
            page_data.setdefault("brand", _brand)
            page_data.setdefault("created_at", datetime.utcnow().isoformat())
            # Word count from body
            body_text = page_data.get("body", "")
            page_data.setdefault("word_count", len(body_text.split()) if body_text else 0)

            saved = await self._labat_post("/api/content/pages", page_data)
            if saved:
                result["generated"] += 1
                # Mark keyword as processed
                await self._labat_post(
                    f"/api/content/keywords/{kw.get('id', '')}/status",
                    {"status": "page_generated"},
                )

        self.cycle_stats["pages_generated"] += result["generated"]
        self.last_content_queue_run = datetime.utcnow()
        logger.info("ALEX: Content queue — %d processed, %d generated", result["processed"], result["generated"])
        return result

    async def run_page_refresh(self) -> Dict[str, Any]:
        """Check existing pages and refresh older drafts."""
        logger.info("ALEX: Starting page refresh cycle")
        result = {"checked": 0, "refreshed": 0, "errors": []}

        # Try analytics from services (may not be available yet)
        analytics = await self._services_get(
            "/api/content/analytics",
            params={"period": "30d", "limit": "50", "sort": "ctr_asc"},
        )

        if analytics:
            pages_data = analytics if isinstance(analytics, list) else analytics.get("data", [])
        else:
            # Fall back to refreshing existing draft pages from LABAT
            all_pages = await self._labat_get(
                "/api/content/pages", params={"status": "draft", "limit": "10"}
            )
            pages_data = all_pages if isinstance(all_pages, list) else []

        if not pages_data:
            logger.info("ALEX: No pages available for refresh")
            self.last_page_refresh = datetime.utcnow()
            return result

        for page in pages_data:
            ctr = page.get("ctr", 0.0)
            result["checked"] += 1

            # Skip if analytics present and CTR is fine
            if analytics and ctr >= PAGE_CTR_REFRESH_THRESHOLD:
                continue

            slug = page.get("slug", "")
            title = page.get("title", slug)

            # Fetch the page content
            page_content = await self._labat_get(f"/api/content/pages/{slug}")
            if not page_content:
                continue

            system = (
                "You are ALEX. A blog post needs improvement. "
                "Analyze it and suggest improvements. Return JSON with: "
                "new_title, new_meta_description, content_additions (markdown to append to body), "
                "new_faq_items (additional FAQ items as [{question, answer}]), improvement_notes."
            )
            user_msg = (
                f"Page: {title}\nSlug: {slug}\n"
                f"Current CTR: {ctr:.4f}\nImpressions: {page.get('impressions', 'unknown')}\n"
                f"Current content:\n{json.dumps(page_content, default=str)[:4000]}"
            )

            llm_out = await self._llm_generate(system, user_msg)
            if not llm_out:
                result["errors"].append(f"LLM failed for refresh: {slug}")
                continue

            try:
                text = llm_out.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    text = text.rsplit("```", 1)[0]
                refresh_data = json.loads(text)
            except json.JSONDecodeError:
                result["errors"].append(f"JSON parse error on refresh: {slug}")
                continue

            refresh_data["refreshed_by"] = "alex_background"
            refresh_data["refreshed_at"] = datetime.utcnow().isoformat()
            refresh_data["previous_ctr"] = ctr

            updated = await self._labat_post(f"/api/content/pages/{slug}/refresh", refresh_data)
            if updated:
                result["refreshed"] += 1

        self.cycle_stats["pages_refreshed"] += result["refreshed"]
        self.last_page_refresh = datetime.utcnow()
        logger.info("ALEX: Page refresh — %d checked, %d refreshed", result["checked"], result["refreshed"])
        return result

    async def run_opportunity_scan(self) -> Dict[str, Any]:
        """Scan for speaking, podcast, and partnership opportunities."""
        logger.info("ALEX: Starting opportunity scan")
        result = {"found": 0, "saved": 0, "errors": []}

        # Fetch existing opportunities to avoid duplicates
        existing = await self._labat_get(
            "/api/content/opportunities", params={"limit": "100"}
        )
        existing_titles = set()
        if existing:
            opps = existing if isinstance(existing, list) else existing.get("data", [])
            existing_titles = {o.get("title", "").lower() for o in opps}

        # Fetch recent search queries mentioning speaking/events
        queries = await self._services_get(
            "/api/content/search-queries",
            params={"period": "30d", "limit": "20", "filter": "speaking,conference,event,podcast"},
        )

        _brand = ALEX_BRAND_SCOPE or "wihy"
        _brand_name = BRAND_DISPLAY_NAMES.get(_brand, "WIHY")

        system = (
            f"You are ALEX, scanning for speaking and partnership opportunities for Kortney ({_brand_name} founder). "
            f"Based on {_brand_name}'s mission (health for underserved communities, mobile app, book, school wellness), "
            "suggest realistic speaking/partnership opportunities. "
            "Return a JSON array of opportunity objects: "
            '{"title": "...", "type": "conference|podcast|school|corporate|panel|church|university|grant", '
            '"organization": "...", "fit_score": 1-10, "suggested_talk_title": "...", '
            '"pitch_summary": "2-3 sentences", "notes": "..."}'
        )

        data_context = ""
        if queries:
            data_context += f"Related search interest:\n{json.dumps(queries, default=str)[:2000]}\n"
        if existing_titles:
            data_context += f"Already tracked (skip): {', '.join(list(existing_titles)[:30])}\n"

        user_msg = (
            "Identify 5 new speaking/partnership opportunities based on current health and wellness trends. "
            "Focus on: school wellness, corporate wellness, church health ministries, health tech conferences, "
            "nutrition podcasts, community health events.\n\n"
            f"{data_context}"
        )

        llm_out = await self._llm_generate(system, user_msg)
        if not llm_out:
            result["errors"].append("LLM generation failed")
            self.last_opportunity_scan = datetime.utcnow()
            return result

        try:
            text = llm_out.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            opportunities = json.loads(text)
        except json.JSONDecodeError:
            result["errors"].append("JSON parse error")
            self.last_opportunity_scan = datetime.utcnow()
            return result

        for opp in opportunities:
            title = opp.get("title", "").strip()
            if not title or title.lower() in existing_titles:
                continue
            result["found"] += 1

            saved = await self._labat_post("/api/content/opportunities", {
                "title": title,
                "type": opp.get("type", "conference"),
                "organization": opp.get("organization", ""),
                "fit_score": opp.get("fit_score", 5),
                "suggested_talk_title": opp.get("suggested_talk_title", ""),
                "pitch_summary": opp.get("pitch_summary", ""),
                "notes": opp.get("notes", ""),
                "status": "new",
                "discovered_by": "alex_background",
                "discovered_at": datetime.utcnow().isoformat(),
            })
            if saved:
                result["saved"] += 1

        self.cycle_stats["opportunities_found"] += result["found"]
        self.last_opportunity_scan = datetime.utcnow()
        logger.info("ALEX: Opportunity scan — %d found, %d saved", result["found"], result["saved"])
        return result

    async def run_analytics_ingestion(self) -> Dict[str, Any]:
        """Pull page performance analytics and count existing content assets."""
        logger.info("ALEX: Starting analytics ingestion")
        result = {"pages_checked": 0, "metrics_stored": 0, "errors": []}

        # Try external analytics (may not be available yet)
        analytics = await self._services_get(
            "/api/content/analytics", params={"period": "24h", "limit": "100"}
        )

        if analytics:
            pages_data = analytics if isinstance(analytics, list) else analytics.get("data", [])
            result["pages_checked"] = len(pages_data)

            total_impressions = sum(p.get("impressions", 0) for p in pages_data)
            total_clicks = sum(p.get("clicks", 0) for p in pages_data)
            avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0

            logger.info(
                "ALEX: Analytics ingestion — %d pages, %d impressions, %.2f%% CTR",
                len(pages_data), total_impressions, avg_ctr * 100,
            )
        else:
            # Count content assets from LABAT as a basic metric
            keywords = await self._labat_get("/api/content/keywords", params={"limit": "200"})
            pages = await self._labat_get("/api/content/pages", params={"limit": "200"})
            kw_count = len(keywords) if isinstance(keywords, list) else 0
            pg_count = len(pages) if isinstance(pages, list) else 0
            result["pages_checked"] = pg_count
            logger.info(
                "ALEX: Analytics — no external source; asset count: %d keywords, %d pages",
                kw_count, pg_count,
            )

        self.cycle_stats["analytics_ingested"] += 1
        self.last_analytics_pull = datetime.utcnow()
        return result

    async def get_realtime_signals(
        self,
        query: str,
        brand: str = "wihy",
        limit: int = 8,
    ) -> Dict[str, Any]:
        """Return near-real-time hashtag and keyword signals for content generation.

        Sources: keyword queue, recent search queries, and scan trends.
        """
        cap = max(3, min(limit, 20))
        query_l = (query or "").lower()
        brand_l = self._normalize_brand(brand)

        keywords = await self._labat_get(
            "/api/content/keywords",
            params={"limit": "120", "brand": brand_l},
        )
        search_queries = await self._services_get(
            "/api/content/search-queries",
            params={"period": "24h", "limit": "40"},
        )
        scan_trends = await self._services_get(
            "/api/scan/trends",
            params={"period": "24h", "limit": "30"},
        )
        google_suggestions = await self._fetch_google_query_suggestions(query) if ENABLE_GOOGLE_TRENDS else []
        google_trends = await self._fetch_google_trending_terms() if ENABLE_GOOGLE_TRENDS else []
        reddit_terms = await self._fetch_reddit_trending_terms(query) if ENABLE_REDDIT_TRENDS else []
        x_terms = await self._fetch_x_trending_terms(query) if ENABLE_X_TRENDS else []

        keyword_items = keywords if isinstance(keywords, list) else (keywords or {}).get("data", [])
        query_items = (
            search_queries
            if isinstance(search_queries, list)
            else (search_queries or {}).get("data", [])
        )
        trend_items = (
            scan_trends if isinstance(scan_trends, list) else (scan_trends or {}).get("data", [])
        )

        scored_terms: List[tuple[str, float, str]] = []

        for k in keyword_items:
            word = (k.get("keyword") or "").strip().lower()
            if not word:
                continue
            score = float(k.get("priority_score") or 5)
            if query_l and any(part in word for part in query_l.split() if len(part) > 3):
                score += 2.0
            scored_terms.append((word, score, "keyword"))

        for q in query_items:
            text = (q.get("query") or q.get("term") or q.get("text") or "").strip().lower()
            if not text:
                continue
            score = float(q.get("count") or q.get("volume") or 2)
            if query_l and any(part in text for part in query_l.split() if len(part) > 3):
                score += 2.5
            scored_terms.append((text, score, "search_query"))

        for t in trend_items:
            text = (t.get("term") or t.get("query") or t.get("name") or "").strip().lower()
            if not text:
                continue
            score = float(t.get("score") or t.get("count") or t.get("mentions") or 3)
            if query_l and any(part in text for part in query_l.split() if len(part) > 3):
                score += 2.5
            scored_terms.append((text, score, "scan_trend"))

        for suggestion in google_suggestions:
            text = suggestion.strip().lower()
            if not text:
                continue
            score = 4.0
            if query_l and any(part in text for part in query_l.split() if len(part) > 3):
                score += 2.5
            scored_terms.append((text, score, "google_suggest"))

        health_focus_words = {
            "health", "healthy", "nutrition", "food", "diet", "obesity", "weight", "diabetes",
            "protein", "sugar", "snack", "fitness", "wellness", "ingredient", "processed", "label",
            "vitamin", "supplement", "exercise", "grocery", "school", "kids", "child", "community",
        }

        for term in google_trends:
            text = term.strip().lower()
            if not text:
                continue
            score = 2.0
            has_health_word = any(w in text for w in health_focus_words)
            has_query_overlap = query_l and any(part in text for part in query_l.split() if len(part) > 3)
            if has_health_word:
                score += 2.5
            if has_query_overlap:
                score += 3.0
            if brand_l in ("communitygroceries", "wihy", "vowels") and any(w in text for w in ("food", "health", "school", "kids", "nutrition", "ingredient", "label")):
                score += 1.5
            if has_health_word or has_query_overlap:
                scored_terms.append((text, score, "google_trends"))

        # Step 1: detect trend from Reddit and X, then score for WIHY relevance.
        for term in reddit_terms:
            text = term.strip().lower()
            if not text:
                continue
            score = 2.5
            if any(w in text for w in health_focus_words):
                score += 2.5
            if query_l and any(part in text for part in query_l.split() if len(part) > 3):
                score += 2.0
            scored_terms.append((text, score, "reddit"))

        for term in x_terms:
            text = term.strip().lower()
            if not text:
                continue
            score = 2.5
            if any(w in text for w in health_focus_words):
                score += 2.5
            if query_l and any(part in text for part in query_l.split() if len(part) > 3):
                score += 2.5
            scored_terms.append((text, score, "x_trends"))

        seen = set()
        ranked: List[Dict[str, Any]] = []
        for term, score, source in sorted(scored_terms, key=lambda x: x[1], reverse=True):
            normalized = " ".join(term.split())
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ranked.append({"term": normalized, "score": round(score, 2), "source": source})
            if len(ranked) >= cap:
                break

        def to_hashtag(text: str) -> str:
            compact = "".join(ch for ch in text.title() if ch.isalnum())
            return f"#{compact[:40]}" if compact else ""

        # Step 2: translate trend language to WIHY context before hashtag conversion.
        translated_terms = [self._translate_trend_to_wihy_context(item["term"], query_l) for item in ranked]

        hashtags = [to_hashtag(term) for term in translated_terms]
        hashtags = [h for h in hashtags if h]

        brand_tags = {
            "wihy": ["#WIHY", "#WhatIsHealthy"],
            "communitygroceries": ["#CommunityGroceries", "#FoodAccess"],
            "vowels": ["#Vowels", "#VowelsOrg", "#WhatIsHealthy", "#NutritionEducation"],
            "snackingwell": ["#SnackingWell", "#SmartSnacking"],
        }

        ordered = []
        for h in brand_tags.get(brand_l, ["#WIHY"]):
            if h not in ordered:
                ordered.append(h)
        for h in hashtags:
            if h not in ordered:
                ordered.append(h)

        # Step 3: build 3-tier hashtag stack (reach + targeting).
        tier_stack = self._build_hashtag_tier_stack(
            ranked_terms=translated_terms,
            generated_hashtags=ordered,
            brand=brand_l,
        )
        # Respect anti-repetition: rotate if identical to recent selections.
        final_hashtags = self._select_rotated_hashtag_set(tier_stack)

        return {
            "query": query,
            "brand": brand_l,
            "generated_at": datetime.utcnow().isoformat(),
            "top_signals": ranked,
            "hashtag_tiers": tier_stack,
            "recommended_hashtags": final_hashtags[: max(cap, 12)],
            "recommended_hashtag_count": len(final_hashtags),
            "sources": {
                "keywords": len(keyword_items),
                "search_queries": len(query_items),
                "scan_trends": len(trend_items),
                "google_suggest": len(google_suggestions),
                "google_trends": len(google_trends),
                "reddit": len(reddit_terms),
                "x_trends": len(x_terms),
            },
        }

    def _normalize_brand(self, brand: Optional[str]) -> str:
        """Normalize known brand aliases into canonical keys."""
        b = (brand or ALEX_BRAND_SCOPE or "wihy").strip().lower()
        aliases = {
            "wihy": "wihy",
            "trinity": "vowels",
            "whatishealthy": "vowels",
            "what-is-healthy": "vowels",
            "book": "vowels",
            "vowelsbook": "vowels",
            "communitygroceries": "communitygroceries",
            "community-groceries": "communitygroceries",
            "community groceries": "communitygroceries",
            "cg": "communitygroceries",
            "vowels": "vowels",
            "snackingwell": "snackingwell",
            "childrennutrition": "childrennutrition",
            "children-nutrition": "childrennutrition",
            "cn": "childrennutrition",
            "parentingwithchrist": "parentingwithchrist",
            "parenting-with-christ": "parentingwithchrist",
            "pwc": "parentingwithchrist",
        }
        return aliases.get(b, "wihy")

    def _translate_trend_to_wihy_context(self, term: str, query_l: str) -> str:
        """Translate raw trend terms to WIHY health/nutrition framing."""
        t = (term or "").strip().lower()
        if not t:
            return term

        mapping = [
            ("high protein", "high protein healthy snacks"),
            ("protein snack", "high protein healthy snacks"),
            ("weight loss", "healthy weight management"),
            ("meal prep", "whole food meal prep"),
            ("food labels", "food label literacy"),
            ("ingredient", "ingredient awareness"),
            ("processed", "ultra processed food awareness"),
        ]
        for needle, replacement in mapping:
            if needle in t:
                t = t.replace(needle, replacement)

        if query_l and query_l not in t and any(w in query_l for w in ("health", "food", "nutrition", "label", "ingredient")):
            t = f"{t} {query_l}".strip()
        return t

    def _build_hashtag_tier_stack(
        self,
        ranked_terms: List[str],
        generated_hashtags: List[str],
        brand: str,
    ) -> Dict[str, List[str]]:
        """Create high/mid/niche hashtag stack for distribution quality."""
        high_pool = [
            "#Health", "#Nutrition", "#Fitness", "#Wellness", "#HealthyLifestyle",
            "#HealthyFood", "#Food", "#HealthTips", "#RealFood", "#HealthAwareness",
        ]
        mid_pool = [
            "#FoodEducation", "#IngredientAwareness", "#HealthyFoodChoices", "#FoodLabelLiteracy",
            "#NutritionEducation", "#WholeFoods", "#HealthyHabits", "#CleanEatingTips",
            "#MetabolicHealth", "#FamilyNutrition", "#SmartGroceryChoices",
        ]
        niche_brand_pool = {
            "wihy": ["#WIHY", "#WhatIsHealthy", "#FoodTruth", "#DecodeFoodLabels", "#EvidenceFirstHealth"],
            "communitygroceries": ["#CommunityGroceries", "#CommunityGroceriesHealth", "#FoodAccess", "#HealthyNeighborhoods", "#SmartShopping"],
            "vowels": ["#Vowels", "#VowelsOrg", "#WhatIsHealthy", "#NutritionEducation", "#FoodLabelLiteracy"],
            "snackingwell": ["#SnackingWell", "#SmartSnacking", "#HealthySnacks", "#SnackBetter", "#FoodTruth"],
        }

        # Derive additional mid/niche tags from top translated terms.
        derived = []
        for term in ranked_terms[:20]:
            cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", (term or "").strip())
            cleaned = " ".join(cleaned.split())
            if len(cleaned) < 4:
                continue
            tag = "#" + "".join(word.capitalize() for word in cleaned.split()[:4])
            if 2 < len(tag) <= 40:
                derived.append(tag)

        niche_pool = niche_brand_pool.get(brand, ["#WIHY", "#FoodTruth"]) + derived

        def pick_unique(pool: List[str], count: int, used: set) -> List[str]:
            chosen: List[str] = []
            for item in pool:
                if item not in used:
                    chosen.append(item)
                    used.add(item)
                if len(chosen) >= count:
                    break
            return chosen

        used: set = set()
        high = pick_unique(high_pool, max(1, HASHTAG_TIER_HIGH_COUNT), used)
        mid = pick_unique(mid_pool + generated_hashtags, max(1, HASHTAG_TIER_MID_COUNT), used)
        niche = pick_unique(niche_pool + generated_hashtags, max(1, HASHTAG_TIER_NICHE_COUNT), used)

        return {
            "high_volume": high,
            "mid_volume": mid,
            "niche_brand": niche,
        }

    def _select_rotated_hashtag_set(self, tier_stack: Dict[str, List[str]]) -> List[str]:
        """Flatten tier stack and rotate to avoid repeated identical sets."""
        combined = tier_stack.get("high_volume", []) + tier_stack.get("mid_volume", []) + tier_stack.get("niche_brand", [])
        deduped: List[str] = []
        seen = set()
        for h in combined:
            if h not in seen:
                deduped.append(h)
                seen.add(h)

        # Rotate by one if identical to last set to reduce repeat usage.
        if self._recent_hashtag_sets and deduped == self._recent_hashtag_sets[-1] and len(deduped) > 1:
            deduped = deduped[1:] + deduped[:1]

        self._recent_hashtag_sets.append(deduped)
        if len(self._recent_hashtag_sets) > 20:
            self._recent_hashtag_sets = self._recent_hashtag_sets[-20:]
        return deduped

    async def _fetch_reddit_trending_terms(self, query: str) -> List[str]:
        """Fetch trending terms from Reddit search results (no auth required)."""
        if not query or not query.strip():
            return []
        url = "https://www.reddit.com/search.json"
        params = {"q": query, "sort": "relevance", "limit": "20", "t": "day"}
        headers = {"User-Agent": "wihy-alex/1.0"}
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(url, params=params, headers=headers)
                if r.status_code != 200:
                    logger.warning("ALEX: Reddit trends returned %s", r.status_code)
                    return []
                payload = r.json()
            posts = (((payload or {}).get("data") or {}).get("children") or [])
            terms: List[str] = []
            for p in posts:
                data = (p or {}).get("data") or {}
                title = (data.get("title") or "").strip()
                if title:
                    terms.append(title)
            return terms[:20]
        except Exception as e:
            logger.warning("ALEX: Failed to fetch Reddit trends: %s", e)
            return []

    async def _fetch_x_trending_terms(self, query: str) -> List[str]:
        """Fetch trend-adjacent terms from X recent search when token is available."""
        if not X_BEARER_TOKEN or not query or not query.strip():
            return []
        url = "https://api.twitter.com/2/tweets/search/recent"
        params = {
            "query": f"({query}) lang:en -is:retweet",
            "max_results": "20",
            "tweet.fields": "public_metrics,text",
        }
        headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(url, params=params, headers=headers)
                if r.status_code != 200:
                    logger.warning("ALEX: X trends returned %s", r.status_code)
                    return []
                payload = r.json()
            items = (payload or {}).get("data") or []
            terms: List[str] = []
            for tweet in items:
                text = (tweet.get("text") or "").strip().lower()
                if not text:
                    continue
                # Pull candidate phrases from hashtags first, fallback to short phrases.
                hash_terms = re.findall(r"#([A-Za-z0-9_]{3,30})", text)
                if hash_terms:
                    terms.extend([h.replace("_", " ") for h in hash_terms])
                    continue
                words = [w for w in re.split(r"\W+", text) if len(w) > 3]
                if words:
                    terms.append(" ".join(words[:4]))
            return terms[:20]
        except Exception as e:
            logger.warning("ALEX: Failed to fetch X trends: %s", e)
            return []

    async def _fetch_google_query_suggestions(self, query: str) -> List[str]:
        """Fetch query-specific trending suggestions from Google suggest API."""
        if not query or not query.strip():
            return []

        url = "https://suggestqueries.google.com/complete/search"
        params = {
            "client": "firefox",
            "q": query,
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    logger.warning("ALEX: Google suggest returned %s", r.status_code)
                    return []
                payload = r.json()

            suggestions: List[str] = []
            if isinstance(payload, list) and len(payload) > 1:
                second = payload[1]
                if isinstance(second, list):
                    suggestions = [str(x).strip() for x in second if str(x).strip()]
                elif isinstance(second, dict):
                    vals = second.get("value", [])
                    suggestions = [str(x).strip() for x in vals if str(x).strip()]
            return suggestions[:20]
        except Exception as e:
            logger.warning("ALEX: Failed to fetch Google suggestions: %s", e)
            return []

    async def _fetch_google_trending_terms(self) -> List[str]:
        """Fetch current US trending terms from Google's public RSS feed."""
        url = "https://trends.google.com/trending/rss?geo=US"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    logger.warning("ALEX: Google Trends RSS returned %s", r.status_code)
                    return []

            root = ElementTree.fromstring(r.text)
            # RSS item titles are under channel/item/title
            titles: List[str] = []
            for item in root.findall("./channel/item"):
                title_node = item.find("title")
                if title_node is None:
                    continue
                text = (title_node.text or "").strip()
                if text:
                    titles.append(text)
            return titles[:50]
        except Exception as e:
            logger.warning("ALEX: Failed to fetch Google Trends RSS: %s", e)
            return []

    # ── Status / Health ───────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Check health of dependent services."""
        results = {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, cfg in PEER_SERVICES.items():
                try:
                    r = await client.get(
                        cfg["url"] + cfg["health_endpoint"],
                        headers={"X-Admin-Token": INTERNAL_ADMIN_TOKEN},
                    )
                    results[name] = {
                        "status": "healthy" if r.status_code == 200 else "unhealthy",
                        "response_time_ms": round(r.elapsed.total_seconds() * 1000),
                    }
                except Exception as e:
                    results[name] = {"status": "error", "error": str(e)}
        return results

    def get_status(self) -> Dict[str, Any]:
        """Return current ALEX status and stats."""
        return {
            "agent": "ALEX",
            "version": "1.0.0",
            "status": "running",
            "last_runs": {
                "keyword_discovery": self.last_keyword_run.isoformat() if self.last_keyword_run else None,
                "content_queue": self.last_content_queue_run.isoformat() if self.last_content_queue_run else None,
                "page_refresh": self.last_page_refresh.isoformat() if self.last_page_refresh else None,
                "opportunity_scan": self.last_opportunity_scan.isoformat() if self.last_opportunity_scan else None,
                "analytics_ingestion": self.last_analytics_pull.isoformat() if self.last_analytics_pull else None,
            },
            "cycle_stats": self.cycle_stats,
        }

    async def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive ALEX status report (email-friendly flat structure)."""
        health = await self.health_check()
        stats = self.cycle_stats

        # Book lead performance from LABAT
        book_leads: Dict[str, Any] = {}
        try:
            raw = await self._labat_get("/api/labat/leads/sync/report", params={"days": "7"})
            if raw:
                book_leads = raw
        except Exception as _bl_err:
            logger.warning("Could not fetch book leads report: %s", _bl_err)

        return {
            "agent": "ALEX",
            "generated_at": datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC"),
            "keywords_discovered": stats.get("keywords_discovered", 0),
            "pages_generated": stats.get("pages_generated", 0),
            "pages_refreshed": stats.get("pages_refreshed", 0),
            "opportunities_found": stats.get("opportunities_found", 0),
            "analytics_ingested": stats.get("analytics_ingested", 0),
            "last_runs": {
                k: (v.strftime("%b %d %H:%M UTC") if isinstance(v, datetime) else v)
                for k, v in {
                    "keyword_discovery": self.last_keyword_run,
                    "content_queue": self.last_content_queue_run,
                    "page_refresh": self.last_page_refresh,
                    "opportunity_scan": self.last_opportunity_scan,
                    "analytics_ingestion": self.last_analytics_pull,
                }.items()
                if v is not None
            },
            "service_health": {
                name: f"{info.get('status', '?')} ({info.get('response_time_ms', '?')}ms)"
                for name, info in health.items()
            },
            "book_leads": book_leads,
        }

    async def send_report(self) -> bool:
        """Send report via auth notification service."""
        report = await self.generate_report()
        bl = report.get("book_leads") or {}
        engagement = bl.get("email_engagement") or {}
        book_summary = (
            f"Book leads: {bl.get('total_book_leads', '?')} total, "
            f"{bl.get('new_leads_last_7d', bl.get('new_leads_last_30d', '?'))} new (7d), "
            f"{bl.get('total_purchased', '?')} purchased | "
            f"Email open {engagement.get('open_rate_pct', '?')}% "
            f"click {engagement.get('click_rate_pct', '?')}%"
        )
        return await send_notification(
            agent="alex",
            severity="info",
            title="ALEX Periodic Report",
            message=(
                f"Keywords: {self.cycle_stats['keywords_discovered']}, "
                f"Pages: {self.cycle_stats['pages_generated']}, "
                f"Refreshed: {self.cycle_stats['pages_refreshed']}, "
                f"Opportunities: {self.cycle_stats['opportunities_found']} | "
                f"{book_summary}"
            ),
            service="alex-seo",
            details=report,
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[AlexService] = None


def get_alex_service() -> AlexService:
    """Return singleton AlexService."""
    global _instance
    if _instance is None:
        _instance = AlexService()
    return _instance
