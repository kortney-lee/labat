"""
B2B Nurture Service
5-email outreach sequence for business leads: bookstores, libraries, podcasts,
blogs, churches, schools.

Same visual style as the consumer nurture emails. Personal story-first,
soft book purchase section, reply CTA.

Schedule:
  Day 0:  Why I wrote the book + B2B intro
  Day 3:  Who the book reaches + B2B angle
  Day 7:  Social proof + program details
  Day 14: Direct ask
  Day 21: Last note
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
FROM_EMAIL = os.getenv("B2B_FROM_EMAIL", "info@vowels.org")
FROM_NAME  = os.getenv("B2B_FROM_NAME",  "Kortney Lee")
BCC_EMAIL  = os.getenv("BOOK_EMAIL_BCC", "kortney@wihy.ai")

UNSUBSCRIBE_URL    = "https://whatishealthy.org/unsubscribe"
WHOLESALE_URL      = "https://whatishealthy.org/wholesale"
MEDIA_KIT_URL      = "https://whatishealthy.org/media-kit"
LIBRARY_URL        = "https://whatishealthy.org/libraries"

# IngramSpark direct purchase (shows book cover)
INGRAM_FEMALE_URL  = "https://shop.ingramspark.com/b/084?params=KdF9tI0DBCGxHsXvFp5EzonT2Vjy0qlWQPnReIEveSF"
INGRAM_MALE_URL    = "https://shop.ingramspark.com/b/084?params=ortH8rLGOSivIH3DLwamRSP1VHE5GqBpHxkPRViMMmp"
COVER_FEMALE_IMG   = "https://image-hub-cloud.lightningsource.com/2011-04-01/Images/front_cover/x200/sku/9798822989481.jpg?viewkey=cbe6f8e435b911f25bba9f623f1beeb0b63fe7797d202afd9ae0389ba174c2fd"
COVER_MALE_IMG     = "https://image-hub-cloud.lightningsource.com/2011-04-01/Images/front_cover/x200/sku/9798822981973.jpg?viewkey=6a6da316aacd73878e33dcdc077f227bfcc0f50c9d3bade6d01aeae2d7eae624"

# Amazon / other formats
AMAZON_PAPERBACK_URL = "https://www.amazon.com/dp/B0FJ2494LH"
AMAZON_HARDCOVER_URL = "https://www.amazon.com/dp/B0FJ23J6JQ"
AMAZON_KINDLE_URL    = "https://www.amazon.com/dp/B0DL7Z7NFL"
AMAZON_AUDIBLE_URL   = "https://www.amazon.com/dp/B0GVWM74FR"


# ── Copy by business type ─────────────────────────────────────────────────────

_COPY = {
    "bookstore": {
        "d0_subject":  "Wholesale info for What Is Healthy?",
        "d3_subject":  "Why this book has been moving off shelves",
        "d7_subject":  "What independent bookstores are saying",
        "d14_subject": "Can we get 10 copies on your shelf?",
        "d21_subject": "Last note — What Is Healthy?",
        "d0_b2b": "I'm reaching out because I'd love to get the book on your shelves. We offer wholesale pricing for orders of 10+ copies with standard returnable terms. Happy to send a review copy first so you can see if it's the right fit for your customers.",
        "d0_cta_label": "View Wholesale Info",
        "d0_cta_url": WHOLESALE_URL,
        "d3_b2b": "Most stores put it in the health/wellness section, but it also moves in self-help and near registers as an impulse buy. The cover is a bright green that stands out, and the title does a lot of work on its own. Readers who pick it up tend to already be health-curious — they've read labels, wondered about ingredients, felt like the system wasn't designed with them in mind. This book validates that feeling and gives them somewhere to go with it.",
        "d3_cta_label": "View Wholesale Terms",
        "d3_cta_url": WHOLESALE_URL,
        "d7_b2b": 'A few things we\'ve heard from stores: <em>"It tends to self-merchandise — people pick it up, read the back, and put it back. Then they come back for it."</em> We also support stores with signage, author Q&amp;A sessions (in person or virtual), and reading group materials.',
        "d14_ask": "I'd love to get 10 copies on your shelf and see how your customers respond. If they move, we reorder. If they don't, standard returns apply. What would it take to make that happen?",
        "d21_close": "I don't want to keep following up if it's not the right fit — I just believe in the book and know your customers would too. If interest shifts, we're always here.",
    },
    "library": {
        "d0_subject":  "What Is Healthy? — library acquisition info",
        "d3_subject":  "What community libraries are doing with this book",
        "d7_subject":  "Discussion guide, author Q&A, and program support",
        "d14_subject": "Happy to support your acquisition request",
        "d21_subject": "Last note — What Is Healthy? for your community",
        "d0_b2b": "I'm reaching out about getting <em>What Is Healthy?</em> into your library collection. Libraries have used it for community wellness programs, book clubs, and as a general health reference. I'm happy to provide a complimentary review copy, along with a reading group guide and program support materials.",
        "d0_cta_label": "Library Acquisition Info",
        "d0_cta_url": LIBRARY_URL,
        "d3_b2b": "Libraries that have added the book have used it in a few ways: 4&ndash;6 week community health discussions (we provide a discussion guide), book clubs where the everyday-life angle generates strong conversation, and author events that tend to draw well because the topic is relevant to almost everyone.",
        "d3_cta_label": "See Library Program Info",
        "d3_cta_url": LIBRARY_URL,
        "d7_b2b": "Available to libraries that carry the book: reading group discussion guide (12 questions), community health program curriculum (6 sessions), author Q&amp;A (virtual or in-person), and promotional materials. All free. I want the book to actually be read and used, not just sit on a shelf.",
        "d14_ask": "I'd love to make sure your library has a copy and the materials to make it useful to your community. What's the best way to support your acquisition process from here?",
        "d21_close": "If there's anything I can do to help with the acquisition review — a press kit, additional review materials, or a reference call with another librarian who's used the book — just reply and let me know.",
    },
    "podcast": {
        "d0_subject":  "Podcast guest — What Is Healthy? with Kortney Lee",
        "d3_subject":  "Episode angles that tend to generate strong response",
        "d7_subject":  "What listeners take away from these conversations",
        "d14_subject": "Are we booking a date?",
        "d21_subject": "Last note on the podcast booking",
        "d0_b2b": "I'm an experienced speaker and can adapt the conversation to what resonates most with your audience — whether that's weight loss, feeding kids, food budgets, or the bigger picture of community health. Media kit and talking points are ready whenever you need them.",
        "d0_cta_label": "View Media Kit & Talking Points",
        "d0_cta_url": MEDIA_KIT_URL,
        "d3_b2b": 'A few angles that generate strong listener response: <strong>The 5-second label test</strong> — a simple way to know if a food is worth eating before you even read the ingredients. <strong>Why your grandmother\'s food was healthier</strong> — the structural changes in the food supply since the 1970s. <strong>The working-class health gap</strong> — why wellness feels like a luxury and what that costs communities. <strong>What 100-year-olds actually eat</strong> — Blue Zones research distilled into practical takeaways.',
        "d3_cta_label": "See All Episode Topics",
        "d3_cta_url": MEDIA_KIT_URL,
        "d7_b2b": 'What listeners say after these conversations: <em>"I went straight to the store and started reading labels differently."</em> <em>"I bought copies for my whole family."</em> <em>"This is the episode I keep sending people."</em> I bring real research, personal story, and practical takeaways your listeners can actually use.',
        "d14_ask": "I'd love to make this happen. What does your booking calendar look like? I'm flexible on format — long-form, short-form, video or audio only.",
        "d21_close": "If the timing doesn't work right now, no problem — just keep me in mind. The offer stands whenever it makes sense.",
    },
    "blog": {
        "d0_subject":  "Review copy + interview — What Is Healthy?",
        "d3_subject":  "Angles your readers will connect with",
        "d7_subject":  "What other writers have done with the book",
        "d14_subject": "Would an exclusive excerpt help?",
        "d21_subject": "Last note — covering What Is Healthy?",
        "d0_b2b": "I'd love for your readers to know about <em>What Is Healthy?</em> I'm happy to provide a complimentary review copy (digital or print), an exclusive excerpt, or an interview — whatever format works best for your publication.",
        "d0_cta_label": "Request a Review Copy",
        "d0_cta_url": MEDIA_KIT_URL,
        "d3_b2b": "Angles that connect strongly with readers: <strong>Label deception</strong> — &ldquo;natural flavors&rdquo; appears on 80% of packaged food and most people don't know what it means. <strong>The budget angle</strong> — eating well isn't just a willpower problem, it's an economic problem. <strong>The family angle</strong> — what to feed kids when the food system is working against you.",
        "d3_cta_label": "See Media Kit",
        "d3_cta_url": MEDIA_KIT_URL,
        "d7_b2b": "What other writers have done: an exclusive excerpt from Chapter 3 (on &ldquo;natural flavors&rdquo; — we can provide this as a standalone piece), Q&amp;A-style interviews (written or live), and guest posts from me on any of the angles above — fully written, original, not published elsewhere.",
        "d14_ask": "Would an exclusive excerpt from Chapter 3 help get this on your editorial calendar? I can have it to you within a few days.",
        "d21_close": "If the timing or angle doesn't fit right now, no problem. The offer for a review copy or excerpt stands whenever you're ready.",
    },
    "church": {
        "d0_subject":  "What Is Healthy? — church & community wellness programs",
        "d3_subject":  "How faith communities are using this book",
        "d7_subject":  "Small group guide, bulk pricing, and speaking",
        "d14_subject": "Ready to support your community health program",
        "d21_subject": "Last note — What Is Healthy? for your congregation",
        "d0_b2b": "The book has been used in church wellness programs, small group studies, and community health events. I love supporting faith communities doing this work. Bulk pricing is available for group studies (10+ copies), and I'm available to speak at health-focused church events.",
        "d0_cta_label": "View Bulk Order & Speaking Info",
        "d0_cta_url": WHOLESALE_URL,
        "d3_b2b": "Faith communities have used the book for 6-week small group studies (we provide a discussion guide that works well for groups of 8&ndash;15), health ministry resources, and community health events. The conversation about chronic illness and community care tends to land particularly well.",
        "d3_cta_label": "Learn About Community Programs",
        "d3_cta_url": WHOLESALE_URL,
        "d7_b2b": "Available to faith communities: small group discussion guide (6 sessions), bulk pricing (10+ copies at wholesale), author talk (in person or virtual, 45&ndash;60 minutes), and health ministry support materials. My grandmother passed from cancer after years of type 2 diabetes and high blood pressure — that's the personal reason I care about getting this into communities that are paying attention.",
        "d14_ask": "I'd love to support your community with this. What does your health ministry or wellness program look like, and how can we best fit into it?",
        "d21_close": "Whether it's a few books for a small group or a full community event, we're here whenever the timing is right. Just reply and we'll make it work.",
    },
    "school": {
        "d0_subject":  "What Is Healthy? — school nutrition & health programs",
        "d3_subject":  "How schools are using the book in health classes",
        "d7_subject":  "Curriculum resources, assemblies, and parent workshops",
        "d14_subject": "Ready to support your nutrition program",
        "d21_subject": "Last note — What Is Healthy? for your school",
        "d0_b2b": "I'm reaching out about bringing <em>What Is Healthy?</em> into your school's health or nutrition program. We offer classroom and program pricing (10+ copies), and I'm available for student assemblies, parent workshops, and teacher professional development sessions.",
        "d0_cta_label": "View School Program Info",
        "d0_cta_url": LIBRARY_URL,
        "d3_b2b": "Schools have found a few entry points that work well: parent education workshops (&ldquo;What's really in your kid's lunch?&rdquo; draws well), health class supplemental reading (Chapters 1&ndash;3 work as a standalone unit on label reading for high school), and student assemblies on the connection between food, focus, and long-term health.",
        "d3_cta_label": "See Program Options",
        "d3_cta_url": LIBRARY_URL,
        "d7_b2b": "Resources available to schools: program pricing (10+ copies at educational rates), discussion guide aligned to health curriculum standards, student assembly (45 minutes, Q&amp;A included), parent workshop (60&ndash;90 minutes), and teacher PD session on food literacy. The goal is for students to leave with one or two things they can actually apply — reading a label, making a better choice at the store.",
        "d14_ask": "What would be most useful for your school right now — books for a class, a parent event, or a student assembly? I'd love to figure out the right fit.",
        "d21_close": "School programs take time to put together and I understand calendars get full. Whenever the timing is right, we're here to support your nutrition program.",
    },
    "other": {
        "d0_subject":  "What Is Healthy? — partnership inquiry",
        "d3_subject":  "A few ways we work with partners",
        "d7_subject":  "What we've built with other organizations",
        "d14_subject": "Ready to make something happen",
        "d21_subject": "Last note from Kortney",
        "d0_b2b": "Whether you're thinking about bulk orders, a content partnership, an author event, or something else entirely — I'm open to the conversation. Hit reply and tell me what you're imagining.",
        "d0_cta_label": "Start the Conversation",
        "d0_cta_url": WHOLESALE_URL,
        "d3_b2b": "A few ways we work with organizations: bulk orders (wholesale pricing for 10+ copies), author events (in-person or virtual), content partnerships (exclusive excerpts, guest posts, interviews), and community programs (reading guides, curriculum materials, health program support).",
        "d3_cta_label": "See Partnership Options",
        "d3_cta_url": WHOLESALE_URL,
        "d7_b2b": "The best partnerships we've built have been with organizations that put the book in front of the right people at the right time. My grandmother passed from cancer after years of type 2 diabetes and high blood pressure — three chronic illnesses. That's what drove the research behind this book, and why I care about getting it into communities that are paying attention to their health.",
        "d14_ask": "What would a partnership look like for you? I'd love to find a way to make this work.",
        "d21_close": "If the timing wasn't right or something shifted, no problem — just reply whenever it does make sense.",
    },
}


def _get(bt: str) -> dict:
    return _COPY.get(bt, _COPY["other"])


# ── Shared components (match consumer email style) ────────────────────────────

def _wrap(content: str) -> str:
    """560px white wrapper matching the consumer nurture email style."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;">
{content}
<tr><td style="padding:16px 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:0 0 6px;font-size:13px;line-height:1.6;color:#6b7280;">
You're receiving this because you reached out about <em>What Is Healthy?</em> or a partnership with Vowels.</p>
<p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;">
<a href="{UNSUBSCRIBE_URL}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
&middot; Kortney Lee &middot; partnerships@vowels.org
</p></td></tr>
</table></td></tr></table></body></html>"""


def _cta_btn(label: str, url: str) -> str:
    return (
        f'<a href="{url}" target="_blank" style="display:inline-block;background:#1e40af;'
        f'color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;'
        f'padding:12px 24px;border-radius:6px;">{label}</a>'
    )


def _book_covers() -> str:
    """Two IngramSpark book cover cards, email-safe table layout."""
    def cover_card(img: str, link: str, label: str) -> str:
        return (
            f'<td width="50%" style="padding:0 8px 0 0;vertical-align:top;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid #e5e7eb;border-radius:8px;">'
            f'<tr><td align="center" style="padding:12px 12px 8px;">'
            f'<a href="{link}" target="_blank">'
            f'<img src="{img}" width="80" alt="What Is Healthy?" '
            f'style="display:block;border:0;" /></a></td></tr>'
            f'<tr><td style="padding:0 12px 6px;">'
            f'<p style="margin:0;font-size:13px;font-weight:700;color:#111827;'
            f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
            f'What Is Healthy?</p>'
            f'<p style="margin:2px 0 0;font-size:12px;color:#6b7280;font-style:italic;">'
            f'Kortney O. Lee &mdash; {label}</p></td></tr>'
            f'<tr><td align="center" style="padding:8px 12px 12px;">'
            f'<a href="{link}" target="_blank" '
            f'style="display:inline-block;background:#FEBE10;color:#000000;'
            f'font-size:14px;font-weight:700;text-decoration:none;'
            f'padding:8px 20px;border-radius:8px;">Buy Now</a>'
            f'</td></tr></table></td>'
        )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8px;">'
        f'<tr>'
        + cover_card(COVER_FEMALE_IMG, INGRAM_FEMALE_URL, "Female cover")
        + cover_card(COVER_MALE_IMG,   INGRAM_MALE_URL,   "Male cover")
        + f'</tr></table>'
        f'<p style="margin:8px 0 0;font-size:13px;line-height:1.7;color:#6b7280;">'
        f'Also on '
        f'<a href="{AMAZON_PAPERBACK_URL}" style="color:#1e40af;text-decoration:underline;">Amazon Paperback</a>'
        f' &middot; '
        f'<a href="{AMAZON_HARDCOVER_URL}" style="color:#1e40af;text-decoration:underline;">Hardcover</a>'
        f' &middot; '
        f'<a href="{AMAZON_KINDLE_URL}" style="color:#1e40af;text-decoration:underline;">Kindle</a>'
        f' &middot; '
        f'<a href="{AMAZON_AUDIBLE_URL}" style="color:#1e40af;text-decoration:underline;">Audible</a>'
        f'</p>'
    )


def _sig() -> str:
    return (
        '<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">'
        'Talk soon,<br/><strong>Kortney Lee</strong><br/>'
        '<span style="font-size:14px;color:#6b7280;">Author, <em>What Is Healthy?</em>'
        ' &middot; partnerships@vowels.org</span></p>'
    )


def _reply_cta(question: str) -> str:
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0">'
        f'<tr><td style="padding:20px 0 0;border-top:1px solid #f3f4f6;">'
        f'<p style="margin:0;font-size:15px;line-height:1.7;color:#374151;">'
        f'<strong>{question}</strong> Hit reply &mdash; I read every response.</p>'
        f'</td></tr></table>'
    )


# ── Why I wrote the book — the personal story (used in Day 0) ─────────────────

_WHY_I_WROTE_IT = """<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My grandmother was one of the most vibrant people I knew. She was also someone who, for years,
lived with type 2 diabetes, high blood pressure, and cancer. Three chronic illnesses at once.
She died from the cancer. I've spent a long time thinking about whether that was inevitable.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The research I found while writing this book suggests it wasn't. 60% of Americans have at least
one chronic illness. 51% have two or more. These aren't just individual health failures &mdash;
they're a system that was never designed to help most people be well.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
That's what <em>What Is Healthy?</em> is about. Not a diet. Not a fitness plan. A clear-eyed
look at what the food industry has done, what the research actually shows, and what people can
realistically do about it &mdash; especially people who don't have the time or money to make
wellness a full-time job.</p>"""


# ── Email templates ───────────────────────────────────────────────────────────

def _render_b2b_day0(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    company = f" at {company_name}" if company_name else ""
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
{_WHY_I_WROTE_IT}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:16px;line-height:1.8;color:#374151;">
I'm reaching out because I think the book could be a real fit for {f"<strong>{company_name}</strong>" if company_name else "what you do"}{company and ""}.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['d0_b2b']}</p>
<p style="margin:0 0 24px;font-size:16px;line-height:1.8;color:#374151;">
{_cta_btn(c['d0_cta_label'], c['d0_cta_url'])}</p>
<p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#374151;">
Or pick up a copy yourself &mdash; there are two cover options:</p>
</td></tr>
<tr><td style="padding:0 40px 24px;">
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Does this sound like something that could work for you?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">
{_sig()}
</td></tr>""")


