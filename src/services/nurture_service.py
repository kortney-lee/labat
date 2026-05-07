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
WIHY_SUB_URL = "https://wihy.ai/subscription"
WIHY_ICON_URL = "https://storage.googleapis.com/wihy-web-assets/images/eden/eden-icon.png"
BOOK_URL = "https://whatishealthy.org"
UNSUBSCRIBE_URL = "https://whatishealthy.org/unsubscribe"

CG_URL = "https://communitygroceries.com"
CG_SUB_URL = "https://communitygroceries.com/subscription"
CG_ICON_URL = "https://storage.googleapis.com/wihy-web-assets/images/cora/cora-icon.png"

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
    """2-column pill-button grid for all 6 purchase formats. Email-safe tables."""
    def cell(label: str, url: str, color: str) -> str:
        return (
            f'<td width="50%" style="padding:0 4px 8px;">'
            f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'<td align="center" bgcolor="{color}" style="border-radius:6px;">'
            f'<a href="{url}" target="_blank"'
            f' style="display:block;padding:13px 10px;color:#ffffff;font-size:14px;'
            f'font-weight:700;text-decoration:none;line-height:1.3;'
            f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
            f'{label}</a></td></tr></table></td>'
        )
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 4px;">'
        '<tr>'
        + cell("Ship Paperback<br/>Female Cover", PAPERBACK_URL_FEMALE, "#15803d")
        + cell("Ship Paperback<br/>Male Cover",   PAPERBACK_URL_MALE,   "#15803d")
        + '</tr><tr>'
        + cell("Amazon Paperback",                AMAZON_PAPERBACK_URL, "#c45000")
        + cell("Amazon Hardcover",                AMAZON_HARDCOVER_URL, "#1f2937")
        + '</tr><tr>'
        + cell("Kindle Edition",                  AMAZON_KINDLE_URL,    "#1a5c8a")
        + cell("Audible Audiobook",               AMAZON_AUDIBLE_URL,   "#b45309")
        + '</tr></table>'
    )


def _brand_cards() -> str:
    """Side-by-side Eden + Cora brand cards with images, positioning, and CTA buttons."""
    return f"""
<table width="100%" cellpadding="0" cellspacing="0">
<tr>
  <!-- Eden card -->
  <td width="50%" valign="top" style="padding:0 6px 0 0;">
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
      <tr>
        <td align="center" bgcolor="#1e1b4b" style="padding:20px 16px 12px;">
          <img src="{WIHY_ICON_URL}" width="72" height="72" alt="Eden by WIHY"
               style="display:block;margin:0 auto 10px;border-radius:50%;border:0;" />
          <p style="margin:0;font-size:15px;font-weight:700;color:#ffffff;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
            Eden by WIHY</p>
        </td>
      </tr>
      <tr>
        <td style="padding:14px 14px 6px;">
          <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#1e1b4b;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
            For your overall health goals</p>
          <p style="margin:0;font-size:12px;line-height:1.7;color:#4b5563;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
            Ask any food or health question. Scan labels. Track progress. Eden is built for
            people who want to understand their health from the inside out.</p>
        </td>
      </tr>
      <tr>
        <td align="center" style="padding:12px 14px 16px;">
          <table cellpadding="0" cellspacing="0"><tr>
            <td align="center" bgcolor="#1e1b4b" style="border-radius:5px;">
              <a href="{WIHY_SUB_URL}" target="_blank"
                 style="display:block;padding:10px 18px;color:#ffffff;font-size:13px;
                 font-weight:700;text-decoration:none;
                 font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
                Get Started Free</a>
            </td>
          </tr></table>
        </td>
      </tr>
    </table>
  </td>
  <!-- Cora card -->
  <td width="50%" valign="top" style="padding:0 0 0 6px;">
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
      <tr>
        <td align="center" bgcolor="#f0fdf4" style="padding:20px 16px 12px;">
          <img src="{CG_ICON_URL}" width="72" height="72" alt="Cora by Community Groceries"
               style="display:block;margin:0 auto 10px;border:0;" />
          <p style="margin:0;font-size:15px;font-weight:700;color:#15803d;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
            Cora by CG</p>
        </td>
      </tr>
      <tr>
        <td style="padding:14px 14px 6px;">
          <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#15803d;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
            For singles &amp; empty nesters</p>
          <p style="margin:0;font-size:12px;line-height:1.7;color:#4b5563;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
            Real food at fair prices, sized for one or two. No bulk. No waste.
            Cora is built for people who want to eat well without buying for a family
            they no longer have.</p>
        </td>
      </tr>
      <tr>
        <td align="center" style="padding:12px 14px 16px;">
          <table cellpadding="0" cellspacing="0"><tr>
            <td align="center" bgcolor="#15803d" style="border-radius:5px;">
              <a href="{CG_SUB_URL}" target="_blank"
                 style="display:block;padding:10px 18px;color:#ffffff;font-size:13px;
                 font-weight:700;text-decoration:none;
                 font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
                Get Started Free</a>
            </td>
          </tr></table>
        </td>
      </tr>
    </table>
  </td>
</tr>
</table>"""


