"""
content/page_renderer.py — Renders page_store JSON pages as standalone SEO HTML.

Generates static HTML files for /is-it-healthy/{slug} pages that can be
deployed to Firebase Hosting (CG) or any static host (WIHY).

Output: self-contained HTML with embedded CSS, JSON-LD schema,
Open Graph tags, and CTAs linking into the main app.
"""

from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("wihy.page_renderer")


# ── Brand configs ─────────────────────────────────────────────────────────────

BRANDS = {
    "wihy": {
        "name": "WIHY",
        "full_name": "WIHY — What Is Healthy for You",
        "domain": "wihy.ai",
        "url": "https://wihy.ai",
        "logo": "/static/Logo_wihy.png",
        "favicon": "/static/Favicon.png",
        "color_primary": "#fa5f06",
        "color_primary_light": "rgba(250, 95, 6, 0.1)",
        "color_green": "#4cbb17",
        "color_blue": "#3b82f6",
        "cta_text": "Ask WIHY",
        "cta_url": "https://wihy.ai",
        "cta_scan": "https://wihy.ai",
        "cta_meal": "https://wihy.ai",
        "og_image": "https://wihy.ai/static/Logo_wihy.png",
        "twitter_handle": "@wihyai",
    },
    "communitygroceries": {
        "name": "Community Groceries",
        "full_name": "Community Groceries — Healthy Food for Your Community",
        "domain": "communitygroceries.com",
        "url": "https://communitygroceries.com",
        "logo": "/shoppingwithpurpose.png",
        "favicon": "/favicon.ico",
        "color_primary": "#2d6a4f",
        "color_primary_light": "rgba(45, 106, 79, 0.1)",
        "color_green": "#40916c",
        "color_blue": "#3b82f6",
        "cta_text": "Ask Community Groceries",
        "cta_url": "https://communitygroceries.com/chat",
        "cta_scan": "https://communitygroceries.com",
        "cta_meal": "https://communitygroceries.com/meals",
        "og_image": "https://communitygroceries.com/shoppingwithpurpose.png",
        "twitter_handle": "@commgroceries",
    },
}


def _e(text: str) -> str:
    """HTML-escape text."""
    return html.escape(str(text)) if text else ""


def _md_to_html(markdown_text: str) -> str:
    """Convert simple markdown to HTML (no external deps)."""
    if not markdown_text:
        return ""

    lines = markdown_text.split("\n")
    html_parts: list[str] = []
    in_list = False
    in_ol = False

    for line in lines:
        stripped = line.strip()

        # Headers
        if stripped.startswith("#### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h4>{_e(stripped[5:])}</h4>")
        elif stripped.startswith("### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h3>{_e(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h2>{_e(stripped[3:])}</h2>")
        # Unordered list
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_inline_md(_e(stripped[2:]))}</li>")
        # Numbered list
        elif re.match(r"^\d+\.\s", stripped):
            content = re.sub(r"^\d+\.\s", "", stripped)
            if not in_ol:
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                html_parts.append("<ol>")
                in_ol = True
            html_parts.append(f"<li>{_inline_md(_e(content))}</li>")
        # Empty line
        elif not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
        # Regular paragraph
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            html_parts.append(f"<p>{_inline_md(_e(stripped))}</p>")

    if in_list:
        html_parts.append("</ul>")
    if in_ol:
        html_parts.append("</ol>")

    return "\n".join(html_parts)


def _inline_md(text: str) -> str:
    """Convert inline markdown (bold, italic, links, code)."""
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Inline code
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def _build_faq_schema(faqs: List[Dict[str, str]], page_url: str) -> str:
    """Generate JSON-LD FAQPage schema."""
    if not faqs:
        return ""

    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq.get("q", ""),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq.get("a", ""),
                },
            }
            for faq in faqs
        ],
    }
    return json.dumps(schema, indent=2)


