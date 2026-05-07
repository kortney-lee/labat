"""
Nurture Email Service
7-email drip campaign for What Is Healthy? book leads via SendGrid.
Dynamic content based on ad variant (stored as utm_content on the lead).

Schedule:
  Day 0:  book_delivery      — Book download + first check-in
  Day 1:  did_you_get_this    — Follow up, tease paperback
  Day 3:  big_benefit         — Value bullets, chapter tease, soft paperback
  Day 5:  got_questions       — Curse of knowledge, WIHY app mention
  Day 7:  social_proof        — Testimonial, paperback upsell
  Day 10: im_surprised        — Urgency, why haven't you ordered?
  Day 14: last_chance          — Final push, paperback + CG + WIHY
"""

import logging
import os
from datetime import datetime, timezone, timedelta

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
BOOK_EMAIL_BCC = (os.getenv("BOOK_EMAIL_BCC", "kortney@wihy.ai") or "").strip()

# Brand-specific sender configs (matches SendGrid verified senders)
BRAND_CONFIG = {
    "vowels": {
        "from_email": "info@vowels.org",
        "from_name": "Vowels",
        "team_name": "The Vowels Team",
        "brand_label": "Vowels",
    },
    "cg": {
        "from_email": "sales@communitygroceries.com",
        "from_name": "Community Groceries",
        "team_name": "The Community Groceries Team",
        "brand_label": "Community Groceries",
    },
    "wihy": {
        "from_email": "kortney@wihy.ai",
        "from_name": "WiHY AI",
        "team_name": "The WIHY Team",
        "brand_label": "WIHY",
    },
}
_DEFAULT_BRAND = "vowels"

BOOK_PDF_URL = "https://whatishealthy.org/WhatisHealthy_FreeIntroduction.pdf"
CONFIRM_DOWNLOAD_URL = "https://whatishealthy.org/confirm-download.html"
BOOK_IMAGE_URL = "https://storage.googleapis.com/wihy-web-assets/images/book/BookGreen.jpg"
WIHY_URL = "https://wihy.ai"
BOOK_URL = "https://whatishealthy.org"
UNSUBSCRIBE_URL = "https://whatishealthy.org/unsubscribe"

CG_URL = "https://communitygroceries.com"

PAPERBACK_URL_FEMALE = "https://buy.stripe.com/dRmbJ13cu4dYcdz5t0ejK0i"
PAPERBACK_URL_MALE = "https://buy.stripe.com/aFafZheVc7qacdzg7EejK0j"
AMAZON_PAPERBACK_URL = "https://www.amazon.com/dp/B0FJ2494LH"
AMAZON_HARDCOVER_URL = "https://www.amazon.com/dp/B0FJ23J6JQ"
AMAZON_KINDLE_URL = "https://www.amazon.com/dp/B0DL7Z7NFL"
AMAZON_AUDIBLE_URL = "https://www.amazon.com/dp/B0GVWM74FR"

# ── Variant copy — dynamic keyword inserts per ad variant ─────────────────

_DEFAULT_COPY = {
    "goal": "eating healthier and taking control of what goes into your body",
    "desired_result": "finally understanding what's in your food and what to do about it",
    "big_benefit": "A healthier life",
    "topic": "healthy eating",
    "topic_benefit": "take control of their health through better food choices",
    "chapter_hook": "Chapter 3 breaks down the ingredients food companies hide behind 'natural flavors' — and what they're actually doing to your body.",
    "bullet1": "Why 'natural flavors' isn't what you think it is",
    "bullet2": "The one ingredient that shows up in 68% of packaged food — and why it matters",
    "bullet3": "Simple swaps you can make at your next grocery run",
    "download_cta": "Download Your Life-Changing Book",
}