# ── Template builders ─────────────────────────────────────────────────────────

def _render_book_delivery(first_name: str, variant: str = "", **kw) -> str:
    """Day 0 — origin story with CDC-verified data in the callout block."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
My grandmother died of cancer. She had been living with type 2 diabetes and high blood pressure for years before that — three chronic conditions, stacked on top of each other.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
She was not unusual. Sixty percent of American adults have at least one chronic disease. More than half — 51 percent — have two or more. The three my grandmother carried were not a freak combination. They were the national average, multiplied.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
She was not careless. She read labels. She chose the low-fat versions, the heart-healthy cereals, the products marked "natural." By everything she understood, she was eating well.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
After she passed, I could not let it go. I needed to understand how someone who genuinely tried could still end up that sick. Two years of research later, here is what I found:</p>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<table width="100%" cellpadding="20" cellspacing="0" bgcolor="#f0f4ff"
       style="border-left:3px solid #1e40af;font-size:15px;line-height:1.8;color:#374151;">
<tr><td>
<p style="margin:0 0 16px;">More than half of all calories Americans eat today come from ultra-processed food — products engineered to override your body's ability to know when it has had enough. <em>(CDC, 2025)</em></p>
<p style="margin:0 0 16px;">The average American consumes 17 teaspoons of added sugar every day. The recommendation for women is 6. That gap does not come from candy. It comes from salad dressings, pasta sauces, yogurt, and bread — products sold as healthy options. <em>(CDC / American Heart Association)</em></p>
<p style="margin:0 0 16px;">Two in five American adults have prediabetes right now. Eight in ten have no idea. Their blood sugar is quietly damaging their organs for years while the labels they trust tell them everything is fine. <em>(CDC, 2026)</em></p>
<p style="margin:0;">The FDA permits approximately 3,000 flavoring substances under the single label "natural flavors." The term was not created to inform you. It was created to satisfy disclosure law while revealing as little as possible. <em>(FDA SAAF database)</em></p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<p style="margin:20px 0 20px;font-size:16px;line-height:1.8;color:#374151;">
None of this is fringe. It is in the regulatory filings, the peer-reviewed literature, and the industry's own documents. I spent two years pulling it together — no supplements to sell, no diet to push.</p>
<p style="margin:0 0 8px;font-size:16px;line-height:1.8;color:#374151;">
That became <strong>What Is Healthy?</strong> — 264 pages on what the food system does not want you to understand, and exactly what to do about it.</p>
</td></tr>
<tr><td align="center" style="padding:0 32px 16px;">
<img src="{BOOK_IMAGE_URL}" alt="What Is Healthy? book cover" width="160"
     style="display:block;margin:0 auto;border:0;" />
</td></tr>
<tr><td style="padding:0 32px 24px;">
{_all_format_buttons()}
<p style="margin:12px 0 0;font-size:13px;line-height:1.6;color:#9ca3af;text-align:center;">
Paperback ships free. Kindle and Audible available immediately.</p>
</td></tr>
<tr><td style="padding:16px 32px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
I will send you the opening chapter tomorrow.</p>
<p style="margin:20px 0 0;font-size:16px;line-height:1.8;color:#374151;">
Talk soon,<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_did_you_get_this(first_name: str, variant: str = "", **kw) -> str:
    """Day 1 — opening prose from the book, cut at cliffhanger. Buy CTA."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Here's how <strong>What Is Healthy?</strong> opens:</p>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<table width="100%" cellpadding="24" cellspacing="0" bgcolor="#f9fafb"
       style="border-left:3px solid #d1d5db;font-size:15px;line-height:1.9;color:#4b5563;">