def _render_b2b_day3(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Following up on my note from a few days ago &mdash; wanted to share a bit more about who the book reaches and why it tends to resonate.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
The readers who connect with it most are adults 30&ndash;65 who are frustrated with conflicting
health advice and want a research-backed, agenda-free perspective. Strong resonance with families,
faith communities, and health-conscious individuals who feel like the system isn't working for them.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['d3_b2b']}</p>
<p style="margin:0 0 24px;font-size:16px;line-height:1.8;color:#374151;">
{_cta_btn(c['d3_cta_label'], c['d3_cta_url'])}</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 8px;font-size:15px;font-weight:600;color:#374151;">
The book &mdash; two cover options:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Any questions I can answer?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">
{_sig()}
</td></tr>""")


def _render_b2b_day7(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['d7_b2b']}</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
264 pages. Paperback, hardcover, Kindle, and Audible. Written for a general audience &mdash;
not a textbook, not a diet book. Something people will actually read and share.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 8px;font-size:15px;font-weight:600;color:#374151;">
Order a copy to review:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("What would make this easy to move forward?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">
{_sig()}
</td></tr>""")


def _render_b2b_day14(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['d14_ask']}</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Just hit reply &mdash; that's the fastest way to make this happen.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 8px;font-size:15px;font-weight:600;color:#374151;">
The book &mdash; in case you want to read it first:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:20px 40px 32px;border-top:1px solid #e5e7eb;">
{_sig()}
</td></tr>""")


def _render_b2b_day21(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Last note from me &mdash; I don't want to fill your inbox.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['d21_close']}</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
partnerships@vowels.org &mdash; reach out any time.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_book_covers()}
</td></tr>
<tr><td style="padding:20px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
All the best,<br/><strong>Kortney</strong></p>
</td></tr>""")