VARIANT_COPY = {
    "weight": {
        "goal": "losing weight and keeping it off",
        "desired_result": "finally dropping the weight for good",
        "big_benefit": "A healthier body",
        "topic": "weight loss",
        "topic_benefit": "take control of their weight",
        "chapter_hook": "Chapter 5 breaks down why calories-in-calories-out is a myth — and what actually controls your weight.",
        "bullet1": "Why 'low-fat' and 'diet' labels may actually be making you gain weight",
        "bullet2": "The one ingredient in 68% of packaged food that keeps your body storing fat",
        "bullet3": "How to drop weight by changing WHAT you buy — not how much you eat",
        "download_cta": "Your Key to Finally Losing the Weight",
    },
    "kids": {
        "goal": "getting your kids eating healthy without the fights",
        "desired_result": "getting your kids off processed food for good",
        "big_benefit": "A healthier family",
        "topic": "kids and nutrition",
        "topic_benefit": "raise their kids on real food",
        "chapter_hook": "Chapter 7 exposes exactly how food companies engineer products to hook your children.",
        "bullet1": "Why your 'picky eater' isn't picky — they're addicted to engineered flavors",
        "bullet2": "3 simple swaps that make the transition painless for kids",
        "bullet3": "The after-school snack trick that changes everything",
        "download_cta": "Your Key to a Healthier Family",
    },
    "energy": {
        "goal": "getting your energy back and feeling like yourself again",
        "desired_result": "eliminating brain fog and afternoon crashes",
        "big_benefit": "All-day energy",
        "topic": "energy and nutrition",
        "topic_benefit": "stop feeling tired all the time",
        "chapter_hook": "Chapter 4 connects the dots between what you eat for breakfast and why you crash at 2pm.",
        "bullet1": "Why your morning 'healthy' cereal might be draining your energy by noon",
        "bullet2": "The blood-sugar trap hiding in foods you think are good for you",
        "bullet3": "One simple morning change that eliminates the afternoon crash",
        "download_cta": "Your Key to All-Day Energy",
    },
    "groceries": {
        "goal": "spending less on groceries while eating healthier",
        "desired_result": "cutting your grocery bill while eating better",
        "big_benefit": "Lower grocery bills",
        "topic": "grocery shopping and health",
        "topic_benefit": "stop overspending on food that isn't feeding their body",
        "chapter_hook": "Chapter 6 shows you exactly which 'premium' products are just repackaged junk — and what to buy instead.",
        "bullet1": "Why 'organic' and 'natural' labels cost you more but don't make you healthier",
        "bullet2": "The 5 grocery aisles where you're wasting the most money every week",
        "bullet3": "How to cut your food budget by 30% while eating better than before",
        "download_cta": "Your Key to Eating Better for Less",
    },
    "family": {
        "goal": "breaking the cycle of diet-related disease in your family",
        "desired_result": "protecting your family from the health problems you watched your parents go through",
        "big_benefit": "A healthier future",
        "topic": "family health",
        "topic_benefit": "make sure their family doesn't repeat the same health mistakes",
        "chapter_hook": "Chapter 8 shows why it was never genetics — it was habits passed down through food choices.",
        "bullet1": "Why the diseases you watched your parents fight weren't 'genetic' — they were dietary",
        "bullet2": "The 3 food habits silently being passed from generation to generation",
        "bullet3": "How one family dinner change can shift your kids' health trajectory",
        "download_cta": "Your Key to a Healthier Future",
    },
    "confused": {
        "goal": "finally understanding what's actually healthy",
        "desired_result": "cutting through the noise and knowing exactly what to eat",
        "big_benefit": "Clarity on health",
        "topic": "what's really healthy",
        "topic_benefit": "stop being confused about nutrition",
        "chapter_hook": "Chapter 2 explains why the advice keeps changing — and who profits when you stay confused.",
        "bullet1": "Why eggs, fat, and salt keep flip-flopping between 'good' and 'bad'",
        "bullet2": "The food industry's #1 strategy: keep you confused so you keep buying",
        "bullet3": "A dead-simple framework to know if something is actually healthy in 5 seconds",
        "download_cta": "Your Key to Knowing What's Actually Healthy",
    },
    "warning": {
        "goal": "knowing exactly what you're putting in your family's bodies",
        "desired_result": "never being fooled by a food label again",
        "big_benefit": "Label literacy",
        "topic": "food labels and marketing",
        "topic_benefit": "stop falling for food industry tricks",
        "chapter_hook": "Chapter 3 breaks down the 23 ingredients food companies hide behind 'natural flavors' — and what they do to your body.",
        "bullet1": "Why 'natural flavors' is the most misleading phrase on any food label",
        "bullet2": "The 5 'health foods' at your grocery store that are actually junk food in disguise",
        "bullet3": "How to read any food label in 10 seconds and know if it's real food",
        "download_cta": "Your Key to Reading Every Label Right",
    },
    "realfood": {
        "goal": "feeding your family real food without spending more money",
        "desired_result": "getting real food on your table this week without blowing your budget",
        "big_benefit": "Real food, same budget",
        "topic": "eating real food on a budget",
        "topic_benefit": "feed their family real food without going broke",
        "chapter_hook": "Chapter 6 proves you don't need a bigger grocery budget — you need to stop buying the foods the industry tricked you into thinking are healthy.",
        "bullet1": "Why the 'healthy' aisle is the most overpriced section of the grocery store",
        "bullet2": "5 real-food swaps that cost LESS than what you're buying now",
        "bullet3": "The meal planning shortcut that saves most families $200+ per month",
        "download_cta": "Your Key to Real Food on Any Budget",
    },
    "eliminate": {
        "goal": "losing weight and saving money by cutting the right foods",
        "desired_result": "dropping weight and grocery costs at the same time",
        "big_benefit": "Less weight, less spending",
        "topic": "hidden 'health' foods",
        "topic_benefit": "stop buying foods that sabotage their health and wallet",
        "chapter_hook": "Chapter 3 reveals the 10 'health' foods that are keeping you overweight and costing you a fortune.",
        "bullet1": "Why that granola bar is worse for you than the candy bar next to it",
        "bullet2": "The fruit juice truth: how '100% natural' became 100% sugar",
        "bullet3": "10 immediate cuts that save you money AND help you lose weight this month",
        "download_cta": "Your Key to Cutting the Weight & the Cost",
    },
    "biglie": {
        "goal": "seeing through the food industry's lies and protecting your family",
        "desired_result": "never being manipulated by food marketing again",
        "big_benefit": "The truth about food",
        "topic": "what the food industry hides from you",
        "topic_benefit": "protect their family from industry manipulation",
        "chapter_hook": "Chapter 1 traces exactly how food companies convinced an entire generation that processed food was normal — and what it's costing your family.",
        "bullet1": "The marketing trick that makes processed food look healthier than real food",
        "bullet2": "Why childhood obesity tripled in one generation — and it wasn't because of laziness",
        "bullet3": "How to break the cycle so your kids don't inherit the same health problems",
        "download_cta": "Your Key to the Truth About Food",
    },
    "mistakes": {
        "goal": "stopping the grocery mistakes that cost you your health and money",
        "desired_result": "fixing the shopping habits that are quietly draining your wallet and health",
        "big_benefit": "Smarter grocery trips",
        "topic": "grocery shopping mistakes",
        "topic_benefit": "stop making costly mistakes at the grocery store",
        "chapter_hook": "Chapter 6 breaks down the 5 biggest mistakes families make at the grocery store — and shows you how to fix them starting on your next trip.",
        "bullet1": "Mistake #1: Trusting the 'healthy' shelf at your grocery store",
        "bullet2": "Mistake #3: Buying 'organic' everything (it's not what you think)",
        "bullet3": "The checkout-line fix that saves most families $50+ per month",
        "download_cta": "Your Key to Smarter Grocery Trips",
    },
    "finally": {
        "goal": "getting your family eating healthy without dieting or spending more",
        "desired_result": "finally eating healthy without the stress, rules, or extra cost",
        "big_benefit": "Health without the hassle",
        "topic": "eating healthy without dieting",
        "topic_benefit": "get healthy without counting calories or buying expensive food",
        "chapter_hook": "The book strips away everything that makes 'eating healthy' feel hard — no calorie counting, no meal kits, no overpriced organic everything.",
        "bullet1": "Why diets fail 95% of the time — and what to do instead",
        "bullet2": "The 'no diet' approach that helps families eat better on the same budget",
        "bullet3": "How to make the switch to real food without changing your schedule",
        "download_cta": "Your Key to Health Without the Hassle",
    },
}