<tr><td>
<p style="margin:0 0 16px;font-style:italic;">We are the sickest generation of Americans in recorded history.</p>
<p style="margin:0 0 16px;font-style:italic;">Not sicker because we are older. Not sicker because we have stopped trying. We are sicker in spite of knowing more about nutrition than any generation before us. We have more diet books, more health apps, more organic labels, and more wellness products than ever before — and the rates of obesity, type 2 diabetes, heart disease, and metabolic dysfunction keep climbing.</p>
<p style="margin:0 0 16px;font-style:italic;">Something is very wrong with the story we have been told about food.</p>
<p style="margin:0 0 16px;font-style:italic;">Most people feel it. They follow the advice and don't get better. They read the labels and still feel confused. They try harder and the needle doesn't move. And after a while, they start to wonder if the problem is them — if they're just not disciplined enough, not consistent enough, not smart enough about food.</p>
<p style="margin:0;font-style:italic;">They're not. The system is broken — and it was designed to be.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
The next chapter is called "How Did We Get Here?" It answers the question most people have been afraid to ask — because the answer means the problem was never you.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">The full 264-page book:</p>
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:16px 32px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">More coming in a few days.</p>
<p style="margin:20px 0 0;font-size:16px;line-height:1.8;color:#374151;">
Talk soon,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_big_benefit(first_name: str, variant: str = "", **kw) -> str:
    """Day 3 — natural flavors deep dive + variant-specific callout."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Here is something from the book I think about every time I walk through a grocery store.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Pick up any packaged food and find the ingredients list. Look for the words <strong>natural flavors</strong>.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
You will find it on almost everything — granola bars, yogurt, flavored water, crackers, baby food. It sounds harmless. The word "natural" is right there.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Here is what the label does not tell you: "natural flavors" is a legal catch-all that covers over 3,000 approved additives. Under FDA rules, any substance originally derived from a plant or animal — no matter how extensively processed — qualifies. The term was not created to inform you. It was created to satisfy disclosure requirements while revealing as little as possible.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
This is not an accident. It is a design decision made by an industry that spent decades lobbying for label language that sounds reassuring while saying nothing.</p>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<table width="100%" cellpadding="20" cellspacing="0" bgcolor="#fffbeb"
       style="border-left:3px solid #d97706;font-size:15px;line-height:1.8;color:#374151;">
<tr><td>
<p style="margin:0 0 8px;font-weight:700;color:#92400e;">What this means for {c['topic']}:</p>
<p style="margin:0 0 8px;">{c['bullet1']}</p>
<p style="margin:0 0 8px;">{c['bullet2']}</p>
<p style="margin:0;">{c['bullet3']}</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<p style="margin:20px 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['chapter_hook']}</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
There are 22 more chapters like this in the book. Each one changes how you read a label and what ends up in your cart.</p>
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:16px 32px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Talk soon,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_got_questions(first_name: str, variant: str = "", **kw) -> str:
    """Day 5 — the 5-second label test framework. Eden by WIHY plug."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
One of the most practical things in the book is a framework I call the 5-second label test. Here is the short version:</p>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<table width="100%" cellpadding="20" cellspacing="0" bgcolor="#f0fdf4"
       style="border-left:3px solid #16a34a;font-size:15px;line-height:1.8;color:#374151;">