_B2B_SEQUENCE = [
    (0,  0,  "b2b_day0",   lambda bt: _get(bt)["d0_subject"],  _render_b2b_day0),
    (1,  3,  "b2b_day3",   lambda bt: _get(bt)["d3_subject"],  _render_b2b_day3),
    (2,  7,  "b2b_day7",   lambda bt: _get(bt)["d7_subject"],  _render_b2b_day7),
    (3,  14, "b2b_day14",  lambda bt: _get(bt)["d14_subject"], _render_b2b_day14),
    (4,  21, "b2b_day21",  lambda bt: _get(bt)["d21_subject"], _render_b2b_day21),
]


# ── Sending ───────────────────────────────────────────────────────────────────

async def _send(to_email: str, subject: str, html: str) -> bool:
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping B2B email")
        return False
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
        "categories": ["b2b-nurture"],
    }
    if BCC_EMAIL and BCC_EMAIL.lower() != to_email.lower():
        payload["personalizations"][0]["bcc"] = [{"email": BCC_EMAIL}]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
            )
        if r.status_code in (200, 201, 202):
            logger.info("B2B email sent: %s subject=%r", to_email, subject)
            return True
        logger.error("B2B SendGrid error %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("B2B email send failed: %s", e)
    return False


async def trigger_b2b_day0(
    email: str, first_name: str, business_type: str, company_name: str = ""
) -> bool:
    """Send Day 0 B2B email immediately on lead capture."""
    bt = business_type or "other"
    html = _render_b2b_day0(first_name, bt, company_name)
    subject = _get(bt)["d0_subject"]
    return await _send(email, subject, html)


async def process_pending_b2b_nurture() -> dict:
    """
    Cron: send pending B2B nurture emails.
    Reads book_leads where lead_type='b2b' and sequence_status='active'.
    """
    from datetime import datetime, timezone, timedelta
    from google.cloud import firestore

    db = firestore.AsyncClient(project=os.getenv("GCP_PROJECT", "wihy-ai"))
    now = datetime.now(timezone.utc)
    sent = skipped = errors = 0

    query = (
        db.collection("book_leads")
        .where("lead_type", "==", "b2b")
        .where("sequence_status", "==", "active")
        .where("nurture_next_at", "<=", now)
        .limit(50)
    )

    async for doc in query.stream():
        d = doc.to_dict()
        stage = d.get("nurture_stage", 0)
        if stage >= len(_B2B_SEQUENCE):
            await doc.reference.update({"sequence_status": "completed"})
            continue

        _, days, template_id, subject_fn, render_fn = _B2B_SEQUENCE[stage]
        email = d.get("email", "")
        first_name = d.get("first_name", "")
        business_type = d.get("business_type", "other")
        company_name = d.get("company_name", "")

        try:
            html = render_fn(first_name, business_type, company_name)
            subject = subject_fn(business_type)
            ok = await _send(email, subject, html)

            next_stage = stage + 1
            update: dict = {
                "nurture_stage": next_stage,
                f"nurture_{template_id}_sent_at": now,
            }
            if next_stage < len(_B2B_SEQUENCE):
                next_days = _B2B_SEQUENCE[next_stage][1]
                update["nurture_next_at"] = now + timedelta(days=next_days)
                update["sequence_status"] = "active"
            else:
                update["sequence_status"] = "completed"

            await doc.reference.update(update)
            if ok:
                sent += 1
            else:
                errors += 1
        except Exception as e:
            logger.error("B2B nurture error for %s: %s", email, e)
            errors += 1

    return {"sent": sent, "skipped": skipped, "errors": errors, "ran_at": now.isoformat()}
