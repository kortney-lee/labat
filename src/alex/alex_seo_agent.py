"""ALEX agent — AI Language Executing X.

Knowledge execution and expansion agent for WIHY.
Turns book content, app data, user questions, and search intent into
scalable SEO pages, authority assets, speaking opportunities, and
monetizable outputs.

ALEX is the builder and expander — not the strategist or overseer.
"""

import json
import logging
from typing import Dict, List, Any, Optional

# from src.agents.base import BaseAgent, AgentAction  # removed (not in this repo)
# from src.agents import data_client  # removed (not in this repo)
# from src.agents.schemas import SuggestedAction  # removed (not in this repo)

logger = logging.getLogger(__name__)


class AlexSEO(BaseAgent):
    name = "alex_seo"
    description = (
        "Knowledge execution engine — turns ideas, data, and user demand into "
        "SEO pages, content drafts, keyword strategies, speaking pitches, and "
        "authority assets that grow WIHY."
    )

    llm_provider = "gemini"
    llm_model = "gemini-2.5-pro"
    llm_max_tokens = 3000
    llm_temperature = 0.5

    # ── Actions ─────────────────────────────────────────────────────────

    def get_actions(self) -> List[AgentAction]:
        return [
            AgentAction(
                name="create_page_draft",
                description=(
                    "Create an SEO page draft. "
                    "Fields: title, slug, page_type (is_it_healthy / ingredient / "
                    "alternative / topic / speaking / schools / business / book / app), "
                    "summary, content, meta_description, keywords (comma-sep)"
                ),
                target="services",
                method="POST",
                path_template="/api/content/pages",
                required_fields=["title", "slug", "page_type", "summary", "content", "meta_description"],
                summary_template="Created page draft: {title}",
            ),
            AgentAction(
                name="save_keyword",
                description=(
                    "Store a discovered keyword with metadata. "
                    "Fields: keyword, source (search_console / trends / user_query / scan / book), "
                    "intent (informational / transactional / navigational), "
                    "priority_score (1-10)"
                ),
                target="services",
                method="POST",
                path_template="/api/content/keywords",
                required_fields=["keyword", "source", "intent", "priority_score"],
                summary_template="Saved keyword: {keyword} (priority {priority_score})",
            ),
            AgentAction(
                name="save_opportunity",
                description=(
                    "Save a speaking/partnership opportunity. "
                    "Fields: title, type (conference / podcast / school / corporate / "
                    "panel / church / university / grant), organization, url (optional), "
                    "deadline (optional), fit_score (1-10), notes"
                ),
                target="services",
                method="POST",
                path_template="/api/content/opportunities",
                required_fields=["title", "type", "organization", "fit_score"],
                summary_template="Saved opportunity: {title} (fit {fit_score}/10)",
            ),
        ]

    # ── Data Fetching ───────────────────────────────────────────────────

    def get_data_tasks(self, user_id: str, jwt: Optional[str], message: str) -> Dict[str, Any]:
        msg = message.lower()
        tasks: Dict[str, Any] = {}

        # Always fetch existing pages and keywords for context
        tasks["existing_pages"] = data_client.fetch_services(
            "/api/content/pages",
            params={"limit": "20", "status": "published"},
            user_jwt=jwt,
        )
        tasks["keyword_queue"] = data_client.fetch_services(
            "/api/content/keywords",
            params={"limit": "20", "status": "pending"},
            user_jwt=jwt,
        )

        # If the query mentions page performance, analytics, or weak pages
        if any(w in msg for w in (
            "performance", "analytics", "impressions", "clicks",
            "ctr", "weak", "underperforming", "improve", "refresh",
        )):
            tasks["page_analytics"] = data_client.fetch_services(
                "/api/content/analytics",
                params={"period": "30d", "limit": "20"},
                user_jwt=jwt,
            )

        # If the query is about speaking/opportunities
        if any(w in msg for w in (
            "speaking", "opportunity", "conference", "podcast",
            "pitch", "partnership", "event", "talk",
        )):
            tasks["opportunities"] = data_client.fetch_services(
                "/api/content/opportunities",
                params={"limit": "20", "status": "active"},
                user_jwt=jwt,
            )

        # If the query is about user questions or search intent
        if any(w in msg for w in (
            "user question", "search", "query", "popular",
            "trending", "top question", "what are people asking",
        )):
            tasks["search_queries"] = data_client.fetch_services(
                "/api/content/search-queries",
                params={"period": "7d", "limit": "30"},
                user_jwt=jwt,
            )

        # If content from the book is mentioned
        if any(w in msg for w in ("book", "chapter", "excerpt", "manuscript")):
            tasks["book_content"] = data_client.fetch_services(
                "/api/content/book-sections",
                params={"limit": "10"},
                user_jwt=jwt,
            )

        # Scan behavior data for product/ingredient pages
        if any(w in msg for w in (
            "scan", "ingredient", "product", "barcode",
            "popular scan", "top scans",
        )):
            tasks["scan_trends"] = data_client.fetch_services(
                "/api/scan/trends",
                params={"period": "7d", "limit": "20"},
                user_jwt=jwt,
            )

        return tasks

    # ── System Prompt ───────────────────────────────────────────────────

    def build_system_prompt(self, context: Dict[str, Any], message: str) -> str:
        prompt = """You are ALEX — AI Language Executing X — the knowledge execution and expansion agent for WIHY.

IDENTITY:
- You are the builder and expander. You turn knowledge into scalable digital assets.
- You work alongside other agents:
  - Amanda handles nutrition validation and health guardrails.
  - LABAT handles growth strategy and prioritization.
  - Shania handles engagement and audience interaction.
  - Otaku Master oversees all agents.
- You do NOT make strategic prioritization decisions — LABAT does that.
- You do NOT validate nutrition claims — Amanda does that.
- You execute: pages, content, keywords, pitches, and authority assets.

CORE CAPABILITIES:
1. Knowledge Execution — transform book content, app data, user questions into structured outputs.
2. SEO Management — keyword discovery, clustering, intent mapping, title/meta generation, content drafts.
3. Dynamic Page Generation — create and maintain SEO-friendly page content.
4. Speaking Opportunity Engine — find, score, and draft pitches for speaking engagements.
5. Authority Building — speaker pages, about pages, mission pages, media kit content.
6. Content Generation — from one idea, produce page draft, FAQ set, headlines, social hooks, CTAs.

PAGE TYPES YOU CREATE:
- /is-it-healthy/[slug] — health assessments of foods, products, habits
- /ingredients/[slug] — deep dives on specific ingredients
- /alternatives/[slug] — healthier alternatives to common products
- /topics/[slug] — educational content on health topics
- /speaking — speaking page and talk topics
- /schools — school wellness offering
- /business — business wellness offering
- /book — book page
- /app — app page

EVERY PAGE MUST INCLUDE:
- SEO title and meta description
- H1 heading
- Quick answer (2-3 sentences)
- Detailed explanation
- "Why this matters" section
- Better alternatives (when applicable)
- WIHY CTA
- Community Groceries CTA (when relevant to grocery/meal planning)
- Related links
- FAQ section (3-5 questions)
- Schema markup data (JSON-LD)

CONTENT RULES:
- Never create thin or low-quality content.
- Never invent unsupported medical claims — flag anything nutrition-sensitive for Amanda review.
- Every page must support a conversion path (app signup, premium, speaking inquiry, etc.).
- Use Kortney's voice — approachable, knowledgeable, real. Not clinical or corporate.
- Internal linking: always suggest 3-5 related pages.
- Include structured FAQ schema for every answer page.

KEYWORD STRATEGY:
- Prioritize keywords with clear search intent.
- Cluster related keywords into topic groups.
- Map intent: informational → educational pages, transactional → product/app pages.
- Score keywords by: volume potential, relevance to WIHY, conversion potential.

SPEAKING OPPORTUNITIES:
- Types: conferences, school wellness events, corporate wellness, podcasts, panels, churches, universities, grants.
- Score fit (1-10) based on: audience alignment, reach, speaking fee potential, brand building value.
- Draft pitches that lead with Kortney's mission and real results.
- Suggest specific talk titles and descriptions.

CONVERSION PATHS (every output should connect to at least one):
- WIHY app signup (free)
- WIHY premium upgrade
- Family plan
- Coach plan
- Speaking inquiry
- School inquiry
- Business inquiry
- Book interest
- Community Groceries (grocery planning flow)

OUTPUT FORMAT:
- When creating page drafts, use clear markdown with designated sections.
- When reporting keywords, include: keyword, source, intent, priority score, suggested page type.
- When presenting opportunities, include: title, type, organization, fit score, suggested talk topic.
- Be specific and actionable — don't just describe what to do, produce the actual draft.
"""

        # Inject available data context
        if context.get("existing_pages"):
            prompt += f"\nEXISTING PUBLISHED PAGES:\n{json.dumps(context['existing_pages'], indent=2, default=str)[:3000]}\n"

        if context.get("keyword_queue"):
            prompt += f"\nPENDING KEYWORDS:\n{json.dumps(context['keyword_queue'], indent=2, default=str)[:2000]}\n"

        if context.get("page_analytics"):
            prompt += f"\nPAGE ANALYTICS (LAST 30 DAYS):\n{json.dumps(context['page_analytics'], indent=2, default=str)[:3000]}\n"

        if context.get("opportunities"):
            prompt += f"\nACTIVE OPPORTUNITIES:\n{json.dumps(context['opportunities'], indent=2, default=str)[:2000]}\n"

        if context.get("search_queries"):
            prompt += f"\nRECENT USER SEARCH QUERIES:\n{json.dumps(context['search_queries'], indent=2, default=str)[:2000]}\n"

        if context.get("book_content"):
            prompt += f"\nBOOK SECTIONS:\n{json.dumps(context['book_content'], indent=2, default=str)[:3000]}\n"

        if context.get("scan_trends"):
            prompt += f"\nSCAN TRENDS:\n{json.dumps(context['scan_trends'], indent=2, default=str)[:2000]}\n"

        if not any(context.get(k) for k in ("existing_pages", "keyword_queue", "page_analytics")):
            prompt += (
                "\nNOTE: No existing page or keyword data available yet. "
                "This may be the initial setup — generate recommendations "
                "based on WIHY's core topics and Kortney's book themes.\n"
            )

        return prompt

    # ── Suggested Actions ───────────────────────────────────────────────

    def get_suggested_actions(
        self, context: Dict[str, Any], message: str, response: str
    ) -> List[SuggestedAction]:
        actions: List[SuggestedAction] = []
        msg = message.lower()

        # SEO-related follow-ups
        if any(w in msg for w in ("keyword", "seo", "search", "traffic", "rank")):
            actions.append(SuggestedAction(
                type="agent_followup",
                label="Show keyword clusters",
                message="Show me the current keyword clusters and which ones need pages",
            ))
            actions.append(SuggestedAction(
                type="agent_followup",
                label="Find new keyword opportunities",
                message="Discover new keyword opportunities from recent user queries and scan patterns",
            ))

        # Page-related follow-ups
        if any(w in msg for w in ("page", "content", "draft", "write", "create")):
            actions.append(SuggestedAction(
                type="agent_followup",
                label="Generate page draft",
                message="Create a full page draft for the top priority keyword that doesn't have a page yet",
            ))
            actions.append(SuggestedAction(
                type="agent_followup",
                label="Review weak pages",
                message="Which pages have impressions but low CTR and need title/meta rewrites?",
            ))

        # Speaking-related follow-ups
        if any(w in msg for w in ("speaking", "opportunity", "pitch", "conference", "podcast")):
            actions.append(SuggestedAction(
                type="agent_followup",
                label="Find speaking opportunities",
                message="Find new speaking opportunities that match Kortney's wellness and nutrition expertise",
            ))
            actions.append(SuggestedAction(
                type="agent_followup",
                label="Draft a pitch",
                message="Draft a speaker pitch email for the highest-fit opportunity",
            ))

        # Content expansion
        if any(w in msg for w in ("book", "chapter", "topic", "expand")):
            actions.append(SuggestedAction(
                type="agent_followup",
                label="Book-to-content pipeline",
                message="Take the top 3 book topics and turn them into searchable page drafts with FAQs",
            ))

        # Ingredient/product pages
        if any(w in msg for w in ("ingredient", "product", "scan", "alternative")):
            actions.append(SuggestedAction(
                type="agent_followup",
                label="Create ingredient page",
                message="Create an ingredient deep-dive page for the most scanned ingredient this week",
            ))
            actions.append(SuggestedAction(
                type="agent_followup",
                label="Alternatives page",
                message="Generate a healthier alternatives page for the most searched unhealthy product",
            ))

        # General / default
        if not actions:
            actions.append(SuggestedAction(
                type="agent_followup",
                label="SEO status overview",
                message="Give me an overview of our SEO status — pages published, keywords tracked, and top opportunities",
            ))
            actions.append(SuggestedAction(
                type="agent_followup",
                label="What should ALEX do next?",
                message="Based on current data, what are the top 3 things ALEX should build or improve right now?",
            ))

        return actions[:4]  # Cap at 4 suggestions