<tr><td>
<p style="margin:0 0 12px;font-weight:700;color:#166534;">The 5-Second Label Test</p>
<p style="margin:0 0 10px;"><strong>1.</strong> Flip the package. Find the ingredients list, not the nutrition facts panel.</p>
<p style="margin:0 0 10px;"><strong>2.</strong> Count how many ingredients have names you could not say out loud in a normal conversation. Not technical abbreviations — just: would a person ever call this an ingredient at home?</p>
<p style="margin:0 0 10px;"><strong>3.</strong> If more than two fail that test, put it back.</p>
<p style="margin:0;">That is it. No chemistry degree needed. Five seconds and the back of the package.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<p style="margin:20px 0 20px;font-size:16px;line-height:1.8;color:#374151;">
The book has 11 more frameworks like this — for reading labels quickly, spotting hidden sugars across 61 different names, and identifying which products in the health food aisle are not what they claim to be.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
The full book with all 12 frameworks:</p>
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:0 32px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 12px;font-size:15px;line-height:1.8;color:#6b7280;">
Two tools I built alongside the book — both free to start:</p>
{_brand_cards()}
<p style="margin:14px 0 0;font-size:13px;line-height:1.7;color:#9ca3af;">
Eden is for anyone working on their overall health. Cora is for people cooking for one
or two who want real food without the bulk-store quantities.</p>
</td></tr>
<tr><td style="padding:16px 32px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Best,<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_social_proof(first_name: str, variant: str = "", **kw) -> str:
    """Day 7 — reader story as narrative. Specific outcome. Clean quote block."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
A reader named Sarah sent me a message a few weeks after reading the book.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
She had just finished Chapter 6 — the one about how grocery stores are physically designed to push you toward high-margin processed items — and walked into a store the next day. She noticed the end-cap displays. The eye-level shelf placement. The sale signage positioned exactly where foot traffic is highest.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
She wrote: "I walked out with half the things I normally buy and spent $40 less. I wasn't even trying. I just couldn't un-see it."</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
That is what the book is built to do. Not rules. Not a diet. Just the kind of understanding that, once you have it, changes every food decision automatically.</p>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<table width="100%" cellpadding="20" cellspacing="0" bgcolor="#f9fafb"
       style="border-left:3px solid #9ca3af;font-size:15px;line-height:1.9;color:#4b5563;">
<tr><td>
<p style="margin:0 0 8px;font-style:italic;">"I had my husband read Chapter 3 while I made dinner. He came downstairs and said: we have been lied to for 30 years. We cleared out half the pantry that night."</p>
<p style="margin:0;font-weight:600;color:#6b7280;">Marcus, reader</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<p style="margin:20px 0 16px;font-size:16px;line-height:1.8;color:#374151;">The full book:</p>
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:16px 32px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_im_surprised(first_name: str, variant: str = "", **kw) -> str:
    """Day 10 — dog-eared chapter tease with specific grocery store insight."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
There is one chapter in <strong>What Is Healthy?</strong> that readers dog-ear more than any other.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
It is not the natural flavors chapter. It is not the one about the food industry's lobbying history. It is called "What the Grocery Store Doesn't Want You to Know" — and it is the most immediately useful chapter in the book.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">One insight from it:</p>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<table width="100%" cellpadding="20" cellspacing="0" bgcolor="#eff6ff"
       style="border-left:3px solid #1e40af;font-size:15px;line-height:1.8;color:#374151;">
<tr><td>
<p style="margin:0 0 12px;">The average grocery store stocks 40,000 items. Research shows shoppers make 60 to 70 percent of purchase decisions in the store, not at home from a list.</p>
<p style="margin:0;">The layout — produce at the entrance, dairy at the back, end-caps and eye-level shelving throughout — is not designed for your convenience. It is designed by category managers whose job is to maximize impulse purchases of high-margin processed products.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<p style="margin:20px 0 20px;font-size:16px;line-height:1.8;color:#374151;">
The chapter walks through how this works aisle by aisle and gives you a shopping approach that routes around it. Most readers say they save $30 to $50 per trip just by changing how they walk through the store.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
That chapter alone is worth the cost of the book. There are 18 more like it.</p>
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:16px 32px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_last_chance(first_name: str, variant: str = "", **kw) -> str:
    """Day 14 — honest final email. No hard sell. Eden + CG close."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">This is my last email.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Over the past two weeks I shared why I wrote this book, the opening chapter, what is actually in "natural flavors," a framework for reading any label in five seconds, a reader who saved $40 her first grocery trip, and the chapter that changes how people walk through a store.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
All of it comes from one 264-page book built on two years of research.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
I am not going to push hard here. If any of this made you think differently about a label, a grocery aisle, or what you are feeding your family, the book is worth it. If none of it landed, it is probably not the right time, and that is fine.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">If you want it:</p>
{_all_format_buttons()}
</td></tr>
<tr><td style="padding:0 32px 16px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 6px;font-size:15px;line-height:1.8;color:#374151;">
Before I go — two things I built that come directly out of the same research as this book.</p>
<p style="margin:0 0 16px;font-size:15px;line-height:1.8;color:#6b7280;">
I started working on both of these the same year I started writing. They are different tools
for different people, but they come from the same place this book does.</p>
{_brand_cards()}
</td></tr>
<tr><td style="padding:16px 32px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Whatever you decide — keep reading those labels.</p>
<p style="margin:20px 0 0;font-size:16px;line-height:1.8;color:#374151;">
All the best,<br/>Kortney</p>
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