def _get_copy(variant: str) -> dict:
    """Return variant-specific copy or defaults."""
    return VARIANT_COPY.get(variant, _DEFAULT_COPY)


# Map variant → brand (all current variants are Vowels ads)
_VARIANT_BRAND = {v: "vowels" for v in VARIANT_COPY}
# Future CG variants: _VARIANT_BRAND["cg_healthy"] = "cg"  etc.


def _get_brand_config(variant: str = "") -> dict:
    """Return brand config (sender, team name) for a variant."""
    brand = _VARIANT_BRAND.get(variant, _DEFAULT_BRAND)
    return BRAND_CONFIG[brand]


def _team(variant: str) -> str:
    """Return team sign-off name for a variant."""
    return _get_brand_config(variant)["team_name"]


# Nurture sequence: (stage, days_after_signup, template_id, subject)
NURTURE_SEQUENCE = [
    (0, 0,  "book_delivery",    "Why I wrote this, {first_name}"),
    (1, 1,  "did_you_get_this", "The first page of the book"),
    (2, 3,  "big_benefit",      "What's actually in \"natural flavors\""),
    (3, 5,  "got_questions",    "The 5-second test for any food label"),
    (4, 7,  "social_proof",     "What changed after Chapter 6"),
    (5, 10, "im_surprised",     "The chapter everyone dog-ears"),
    (6, 14, "last_chance",      "My last email to you"),
]


# ── Email wrapper ─────────────────────────────────────────────────────────────

def _email_wrap(content: str, variant: str = "") -> str:
    """Lightweight, personal email wrapper — white bg, no colored banner."""
    b = _get_brand_config(variant)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;">
{content}
<tr><td style="padding:24px 32px;border-top:1px solid #f0f0f0;">
<p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;text-align:center;">
Sent by {b['brand_label']} &middot; <a href="{UNSUBSCRIBE_URL}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
</p></td></tr>
</table></td></tr></table></body></html>"""


def _cta_button(label: str, url: str, color: str = "#1e40af") -> str:
    return (
        f'<a href="{url}" style="display:inline-block;background:{color};color:#ffffff;'
        f'font-size:16px;font-weight:600;text-decoration:none;padding:14px 28px;'
        f'border-radius:6px;">{label}</a>'
    )


def _bullets(c: dict) -> str:
    return f"""<ul style="margin:0 0 24px;padding-left:20px;font-size:16px;line-height:2;color:#374151;">