def _build_article_schema(page: Dict[str, Any], brand: Dict[str, str]) -> str:
    """Generate JSON-LD Article schema."""
    route_path = page.get("route_path") or f"{str(page.get('route_base', '/is-it-healthy')).rstrip('/')}/{page.get('slug', '')}"
    if not str(route_path).startswith("/"):
        route_path = f"/{route_path}"
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": page.get("title", ""),
        "description": page.get("meta_description", ""),
        "author": {
            "@type": "Organization",
            "name": brand["full_name"],
            "url": brand["url"],
        },
        "publisher": {
            "@type": "Organization",
            "name": brand["full_name"],
            "url": brand["url"],
            "logo": {
                "@type": "ImageObject",
                "url": f"{brand['url']}{brand['logo']}",
            },
        },
        "datePublished": page.get("created_at", datetime.utcnow().isoformat()),
        "dateModified": page.get("updated_at", page.get("created_at", datetime.utcnow().isoformat())),
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"{brand['url']}{route_path}",
        },
    }
    return json.dumps(schema, indent=2)


def render_page_html(
    page: Dict[str, Any],
    brand_key: str = "wihy",
    related_pages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Render a page_store entry as a complete HTML document.

    Args:
        page: Page data from page_store (slug, title, content, meta_description, faq, etc.)
        brand_key: "wihy" or "communitygroceries"
        related_pages: Optional list of related pages for internal linking

    Returns:
        Complete HTML string ready to write to file.
    """
    brand = BRANDS.get(brand_key, BRANDS["wihy"])
    slug = page.get("slug", "")
    title = page.get("title", slug.replace("-", " ").title())
    meta_desc = page.get("meta_description", "")
    summary = page.get("summary", "")
    content = page.get("content", "")
    keywords = page.get("keywords", "")
    faqs = page.get("faq", [])
    route_path = page.get("route_path") or f"{str(page.get('route_base', '/is-it-healthy')).rstrip('/')}/{slug}"
    if not str(route_path).startswith("/"):
        route_path = f"/{route_path}"
    page_url = f"{brand['url']}{route_path}"

    # Convert content markdown to HTML
    content_html = _md_to_html(content)

    # Build FAQ HTML
    faq_html = ""
    if faqs:
        faq_items = []
        for faq in faqs:
            q = _e(faq.get("q", ""))
            a = _e(faq.get("a", ""))
            faq_items.append(
                f'<details class="faq-item">\n'
                f'  <summary>{q}</summary>\n'
                f'  <p>{a}</p>\n'
                f'</details>'
            )
        faq_html = f'<section class="faq-section">\n<h2>Frequently Asked Questions</h2>\n{"".join(faq_items)}\n</section>'

    # Build related links HTML
    related_html = ""
    if related_pages:
        links = []
        for rp in related_pages[:5]:
            rp_slug = rp.get("slug", "")
            rp_title = rp.get("title", rp_slug.replace("-", " ").title())
            rp_route = rp.get("route_path") or f"{str(rp.get('route_base', '/is-it-healthy')).rstrip('/')}/{rp_slug}"
            if not str(rp_route).startswith("/"):
                rp_route = f"/{rp_route}"
            links.append(f'<a href="{_e(rp_route)}">{_e(rp_title)}</a>')
        related_html = (
            '<section class="related-section">\n'
            "<h2>Related Articles</h2>\n"
            '<div class="related-links">\n'
            + "\n".join(links)
            + "\n</div>\n</section>"
        )

    # Schema markup
    faq_schema = _build_faq_schema(faqs, page_url)
    article_schema = _build_article_schema(page, brand)

    route_base = str(page.get("route_base", "/is-it-healthy")).rstrip("/")
    if not route_base:
        route_base = "/is-it-healthy"
    section_label = "Health Library"
    if route_base == "/blog":
        section_label = "Blog"
    elif route_base == "/insights":
        section_label = "Insights"
    elif route_base == "/fitness":
        section_label = "Fitness"
    elif route_base == "/wellness":
        section_label = "Wellness"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_e(title)} | {_e(brand['name'])}</title>
    <meta name="description" content="{_e(meta_desc)}">
    <meta name="keywords" content="{_e(keywords)}">
    <link rel="canonical" href="{_e(page_url)}">
    <link rel="icon" type="image/png" href="{brand['favicon']}">

    <!-- Open Graph -->
    <meta property="og:type" content="article">
    <meta property="og:title" content="{_e(title)}">
    <meta property="og:description" content="{_e(meta_desc)}">
    <meta property="og:url" content="{_e(page_url)}">
    <meta property="og:image" content="{_e(brand['og_image'])}">
    <meta property="og:site_name" content="{_e(brand['full_name'])}">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{_e(title)}">
    <meta name="twitter:description" content="{_e(meta_desc)}">
    <meta name="twitter:image" content="{_e(brand['og_image'])}">
    <meta name="twitter:site" content="{brand['twitter_handle']}">

    <!-- JSON-LD Article Schema -->
    <script type="application/ld+json">
{article_schema}
    </script>

    {"<!-- JSON-LD FAQ Schema -->" if faq_schema else ""}
    {"<script type='application/ld+json'>" + faq_schema + "</script>" if faq_schema else ""}

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">

    <style>
        :root {{
            --brand-primary: {brand['color_primary']};
            --brand-primary-light: {brand['color_primary_light']};
            --brand-green: {brand['color_green']};
            --brand-blue: {brand['color_blue']};
            --text-dark: #1f2937;
            --text-secondary: #4b5563;
            --text-light: #6b7280;
            --bg-white: #ffffff;
            --bg-light: #f9fafb;
            --bg-blue: #eff6ff;
            --border: #e5e7eb;
            --shadow: 0 1px 3px rgba(0,0,0,0.1);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
            --radius: 12px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--text-dark);
            background: var(--bg-white);
            line-height: 1.7;
            -webkit-font-smoothing: antialiased;
        }}

        /* ── Navigation ─────────────────────────────── */
        .nav {{
            position: sticky;
            top: 0;
            background: var(--bg-white);
            border-bottom: 1px solid var(--border);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 100;
        }}
        .nav-logo {{
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
            color: var(--text-dark);
            font-weight: 700;
            font-size: 1.1rem;
        }}
        .nav-logo img {{
            height: 32px;
            width: auto;
        }}
        .nav-cta {{
            background: var(--brand-primary);
            color: white;
            padding: 8px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: opacity 0.2s;
        }}
        .nav-cta:hover {{ opacity: 0.9; }}

        /* ── Hero / Header ──────────────────────────── */
        .hero {{
            max-width: 780px;
            margin: 0 auto;
            padding: 48px 24px 0;
        }}
        .breadcrumb {{
            font-size: 0.85rem;
            color: var(--text-light);
            margin-bottom: 16px;
        }}
        .breadcrumb a {{
            color: var(--brand-primary);
            text-decoration: none;
        }}
        .hero h1 {{
            font-family: 'Playfair Display', serif;
            font-size: clamp(1.8rem, 4vw, 2.6rem);
            line-height: 1.2;
            margin-bottom: 16px;
            color: var(--text-dark);
        }}
        .hero-summary {{
            font-size: 1.15rem;
            color: var(--text-secondary);
            line-height: 1.6;
            padding: 20px 24px;
            background: var(--bg-blue);
            border-left: 4px solid var(--brand-primary);
            border-radius: 0 var(--radius) var(--radius) 0;
            margin-bottom: 8px;
        }}
        .hero-meta {{
            font-size: 0.85rem;
            color: var(--text-light);
            margin-bottom: 32px;
        }}

        /* ── Article Content ────────────────────────── */
        .article {{
            max-width: 780px;
            margin: 0 auto;
            padding: 0 24px 48px;
        }}
        .article h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.6rem;
            margin: 40px 0 16px;
            color: var(--text-dark);
        }}
        .article h3 {{
            font-size: 1.25rem;
            font-weight: 600;
            margin: 32px 0 12px;
            color: var(--text-dark);
        }}
        .article h4 {{
            font-size: 1.05rem;
            font-weight: 600;
            margin: 24px 0 8px;
            color: var(--text-secondary);
        }}
        .article p {{
            margin-bottom: 16px;
            color: var(--text-secondary);
        }}
        .article ul, .article ol {{
            margin: 0 0 16px 24px;
            color: var(--text-secondary);
        }}
        .article li {{
            margin-bottom: 8px;
        }}
        .article strong {{
            color: var(--text-dark);
            font-weight: 600;
        }}
        .article code {{
            background: var(--bg-light);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
        }}

        /* ── CTA Box ────────────────────────────────── */
        .cta-box {{
            background: linear-gradient(135deg, var(--brand-primary-light), var(--bg-blue));
            border: 2px solid var(--brand-primary);
            border-radius: var(--radius);
            padding: 32px;
            margin: 40px 0;
            text-align: center;
        }}
        .cta-box h3 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.4rem;
            margin: 0 0 12px;
            color: var(--text-dark);
        }}
        .cta-box p {{
            color: var(--text-secondary);
            margin-bottom: 20px;
            font-size: 1.05rem;
        }}
        .cta-button {{
            display: inline-block;
            background: var(--brand-primary);
            color: white;
            padding: 14px 32px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 700;
            font-size: 1.05rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .cta-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 14px rgba(250, 95, 6, 0.3);
        }}

        /* ── FAQ ────────────────────────────────────── */
        .faq-section {{
            max-width: 780px;
            margin: 0 auto;
            padding: 0 24px 48px;
        }}
        .faq-section h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.6rem;
            margin-bottom: 20px;
        }}
        .faq-item {{
            border: 1px solid var(--border);
            border-radius: var(--radius);
            margin-bottom: 12px;
            overflow: hidden;
        }}
        .faq-item summary {{
            padding: 16px 20px;
            cursor: pointer;
            font-weight: 600;
            color: var(--text-dark);
            background: var(--bg-light);
            list-style: none;
        }}
        .faq-item summary::-webkit-details-marker {{ display: none; }}
        .faq-item summary::before {{
            content: "+";
            display: inline-block;
            width: 24px;
            font-weight: 700;
            color: var(--brand-primary);
        }}
        .faq-item[open] summary::before {{ content: "−"; }}
        .faq-item p {{
            padding: 16px 20px;
            color: var(--text-secondary);
            line-height: 1.6;
        }}

        /* ── Related ────────────────────────────────── */
        .related-section {{
            max-width: 780px;
            margin: 0 auto;
            padding: 0 24px 48px;
        }}
        .related-section h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.4rem;
            margin-bottom: 16px;
        }}
        .related-links {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .related-links a {{
            display: block;
            padding: 14px 20px;
            background: var(--bg-light);
            border-radius: var(--radius);
            text-decoration: none;
            color: var(--brand-primary);
            font-weight: 500;
            transition: background 0.2s;
        }}
        .related-links a:hover {{
            background: var(--brand-primary-light);
        }}

        /* ── Footer ─────────────────────────────────── */
        .footer {{
            background: var(--bg-light);
            border-top: 1px solid var(--border);
            padding: 32px 24px;
            text-align: center;
            color: var(--text-light);
            font-size: 0.85rem;
        }}
        .footer a {{
            color: var(--brand-primary);
            text-decoration: none;
        }}
        .footer-links {{
            margin-top: 8px;
            display: flex;
            justify-content: center;
            gap: 24px;
        }}

        /* ── Responsive ─────────────────────────────── */
        @media (max-width: 640px) {{
            .hero {{ padding: 32px 16px 0; }}
            .article {{ padding: 0 16px 32px; }}
            .faq-section {{ padding: 0 16px 32px; }}
            .related-section {{ padding: 0 16px 32px; }}
            .cta-box {{ padding: 24px 16px; }}
        }}
    </style>
</head>
<body>

    <nav class="nav">
        <a href="{brand['url']}" class="nav-logo">
            <img src="{brand['logo']}" alt="{_e(brand['name'])}">
            <span>{_e(brand['name'])}</span>
        </a>
        <a href="{brand['cta_url']}" class="nav-cta">{_e(brand['cta_text'])} →</a>
    </nav>

    <header class="hero">
        <div class="breadcrumb">
            <a href="{brand['url']}">Home</a> › <a href="{route_base}">{_e(section_label)}</a> › {_e(title)}
        </div>
        <h1>{_e(title)}</h1>
        {f'<div class="hero-summary">{_e(summary)}</div>' if summary else ''}
        <div class="hero-meta">
            Reviewed by {_e(brand['full_name'])} · Evidence-based · Updated {datetime.utcnow().strftime("%B %Y")}
        </div>
    </header>

    <article class="article">
        {content_html}

        <div class="cta-box">
            <h3>Get a Personalized Answer</h3>
            <p>Your body, your goals, your restrictions — {_e(brand['name'])} gives you science-backed answers tailored to you.</p>
            <a href="{brand['cta_url']}" class="cta-button">{_e(brand['cta_text'])} →</a>
        </div>
    </article>

    {faq_html}
    {related_html}

    <footer class="footer">
        <p>&copy; {datetime.utcnow().year} {_e(brand['full_name'])}. For educational purposes — not medical advice.</p>
        <div class="footer-links">
            <a href="{brand['url']}/about">About</a>
            <a href="{brand['url']}/privacy">Privacy</a>
            <a href="{brand['url']}/terms">Terms</a>
            <a href="/is-it-healthy">Health Library</a>
        </div>
    </footer>

</body>
</html>"""


def render_index_html(
    pages: List[Dict[str, Any]],
    brand_key: str = "wihy",
) -> str:
    """Render the /is-it-healthy/ index page listing all published articles."""
    brand = BRANDS.get(brand_key, BRANDS["wihy"])

    # Group pages by cluster/category
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for p in pages:
        cat = p.get("page_type", "topic").replace("_", " ").title()
        if "is_it_healthy" in p.get("page_type", ""):
            cat = "Health & Science"
        categories.setdefault(cat, []).append(p)

    # Build card HTML
    cards_html = ""
    for cat_name, cat_pages in categories.items():
        cat_cards = ""
        for p in cat_pages:
            slug = p.get("slug", "")
            title = _e(p.get("title", slug.replace("-", " ").title()))
            desc = _e(p.get("meta_description", "")[:120])
            route_path = p.get("route_path", "")
            if not route_path:
                route_base = str(p.get("route_base", "/is-it-healthy")).rstrip("/")
                route_path = f"{route_base}/{slug}"
            if not str(route_path).startswith("/"):
                route_path = f"/{route_path}"
            cat_cards += (
                f'<a href="{route_path}" class="card">\n'
                f"  <h3>{title}</h3>\n"
                f"  <p>{desc}</p>\n"
                f"</a>\n"
            )
        cards_html += (
            f'<section class="category">\n'
            f"<h2>{_e(cat_name)}</h2>\n"
            f'<div class="card-grid">\n{cat_cards}</div>\n'
            f"</section>\n"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Health Library — Science-Backed Answers | {_e(brand['name'])}</title>
    <meta name="description" content="Evidence-based answers to your health, nutrition, and fitness questions. No fads, no hype — just research.">
    <link rel="canonical" href="{brand['url']}/is-it-healthy">
    <link rel="icon" type="image/png" href="{brand['favicon']}">

    <meta property="og:type" content="website">
    <meta property="og:title" content="Health Library | {_e(brand['name'])}">
    <meta property="og:description" content="Evidence-based answers to health, nutrition, and fitness questions.">
    <meta property="og:url" content="{brand['url']}/is-it-healthy">
    <meta property="og:image" content="{brand['og_image']}">

    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">

    <style>
        :root {{
            --brand-primary: {brand['color_primary']};
            --brand-primary-light: {brand['color_primary_light']};
            --text-dark: #1f2937;
            --text-secondary: #4b5563;
            --text-light: #6b7280;
            --bg-white: #ffffff;
            --bg-light: #f9fafb;
            --border: #e5e7eb;
            --radius: 12px;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            color: var(--text-dark);
            background: var(--bg-white);
            line-height: 1.6;
        }}
        .nav {{
            position: sticky; top: 0; background: var(--bg-white);
            border-bottom: 1px solid var(--border);
            padding: 12px 24px; display: flex; align-items: center;
            justify-content: space-between; z-index: 100;
        }}
        .nav-logo {{
            display: flex; align-items: center; gap: 10px;
            text-decoration: none; color: var(--text-dark);
            font-weight: 700; font-size: 1.1rem;
        }}
        .nav-logo img {{ height: 32px; }}
        .nav-cta {{
            background: var(--brand-primary); color: white;
            padding: 8px 20px; border-radius: 8px; text-decoration: none;
            font-weight: 600; font-size: 0.9rem;
        }}
        .page-header {{
            max-width: 900px; margin: 0 auto; padding: 48px 24px 32px;
            text-align: center;
        }}
        .page-header h1 {{
            font-family: 'Playfair Display', serif;
            font-size: clamp(2rem, 4vw, 2.8rem);
            margin-bottom: 12px;
        }}
        .page-header p {{
            font-size: 1.15rem; color: var(--text-secondary); max-width: 600px;
            margin: 0 auto;
        }}
        .category {{
            max-width: 900px; margin: 0 auto; padding: 0 24px 32px;
        }}
        .category h2 {{
            font-size: 1.3rem; font-weight: 700; margin-bottom: 16px;
            padding-bottom: 8px; border-bottom: 2px solid var(--brand-primary);
            display: inline-block;
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }}
        .card {{
            display: block; padding: 20px; background: var(--bg-light);
            border-radius: var(--radius); text-decoration: none;
            border: 1px solid var(--border); transition: border-color 0.2s, transform 0.2s;
        }}
        .card:hover {{
            border-color: var(--brand-primary); transform: translateY(-2px);
        }}
        .card h3 {{
            font-size: 1.05rem; color: var(--text-dark); margin-bottom: 8px;
        }}
        .card p {{
            font-size: 0.9rem; color: var(--text-light);
        }}
        .footer {{
            background: var(--bg-light); border-top: 1px solid var(--border);
            padding: 32px 24px; text-align: center; color: var(--text-light);
            font-size: 0.85rem; margin-top: 48px;
        }}
        .footer a {{ color: var(--brand-primary); text-decoration: none; }}
    </style>
</head>
<body>
    <nav class="nav">
        <a href="{brand['url']}" class="nav-logo">
            <img src="{brand['logo']}" alt="{_e(brand['name'])}">
            <span>{_e(brand['name'])}</span>
        </a>
        <a href="{brand['cta_url']}" class="nav-cta">{_e(brand['cta_text'])} →</a>
    </nav>

    <header class="page-header">
        <h1>Health Library</h1>
        <p>Evidence-based answers to your health, nutrition, and fitness questions. No fads, no hype — just research.</p>
    </header>

    {cards_html}

    <footer class="footer">
        <p>&copy; {datetime.utcnow().year} {_e(brand['full_name'])}. For educational purposes — not medical advice.</p>
    </footer>
</body>
</html>"""


def render_sitemap_xml(
    pages: List[Dict[str, Any]],
    brand_key: str = "wihy",
    extra_urls: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Generate sitemap.xml for all published pages.

    Each page dict should contain either:
      - route_path: full path like /blog/my-post
      - route_base + slug: e.g. /blog + my-post → /blog/my-post
      - slug only: falls back to /blog/{slug}
    """
    brand = BRANDS.get(brand_key, BRANDS["wihy"])
    base = brand["url"]

    entries = []

    # Static pages
    static_pages = extra_urls or [
        {"loc": "/", "changefreq": "weekly", "priority": "1.0"},
        {"loc": "/about", "changefreq": "monthly", "priority": "0.8"},
        {"loc": "/subscription", "changefreq": "monthly", "priority": "0.8"},
        {"loc": "/chat", "changefreq": "weekly", "priority": "0.7"},
        {"loc": "/is-it-healthy", "changefreq": "daily", "priority": "0.9"},
        {"loc": "/blog", "changefreq": "daily", "priority": "0.9"},
        {"loc": "/insights", "changefreq": "daily", "priority": "0.9"},
        {"loc": "/fitness", "changefreq": "daily", "priority": "0.9"},
        {"loc": "/wellness", "changefreq": "daily", "priority": "0.9"},
        {"loc": "/trends", "changefreq": "daily", "priority": "0.9"},
        {"loc": "/comparison", "changefreq": "daily", "priority": "0.9"},
        {"loc": "/search", "changefreq": "weekly", "priority": "0.7"},
        {"loc": "/support", "changefreq": "monthly", "priority": "0.5"},
    ]
    for s in static_pages:
        entries.append(
            f"  <url>\n"
            f"    <loc>{base}{s['loc']}</loc>\n"
            f"    <changefreq>{s['changefreq']}</changefreq>\n"
            f"    <priority>{s['priority']}</priority>\n"
            f"  </url>"
        )

    # Content pages — use route_path or route_base/slug
    seen = set()
    for p in pages:
        route_path = p.get("route_path", "")
        if not route_path:
            route_base = p.get("route_base", "/blog")
            slug = p.get("slug", "")
            if slug:
                route_path = f"{route_base}/{slug}"
        if route_path and not str(route_path).startswith("/"):
            route_path = f"/{route_path}"
        if not route_path or route_path in seen:
            continue
        seen.add(route_path)
        updated = p.get("updated_at", p.get("created_at", datetime.utcnow().isoformat()))
        entries.append(
            f"  <url>\n"
            f"    <loc>{base}{route_path}</loc>\n"
            f"    <lastmod>{updated[:10]}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.8</priority>\n"
            f"  </url>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>"
    )


def render_robots_txt(brand_key: str = "wihy") -> str:
    """Generate robots.txt."""
    brand = BRANDS.get(brand_key, BRANDS["wihy"])
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {brand['url']}/sitemap.xml\n"
    )