<li>{c['bullet1']}</li>
<li>{c['bullet2']}</li>
<li>{c['bullet3']}</li>
</ul>"""


def _paperback_buttons() -> str:
    return f"""<div style="text-align:center;margin-bottom:8px;">
{_cta_button("Order Paperback &mdash; Female Cover", PAPERBACK_URL_FEMALE, "#16a34a")}
</div>
<div style="text-align:center;margin-top:12px;">
{_cta_button("Order Paperback &mdash; Male Cover", PAPERBACK_URL_MALE, "#16a34a")}
</div>"""


def _all_format_buttons() -> str:
    """Full grid of purchase options: Stripe paperback + all Amazon formats."""
    def btn(label: str, url: str, color: str) -> str:
        return (
            f'<div style="text-align:center;margin-bottom:10px;">'
            f'<a href="{url}" style="display:inline-block;background:{color};color:#ffffff;'
            f'font-size:15px;font-weight:600;text-decoration:none;padding:12px 24px;'
            f'border-radius:6px;width:100%;max-width:320px;box-sizing:border-box;">{label}</a>'
            f'</div>'
        )
    return (
        btn("📦 Ship Paperback — Female Cover", PAPERBACK_URL_FEMALE, "#16a34a") +
        btn("📦 Ship Paperback — Male Cover", PAPERBACK_URL_MALE, "#16a34a") +
        btn("🛒 Amazon Paperback", AMAZON_PAPERBACK_URL, "#FF9900") +
        btn("📘 Amazon Hardcover", AMAZON_HARDCOVER_URL, "#232f3e") +
        btn("📱 Kindle Edition", AMAZON_KINDLE_URL, "#1A6B9A") +
        btn("🎧 Audible Audiobook", AMAZON_AUDIBLE_URL, "#F38B00")
    )


# ── Template builders ─────────────────────────────────────────────────────────

def _render_book_delivery(first_name: str, variant: str = "", **kw) -> str:
    """Day 0 — origin story: why Kortney wrote the book. No download link. Buy CTA."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 0;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
My grandmother died of type 2 diabetes at 64.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
She wasn't reckless about food. She read labels. She bought "low-fat." She chose "heart-healthy" cereals and "natural" juices. By every measure she understood, she was eating well.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
It didn't matter.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
After she passed, I went down a rabbit hole trying to understand how someone who <em>tried</em> could still end up that sick. What I found made me furious — and eventually led me to write <strong>What Is Healthy?</strong></p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Here's a small sample of what the research showed me:</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#eff6ff;border-left:4px solid #1e40af;border-radius:0 8px 8px 0;">
<tr><td style="padding:20px 24px;">
<p style="margin:0 0 14px;font-size:16px;line-height:1.8;color:#1e3a5f;">
&#9679;&nbsp; The FDA allows over <strong>3,000 different chemicals</strong> under the single label "natural flavors" — a term specifically designed to sound harmless while telling you nothing about what's actually in your food.</p>
<p style="margin:0 0 14px;font-size:16px;line-height:1.8;color:#1e3a5f;">
&#9679;&nbsp; The ingredient most strongly linked to metabolic disease appears on food labels under <strong>at least 61 different names</strong>. Most people eat it every single day without knowing it.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#1e3a5f;">
&#9679;&nbsp; The US food industry spends <strong>$14 billion per year</strong> marketing to children — more than the GDP of some nations — specifically to build brand loyalty before a child can read a label.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
None of this is conspiracy. It's in the regulatory filings, the peer-reviewed research, and the industry's own documents. I spent two years pulling it together — no agenda, no supplements to sell, no diet to push.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
That became <strong>What Is Healthy?</strong> — 264 pages on what the food industry doesn't want you to understand, and exactly what to do about it. Available in every format:</p>
</td></tr>
<tr><td style="padding:0 32px 8px;">
{_all_format_buttons()}
<p style="margin:8px 0 0;font-size:13px;line-height:1.6;color:#9ca3af;text-align:center;">
Paperback ships free &bull; Kindle &amp; Audible available instantly</p>
</td></tr>
<tr><td style="padding:24px 32px 32px;border-top:1px solid #f3f4f6;margin-top:24px;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
I'll send you the first page of the book tomorrow.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Talk soon,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_did_you_get_this(first_name: str, variant: str = "", **kw) -> str:
    """Day 1 — embed the book's opening prose as HTML. Cut at cliffhanger. Buy CTA."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 0;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Here's how <strong>What Is Healthy?</strong> opens:</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#fafafa;border:1px solid #e5e7eb;border-radius:8px;">
<tr><td style="padding:28px 32px;">
<p style="margin:0 0 18px;font-size:15px;line-height:1.9;color:#374151;font-style:italic;">
We are the sickest generation of Americans in recorded history.</p>
<p style="margin:0 0 18px;font-size:15px;line-height:1.9;color:#374151;font-style:italic;">
Not sicker because we are older. Not sicker because we have stopped trying. We are sicker
in spite of knowing more about nutrition than any generation before us. We have more
diet books, more health apps, more organic labels, and more "wellness" products than
ever before — and the rates of obesity, type 2 diabetes, heart disease, and metabolic
dysfunction keep climbing.</p>
<p style="margin:0 0 18px;font-size:15px;line-height:1.9;color:#374151;font-style:italic;">
Something is very wrong with the story we've been told about food.</p>
<p style="margin:0 0 18px;font-size:15px;line-height:1.9;color:#374151;font-style:italic;">
Most people feel it. They follow the advice and don't get better. They read the labels
and still feel confused. They try harder and the needle doesn't move. And after a while,
they start to wonder if the problem is them — if they're just not disciplined enough,
not consistent enough, not smart enough about food.</p>
<p style="margin:0 0 0;font-size:15px;line-height:1.9;color:#374151;font-style:italic;">
They're not. The system is broken — and it was designed to be.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<p style="margin:20px 0 20px;font-size:17px;line-height:1.8;color:#374151;">
The next chapter is called <strong>"How Did We Get Here?"</strong></p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
It answers the question most people have been afraid to ask — because the answer means
the problem isn't you. It was never you. And once you see it, you can't unsee it.</p>
<p style="margin:0 0 12px;font-size:17px;line-height:1.8;color:#374151;">
The full 264-page book, in every format:</p>
</td></tr>
<tr><td style="padding:0 32px 8px;">
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:20px 32px 32px;border-top:1px solid #f3f4f6;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
More coming in a few days.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Talk soon,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_big_benefit(first_name: str, variant: str = "", **kw) -> str:
    """Day 3 — deep dive on 'natural flavors' deception + variant-specific angle."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 0;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Here's something from the book I think about every time I'm in a grocery store.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Pick up any packaged food. Find the ingredients list. Look for the words
<strong>"natural flavors."</strong></p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
You'll find it on almost everything — granola bars, yogurt, flavored water, crackers,
baby food. It sounds harmless. "Natural" is right there in the name.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Here's what the label doesn't tell you: "natural flavors" is a legal catch-all term
that covers <strong>over 3,000 approved additives</strong>. Under FDA rules, any
substance originally derived from a plant or animal — no matter how extensively
processed — can be called a "natural flavor." Beaver anal glands.
Insect-derived colorants. Chemically extracted compounds that have never appeared
in nature in that form. All of it: "natural flavors."</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
This isn't an accident. It's a design decision — made by an industry that spent decades
lobbying for label language that sounds reassuring while revealing nothing.</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#fef9ec;border-left:4px solid #d97706;border-radius:0 8px 8px 0;">
<tr><td style="padding:20px 24px;">
<p style="margin:0 0 10px;font-size:15px;font-weight:700;color:#92400e;">
What this means for {c['topic']}:</p>
<p style="margin:0 0 10px;font-size:15px;line-height:1.8;color:#78350f;">&#9679;&nbsp; {c['bullet1']}</p>
<p style="margin:0 0 10px;font-size:15px;line-height:1.8;color:#78350f;">&#9679;&nbsp; {c['bullet2']}</p>
<p style="margin:0 0 0;font-size:15px;line-height:1.8;color:#78350f;">&#9679;&nbsp; {c['bullet3']}</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<p style="margin:20px 0 20px;font-size:17px;line-height:1.8;color:#374151;">
{c['chapter_hook']}</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
There are 22 more revelations like this in the book. Each one changes the way you
read a label — and what you put in your cart. Available in every format:</p>
</td></tr>
<tr><td style="padding:0 32px 8px;">
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:20px 32px 32px;border-top:1px solid #f3f4f6;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
Talk soon,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_got_questions(first_name: str, variant: str = "", **kw) -> str:
    """Day 5 — actionable framework: the 5-second label test. WIHY plug."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 0;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
One of the most useful things in the book is a framework I call the
<strong>5-second label test</strong>. Here's the short version:</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;">
<tr><td style="padding:24px 28px;">
<p style="margin:0 0 10px;font-size:15px;font-weight:700;color:#166534;">
The 5-Second Label Test:</p>
<p style="margin:0 0 12px;font-size:15px;line-height:1.8;color:#14532d;">
<strong>1.</strong> Flip the package over. Find the ingredients list — not the nutrition facts panel.</p>
<p style="margin:0 0 12px;font-size:15px;line-height:1.8;color:#14532d;">
<strong>2.</strong> Count how many ingredients have names you couldn't say out loud at a grocery store. Not abbreviations or jargon — just: would a person call this an ingredient at home?</p>
<p style="margin:0 0 12px;font-size:15px;line-height:1.8;color:#14532d;">
<strong>3.</strong> If more than 2 of them fail that test, put it back.</p>
<p style="margin:0 0 0;font-size:15px;line-height:1.8;color:#14532d;">
That's it. You don't need a chemistry degree. You don't need a calorie counter. You
just need five seconds and the back of the package.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<p style="margin:20px 0 20px;font-size:17px;line-height:1.8;color:#374151;">
The book has 11 more frameworks like this — each one built for a real situation:
reading labels in under a minute, identifying hidden sugars by their 61 alternate names,
knowing which "health food" aisle products are junk in disguise.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
We also built <strong>Eden by WIHY</strong> — a free AI that lets you ask any food or
health question and get a straight answer backed by the same research as the book.
Think of it as the book, but in your pocket at the grocery store.</p>
<div style="text-align:center;margin:0 0 20px;">
{_cta_button("Try Eden Free", WIHY_URL)}
</div>
<p style="margin:0 0 12px;font-size:17px;line-height:1.8;color:#374151;">
And if you want all 12 frameworks in one place — the full book:</p>
</td></tr>
<tr><td style="padding:0 32px 8px;">
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:20px 32px 32px;border-top:1px solid #f3f4f6;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_social_proof(first_name: str, variant: str = "", **kw) -> str:
    """Day 7 — reader story told as mini narrative. Specific outcome. Buy CTA."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 0;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
A reader named Sarah sent me a message a few weeks after getting the book.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
She said she'd read Chapter 6 — the one about how grocery stores are physically designed
to increase impulse purchases of processed food — and then walked into a grocery store
and felt like she was seeing it for the first time. The end-cap displays. The eye-level
placement. The "sale" signage that drives you toward items with the highest margin.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
She said: <em>"I literally walked out of the store with half the things I normally
buy and spent $40 less. I wasn't trying. I just couldn't un-see what the book showed me."</em></p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
That's what this book does. It's not a list of rules. It's not a diet. It's the understanding
that, once you have it, changes how you see every food decision — in the store, in the kitchen,
on the label.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
That's what I wrote it for. And it's why {c['desired_result']} is actually possible —
once you know what you're looking at.</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#f9fafb;border-left:4px solid #6b7280;border-radius:0 8px 8px 0;">
<tr><td style="padding:20px 24px;">
<p style="margin:0 0 0;font-size:15px;line-height:1.9;color:#4b5563;font-style:italic;">
"I had my husband read Chapter 3 while I made dinner. He came downstairs and just
said: 'We've been lied to for 30 years.' We cleared out half the pantry that night."
<br/><span style="font-style:normal;font-weight:600;color:#6b7280;">— Marcus, reader since 2024</span></p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<p style="margin:20px 0 12px;font-size:17px;line-height:1.8;color:#374151;">
The full book, in every format:</p>
</td></tr>
<tr><td style="padding:0 32px 8px;">
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:20px 32px 32px;border-top:1px solid #f3f4f6;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_im_surprised(first_name: str, variant: str = "", **kw) -> str:
    """Day 10 — tease the most dog-eared chapter. Specific content. Urgency. Buy CTA."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 0;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
There's one chapter in <strong>What Is Healthy?</strong> that readers dog-ear more than
any other.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
It's not the one about natural flavors. It's not the one about the food industry's
lobbying history. It's a chapter called <strong>"What the Grocery Store Doesn't
Want You to Know"</strong> — and it's the most practical chapter in the book.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Here's the short version of one insight from it:</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#eff6ff;border-left:4px solid #1e40af;border-radius:0 8px 8px 0;">
<tr><td style="padding:20px 24px;">
<p style="margin:0 0 14px;font-size:15px;line-height:1.9;color:#1e3a5f;">
The average grocery store stocks 40,000 items. Studies show shoppers make 60–70% of
purchase decisions <em>in the store</em>, not at home on a list.</p>
<p style="margin:0 0 0;font-size:15px;line-height:1.9;color:#1e3a5f;">
The store layout — the produce at the entrance, the dairy at the back, the end-caps
and eye-level shelving — is not designed for your convenience. It's designed by
category managers paid specifically to maximize impulse purchases of high-margin
processed items.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 20px;">
<p style="margin:20px 0 20px;font-size:17px;line-height:1.8;color:#374151;">
The chapter breaks down exactly how this works, aisle by aisle — and gives you a
shopping approach that routes around it. Most readers say they save $30–50 per trip
just by changing how they walk through the store.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
That chapter alone is worth the price of the book. And there are 18 more like it.</p>
<p style="margin:0 0 12px;font-size:17px;line-height:1.8;color:#374151;">
Get the full book in whatever format works for you:</p>
</td></tr>
<tr><td style="padding:0 32px 8px;">
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:20px 32px 32px;border-top:1px solid #f3f4f6;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_last_chance(first_name: str, variant: str = "", **kw) -> str:
    """Day 14 — honest final email. Story-based. All formats. CG + Eden plug."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 0;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
This is my last email.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Over the past two weeks I've shared: why I wrote this book, the opening chapter,
what's actually hiding inside "natural flavors," a framework for reading any label in
five seconds, a reader whose grocery bill dropped $40 the first week, and the chapter
that changes how you walk through a store.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
All of it comes from one 264-page book built on two years of research.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
I'm not going to make a hard sell here. If any of this landed for you — if you found
yourself thinking differently about a label, a grocery aisle, or what you're feeding
your family — the full book is going to be worth it. If none of it landed, it's
probably not the right time. And that's fine.</p>
<p style="margin:0 0 12px;font-size:17px;line-height:1.8;color:#374151;">
If you want it:</p>
</td></tr>
<tr><td style="padding:0 32px 8px;">
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:24px 32px 0;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#6b7280;">
Two more things worth knowing, both connected to what the book is about:</p>
<p style="margin:0 0 12px;font-size:16px;line-height:1.8;color:#374151;">
<strong>Eden by WIHY</strong> — a free AI you can ask any food or health question.
Scan a label in the store. Ask why a specific ingredient matters. Get straight answers
backed by real research, not sponsored content.
<a href="{WIHY_URL}" style="color:#1e40af;">Try it free at wihy.ai</a></p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
<strong>Community Groceries</strong> — a grocery service built around the principles
in the book. Real food, fair prices, without the processed aisle.
<a href="{CG_URL}" style="color:#1e40af;">communitygroceries.com</a></p>
</td></tr>
<tr><td style="padding:24px 32px 32px;border-top:1px solid #f3f4f6;margin-top:24px;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
Whatever you decide — keep reading those labels.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
All the best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_buy_now_offer(first_name: str, variant: str = "", **kw) -> str:
    """Immediate buyer-intent push — short, direct, all formats."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 0;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
<strong>What Is Healthy?</strong> is 264 pages on what the food industry doesn't want
you to understand — and exactly what to do about it. No diet. No rules. Just the research
that changes how you see every food decision.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Available in every format:</p>
</td></tr>
<tr><td style="padding:0 32px 8px;">
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:20px 32px 32px;border-top:1px solid #f3f4f6;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
To your health,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


# Template renderer lookup
_RENDERERS = {
    "book_delivery": _render_book_delivery,
    "did_you_get_this": _render_did_you_get_this,
    "big_benefit": _render_big_benefit,
    "got_questions": _render_got_questions,
    "social_proof": _render_social_proof,
    "im_surprised": _render_im_surprised,
    "last_chance": _render_last_chance,
    "buy_now_offer": _render_buy_now_offer,
}


# ── Sending ───────────────────────────────────────────────────────────────────

async def send_nurture_email(to_email: str, first_name: str, template_id: str, subject: str, **kwargs) -> bool:
    """Send a single nurture email via SendGrid."""
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping nurture email")
        return False

    renderer = _RENDERERS.get(template_id)
    if not renderer:
        logger.error(f"Unknown nurture template: {template_id}")
        return False

    name = first_name or "there"
    # Resolve dynamic subject placeholders
    variant = kwargs.pop("variant", "")
    c = _get_copy(variant)
    rendered_subject = (
        subject
        .replace("{first_name}", name)
        .replace("{big_benefit}", c["big_benefit"])
        .replace("{topic}", c["topic"])
    )
    html_body = renderer(name, variant=variant, **kwargs)

    # Resolve brand-specific sender
    brand = _get_brand_config(variant)
    payload = {
        "personalizations": [{
            "to": [{"email": to_email}],
            **({"bcc": [{"email": BOOK_EMAIL_BCC}]} if BOOK_EMAIL_BCC and BOOK_EMAIL_BCC.lower() != to_email.lower() else {}),
        }],
        "from": {"email": brand["from_email"], "name": brand["from_name"]},
        "subject": rendered_subject,
        "content": [{"type": "text/html", "value": html_body}],
        "tracking_settings": {
            "click_tracking": {"enable": True, "enable_text": False},
            "open_tracking": {"enable": True},
        },
        "categories": ["nurture", template_id],
        "custom_args": {"template_id": template_id, "lead_email": to_email},
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (200, 201, 202):
                logger.info(f"Nurture email [{template_id}] sent to {to_email}")
                return True
            elif resp.status_code == 401 and "credits" in resp.text.lower():
                logger.error(f"SendGrid credit limit exceeded — aborting cron run")
                raise _SendGridCreditExhausted(resp.text)
            else:
                logger.error(f"SendGrid nurture error {resp.status_code}: {resp.text}")
                return False
        except _SendGridCreditExhausted:
            raise
        except Exception as e:
            logger.error(f"Nurture email delivery failed: {e}")
            return False


async def trigger_day0(email: str, first_name: str, variant: str = "") -> bool:
    """Send the Day 0 book_delivery nurture email and advance stage."""
    sent = await send_nurture_email(
        to_email=email,
        first_name=first_name,
        template_id="book_delivery",
        subject="Your free copy is here, {first_name}",
        variant=variant,
    )
    if sent:
        # Advance to stage 1 so cron doesn't resend Day 0
        try:
            from src.services.book_leads_service import _get_firestore, COLLECTION, mark_delivered

            await mark_delivered(email)
            db = _get_firestore()
            now = datetime.now(timezone.utc)
            query = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1)
            async for doc in query.stream():
                created_at = doc.to_dict().get("created_at", now)
                await doc.reference.update({
                    "nurture_stage": 1,
                    "nurture_next_at": created_at + timedelta(days=1),
                    "nurture_book_delivery_sent_at": now,
                })
        except Exception as e:
            logger.warning(f"Failed to advance nurture stage after Day 0: {e}")
    return sent


async def trigger_buy_now(email: str, first_name: str, variant: str = "") -> bool:
    """Send immediate buy-now email and close free-book nurture for this lead."""
    sent = await send_nurture_email(
        to_email=email,
        first_name=first_name,
        template_id="buy_now_offer",
        subject="Start now, {first_name} - your copy is ready",
        variant=variant,
    )
    if sent:
        try:
            from src.services.book_leads_service import _get_firestore, COLLECTION

            db = _get_firestore()
            now = datetime.now(timezone.utc)
            query = (
                db.collection(COLLECTION)
                .where("email", "==", email.lower().strip())
                .limit(1)
            )
            async for doc in query.stream():
                await doc.reference.update({
                    "funnel_stage": "buyer_intent_contacted",
                    "sequence_status": "completed",
                    "nurture_buy_now_offer_sent_at": now,
                })
        except Exception as e:
            logger.warning(f"Failed to update buy-now status: {e}")
    return sent


# ── Cron processor ────────────────────────────────────────────────────────────

class _SendGridCreditExhausted(Exception):
    """Raised when SendGrid returns 401 credit limit exceeded — aborts the cron loop."""


async def process_pending_nurture() -> dict:
    """Process all leads with pending nurture emails. Called by cron."""
    from src.services.book_leads_service import _get_firestore, COLLECTION

    db = _get_firestore()
    now = datetime.now(timezone.utc)
    stats = {"processed": 0, "sent": 0, "errors": 0, "completed": 0}

    # Find active leads whose next nurture is due
    query = (
        db.collection(COLLECTION)
        .where("sequence_status", "==", "active")
        .where("nurture_next_at", "<=", now)
        .limit(50)
    )

    async for doc in query.stream():
        data = doc.to_dict()
        stats["processed"] += 1
        email = data.get("email", "")
        first_name = data.get("first_name", "")
        current_stage = data.get("nurture_stage", 0)
        variant = data.get("utm_content", "")

        # Find the next stage to send
        next_entry = None
        for stage, days, template_id, subject in NURTURE_SEQUENCE:
            if stage == current_stage:
                next_entry = (stage, days, template_id, subject)
                break

        if not next_entry:
            # Sequence complete
            await doc.reference.update({"sequence_status": "completed"})
            stats["completed"] += 1
            continue

        _, _, template_id, subject = next_entry

        try:
            sent = await send_nurture_email(
                email, first_name, template_id, subject, variant=variant,
            )
        except _SendGridCreditExhausted:
            stats["credit_exhausted"] = True
            logger.error("SendGrid credits exhausted — stopping cron run early")
            break

        if sent:
            stats["sent"] += 1
            # Advance to next stage
            next_stage = current_stage + 1
            # Find next stage's delay
            next_delay_days = None
            for stage, days, _, _ in NURTURE_SEQUENCE:
                if stage == next_stage:
                    next_delay_days = days
                    break

            if next_delay_days is not None:
                created_at = data.get("created_at", now)
                next_at = created_at + timedelta(days=next_delay_days)
                await doc.reference.update({
                    "nurture_stage": next_stage,
                    "nurture_next_at": next_at,
                    "send_failure_count": 0,
                    f"nurture_{template_id}_sent_at": now,
                })
            else:
                # No more stages — mark completed
                await doc.reference.update({
                    "nurture_stage": next_stage,
                    "sequence_status": "completed",
                    "send_failure_count": 0,
                    f"nurture_{template_id}_sent_at": now,
                })
                stats["completed"] += 1
        else:
            stats["errors"] += 1
            failure_count = data.get("send_failure_count", 0) + 1
            try:
                from src.services.book_leads_service import mark_send_failed
                await mark_send_failed(doc.reference, failure_count)
            except Exception as fe:
                logger.warning(f"Failed to record send failure for {email}: {fe}")

    logger.info(f"Nurture cron: {stats}")
    return stats
