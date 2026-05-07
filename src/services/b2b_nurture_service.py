"""
B2B Nurture Service
5-email outreach sequence for business leads: bookstores, libraries, podcasts,
blogs, churches, schools.

Schedule:
  Day 0:  Introduction + immediate offer
  Day 3:  Why this book sells / what audiences respond to
  Day 7:  Social proof + specific program details
  Day 14: Direct ask — let's make this happen
  Day 21: Last note from Kortney
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
FROM_EMAIL = os.getenv("B2B_FROM_EMAIL", "info@vowels.org")
FROM_NAME  = os.getenv("B2B_FROM_NAME",  "Kortney Lee")
BCC_EMAIL  = os.getenv("BOOK_EMAIL_BCC", "kortney@wihy.ai")
UNSUBSCRIBE_URL = "https://whatishealthy.org/unsubscribe"

WHOLESALE_URL  = "https://whatishealthy.org/wholesale"
MEDIA_KIT_URL  = "https://whatishealthy.org/media-kit"
LIBRARY_URL    = "https://whatishealthy.org/libraries"
BOOK_IMAGE_URL = "https://storage.googleapis.com/wihy-web-assets/images/book-green.jpg"
AMAZON_URL     = "https://www.amazon.com/dp/B0FJ2494LH"


# ── Copy by business type ─────────────────────────────────────────────────────

_COPY = {
    "bookstore": {
        "d0_subject":  "Wholesale info for What Is Healthy?",
        "d3_subject":  "Why this book has been moving off shelves",
        "d7_subject":  "What independent bookstores are saying",
        "d14_subject": "Can we get 10 copies on your shelf?",
        "d21_subject": "Last note from me — What Is Healthy?",
        "d0_intro": "I'm reaching out because I think <em>What Is Healthy?</em> would be a strong fit for your store.",
        "d0_context": "It's a 264-page book on the food industry, label deception, and what families can do about it — written for a general audience, not a medical one. It resonates especially well with readers who are frustrated with conflicting health advice and want something real.",
        "d0_offer": "We offer wholesale pricing for orders of 10+ copies with standard returnable terms. I'd love to get a copy in your hands first so you can see if it's the right fit for your customers.",
        "d0_cta_label": "Request a Wholesale Info Sheet",
        "d0_cta_url": WHOLESALE_URL,
        "d3_body": """Most independent bookstores that carry the book put it in the health/wellness section. But what's surprised us is that it also moves in the cooking section, the self-help section, and near registers as an impulse buy. The cover is distinct — a bright green that stands out — and the title does a lot of work for itself.<br/><br/>
The readers who pick it up tend to already be health-curious. They've read labels, they've wondered about ingredients, they've felt like the system wasn't designed with them in mind. This book validates that feeling and gives them somewhere to go with it.<br/><br/>
Happy to send a review copy if that would help.""",
        "d3_cta_label": "View Wholesale Terms",
        "d3_cta_url": WHOLESALE_URL,
        "d7_body": """A few things we've heard from stores that carry the book:<br/><br/>
<em>"It tends to self-merchandise — people pick it up, read the back, and put it back. Then they come back for it."</em><br/><br/>
<em>"Our wellness section customers are always looking for something that isn't a diet book. This one doesn't feel like a diet book."</em><br/><br/>
We also support stores with signage, author Q&amp;A sessions (in person or virtual), and reading group materials if you want to build a little program around it.""",
        "d7_cta_label": "See What Other Stores Are Doing",
        "d7_cta_url": WHOLESALE_URL,
        "d14_ask": "I'd love to get 10 copies on your shelf and see how your customers respond. If they move, we reorder. If they don't, standard returns apply. What would it take to make that happen?",
        "d21_close": "I don't want to keep following up if it's not the right fit for your store — I just believe in the book and know your customers would too. If timing or interest shifts, we're always here.",
    },
    "library": {
        "d0_subject":  "What Is Healthy? — library acquisition info",
        "d3_subject":  "What community libraries are doing with this book",
        "d7_subject":  "Program support, author Q&A, and reading guides",
        "d14_subject": "Happy to support your acquisition request",
        "d21_subject": "Last note — What Is Healthy? for your community",
        "d0_intro": "I'm reaching out about getting <em>What Is Healthy?</em> into your library collection.",
        "d0_context": "It's a research-backed, general-audience book on the food industry, nutrition myths, and community health. Libraries have found it works well for community wellness programs, book clubs, and as a general health reference.",
        "d0_offer": "I'm happy to provide a complimentary review copy for your acquisition review, along with a reading group guide and program support materials.",
        "d0_cta_label": "Request a Review Copy",
        "d0_cta_url": LIBRARY_URL,
        "d3_body": """Libraries that have added the book to their collections have used it in a few different ways:<br/><br/>
<strong>Community wellness programs</strong> — using it as the anchor text for 4–6 week community health discussions. We provide a discussion guide.<br/><br/>
<strong>Book clubs</strong> — it generates strong conversation because it touches on things people deal with daily (grocery shopping, feeding families, reading labels) but usually can't discuss rigorously.<br/><br/>
<strong>Author events</strong> — I'm available for in-person or virtual author talks for library patrons. These tend to draw well because the topic is relevant to almost everyone.""",
        "d3_cta_label": "See Library Program Info",
        "d3_cta_url": LIBRARY_URL,
        "d7_body": """A few resources available to libraries that carry the book:<br/><br/>
<ul style="margin:0 0 16px;padding-left:20px;font-size:16px;line-height:2;color:#374151;">
<li>Reading group discussion guide (12 questions, chapter by chapter)</li>
<li>Community health program curriculum (6 sessions)</li>
<li>Author Q&amp;A — virtual or in-person</li>
<li>Promotional materials for library bulletin boards</li>
</ul>
All of these are free to libraries that acquire the book. We want the book to actually be read and used, not just sit on a shelf.""",
        "d7_cta_label": "Request Library Support Materials",
        "d7_cta_url": LIBRARY_URL,
        "d14_ask": "I'd love to make sure your library has a copy — and the materials to make it useful to your community. What's the best way to support your acquisition process from here?",
        "d21_close": "Last note from me. If there's anything I can do to help with the acquisition review — a formal press kit, additional review materials, or a reference call with another librarian who's used the book — just reply and let me know.",
    },
    "podcast": {
        "d0_subject":  "Podcast guest — What Is Healthy? with Kortney Lee",
        "d3_subject":  "Episode angles that tend to generate strong response",
        "d7_subject":  "What listeners take away from these conversations",
        "d14_subject": "Are we booking a date?",
        "d21_subject": "Last note on the podcast booking",
        "d0_intro": "I'm Kortney Lee, author of <em>What Is Healthy?</em>, and I think your listeners would find this conversation valuable.",
        "d0_context": "The book covers the gap between what people are told about health and what the research actually shows — specifically around the food industry, label deception, ultra-processed food, and what families can realistically do about it. It's not another diet book. It's a research-backed look at why the system isn't working for most people and what to do about it.",
        "d0_offer": "I'm an experienced speaker and can adapt the conversation to what resonates most with your audience — whether that's weight loss, feeding kids, food budgets, or the bigger picture of community health.",
        "d0_cta_label": "View Media Kit & Talking Points",
        "d0_cta_url": MEDIA_KIT_URL,
        "d3_body": """A few angles that have generated the strongest listener response in past interviews:<br/><br/>
<strong>"The 5-second label test"</strong> — a simple way to know whether a food is worth eating before you even read the ingredients. Listeners share this one.<br/><br/>
<strong>"Why your grandmother's food was healthier — and it wasn't because she cooked better"</strong> — the structural changes in the food supply since the 1970s. Very shareable.<br/><br/>
<strong>"The working-class health gap"</strong> — why wellness feels like a luxury and what that costs us as communities. This one tends to resonate emotionally.<br/><br/>
<strong>"What 100-year-olds actually eat"</strong> — Blue Zones research distilled into practical takeaways. Positive, actionable, surprising.""",
        "d3_cta_label": "See All Episode Topics",
        "d3_cta_url": MEDIA_KIT_URL,
        "d7_body": """What listeners tend to say after these conversations:<br/><br/>
<em>"I went straight to the store and started reading labels differently."</em><br/><br/>
<em>"I bought copies for my whole family."</em><br/><br/>
<em>"This is the episode I keep sending people."</em><br/><br/>
I bring real research, personal story (my grandmother died of cancer after years of type 2 diabetes and high blood pressure — three chronic illnesses at once — and that's what drove the book), and practical takeaways your listeners can actually use.""",
        "d7_cta_label": "Book the Interview",
        "d7_cta_url": MEDIA_KIT_URL,
        "d14_ask": "I'd love to make this happen. What does your booking calendar look like? I'm flexible on format — long-form, short-form, video or audio only.",
        "d21_close": "Last note from me. If the timing doesn't work right now, no problem at all — just keep me in mind for when it does. The offer stands.",
    },
    "blog": {
        "d0_subject":  "Review copy + interview — What Is Healthy?",
        "d3_subject":  "Angles your readers will connect with",
        "d7_subject":  "What other writers have done with the book",
        "d14_subject": "Would an exclusive excerpt help?",
        "d21_subject": "Last note — covering What Is Healthy?",
        "d0_intro": "I'm Kortney Lee, author of <em>What Is Healthy?</em>, and I'd love for your readers to know about it.",
        "d0_context": "The book is a research-backed look at the food industry, nutrition myths, and what families can realistically do to eat better — written for a general audience, not a medical one. It covers label deception, ultra-processed food, community health, and the psychology of why changing eating habits is so hard.",
        "d0_offer": "I'm happy to provide a complimentary review copy (digital or print), an exclusive excerpt for your readers, or an interview — whatever format works best for your publication.",
        "d0_cta_label": "Request a Review Copy",
        "d0_cta_url": MEDIA_KIT_URL,
        "d3_body": """A few angles that have connected strongly with readers:<br/><br/>
<strong>The label deception angle</strong> — "natural flavors" appears on 80% of packaged food. Most people don't know what it actually means. This article tends to drive shares.<br/><br/>
<strong>The budget angle</strong> — eating well isn't just a willpower problem, it's an economic and infrastructure problem. This resonates with readers who feel judged for what's in their grocery cart.<br/><br/>
<strong>The family angle</strong> — what to feed kids when the food system is working against you. High engagement with parents.<br/><br/>
<strong>The personal story angle</strong> — my grandmother died of cancer after years of type 2 and high blood pressure. That loss drove the research that became this book.""",
        "d3_cta_label": "See Media Kit",
        "d3_cta_url": MEDIA_KIT_URL,
        "d7_body": """A few things other writers have done with the book:<br/><br/>
An exclusive excerpt from Chapter 3 (the one on "natural flavors" and what the FDA actually allows). We can provide this as a standalone piece.<br/><br/>
A Q&amp;A-style interview — we can do written answers to your questions, or a live conversation you transcribe.<br/><br/>
A guest post from Kortney on any of the angles above — fully written, original, not published elsewhere.<br/><br/>
We're flexible on format and happy to work around your editorial calendar.""",
        "d7_cta_label": "Request an Excerpt or Interview",
        "d7_cta_url": MEDIA_KIT_URL,
        "d14_ask": "Would an exclusive excerpt from Chapter 3 help get this on your editorial calendar? I can have it to you within a few days.",
        "d21_close": "Last note from me. If the timing or angle doesn't fit right now, no problem. Keep us in mind — the offer for a review copy or excerpt stands whenever you're ready.",
    },
    "church": {
        "d0_subject":  "What Is Healthy? — church & community wellness programs",
        "d3_subject":  "How faith communities are using this book",
        "d7_subject":  "Bulk pricing, speaking, and small group resources",
        "d14_subject": "Ready to support your community health program",
        "d21_subject": "Last note — What Is Healthy? for your congregation",
        "d0_intro": "I'm reaching out because <em>What Is Healthy?</em> has found a real home in faith community wellness programs, and I thought it might be a fit for yours.",
        "d0_context": "The book is about what we put into our bodies, why the system makes it so hard to make good choices, and what individuals and communities can do about it. It's written from a place of care for people — not judgment — and that message resonates with communities that already think about stewardship, wholeness, and looking out for each other.",
        "d0_offer": "We offer bulk pricing for group studies (10+ copies), and I'm available to speak at health-focused church events, wellness weekends, or community health fairs.",
        "d0_cta_label": "View Bulk Order & Speaking Info",
        "d0_cta_url": WHOLESALE_URL,
        "d3_body": """Faith communities have used the book in a few ways that have worked really well:<br/><br/>
<strong>6-week small group study</strong> — we provide a discussion guide that maps to chapters and works well in small groups of 8–15. Topics include food and stewardship, caring for your community's health, and what the research says about chronic illness in working families.<br/><br/>
<strong>Health ministry resource</strong> — many health ministries have added it to their lending library or recommended reading list.<br/><br/>
<strong>Community health events</strong> — I've spoken at church health fairs, "body and soul" weekends, and community wellness events. The conversation about chronic illness and community care tends to land particularly well.""",
        "d3_cta_label": "Learn About Community Programs",
        "d3_cta_url": WHOLESALE_URL,
        "d7_body": """A few things we provide to faith communities that use the book:<br/><br/>
<ul style="margin:0 0 16px;padding-left:20px;font-size:16px;line-height:2;color:#374151;">
<li>Small group discussion guide (6 sessions)</li>
<li>Bulk pricing — 10+ copies at wholesale rates</li>
<li>Author talk — in person or virtual, 45–60 minutes</li>
<li>Health ministry support materials</li>
</ul>
My grandmother passed from cancer after years of type 2 diabetes and high blood pressure — three chronic illnesses that didn't have to end her life the way they did. That's the personal reason behind the book, and it's why I care about getting it into communities that are paying attention to their health.""",
        "d7_cta_label": "Request Program Info",
        "d7_cta_url": WHOLESALE_URL,
        "d14_ask": "I'd love to support your community with this. What does your health ministry or wellness program look like, and how can we best fit into it?",
        "d21_close": "Last note. Whether it's a few books for a small group or a full community event, we're here whenever the timing is right. Just reply and we'll make it work.",
    },
    "school": {
        "d0_subject":  "What Is Healthy? — school nutrition & health programs",
        "d3_subject":  "How schools are using the book in health classes",
        "d7_subject":  "Curriculum resources, assemblies, and parent workshops",
        "d14_subject": "Ready to support your nutrition program",
        "d21_subject": "Last note — What Is Healthy? for your school",
        "d0_intro": "I'm reaching out about bringing <em>What Is Healthy?</em> into your school's health or nutrition program.",
        "d0_context": "The book covers the food industry, what's actually in processed food, how to read labels, and what families can do to make better choices — written for a general adult audience, which makes it ideal for parent education, health teachers, and school wellness staff.",
        "d0_offer": "We offer classroom and program pricing for schools (10+ copies), and I'm available for student assemblies, parent workshops, and teacher professional development sessions.",
        "d0_cta_label": "View School Program Info",
        "d0_cta_url": LIBRARY_URL,
        "d3_body": """Schools have found a few entry points that work well:<br/><br/>
<strong>Parent education workshops</strong> — "What's really in your kid's lunch?" is a perennial draw. Parents want this information but don't know where to get it from a trusted source. This book gives them something to go home with.<br/><br/>
<strong>Health class supplemental reading</strong> — Chapters 1–3 work well as a standalone unit on the food industry and label reading for high school health classes.<br/><br/>
<strong>Student assemblies</strong> — I've spoken to student groups on the connection between food, focus, energy, and long-term health. The personal story elements (chronic illness, family impact) tend to land with students.""",
        "d3_cta_label": "See Program Options",
        "d3_cta_url": LIBRARY_URL,
        "d7_body": """Resources available to schools:<br/><br/>
<ul style="margin:0 0 16px;padding-left:20px;font-size:16px;line-height:2;color:#374151;">
<li>Program pricing — 10+ copies at educational rates</li>
<li>Discussion guide aligned to health curriculum standards</li>
<li>Student assembly — 45 minutes, Q&amp;A included</li>
<li>Parent workshop — 60–90 minutes, includes book</li>
<li>Teacher PD session on food literacy</li>
</ul>
The goal is for students to leave with one or two things they can actually apply — reading a label, making a better choice at the grocery store, understanding why certain foods are marketed to them the way they are.""",
        "d7_cta_label": "Request School Program Info",
        "d7_cta_url": LIBRARY_URL,
        "d14_ask": "What would be most useful for your school right now — books for a class, a parent event, or a student assembly? I'd love to figure out the right fit.",
        "d21_close": "Last note from me. School programs take time to put together and I understand calendars get full — whenever the timing is right, we're here to support your nutrition program.",
    },
    "other": {
        "d0_subject":  "What Is Healthy? — partnership inquiry",
        "d3_subject":  "A few ways we work with partners",
        "d7_subject":  "What we've built together with other organizations",
        "d14_subject": "Ready to make something happen",
        "d21_subject": "Last note from Kortney",
        "d0_intro": "I'm Kortney Lee, author of <em>What Is Healthy?</em>, and I'd love to explore how we might work together.",
        "d0_context": "The book is a research-backed look at the food industry, nutrition myths, and what families can do to eat better. It's finding readers everywhere — from bookstores to church wellness programs to school nutrition initiatives.",
        "d0_offer": "Whether you're thinking about bulk orders, a content partnership, an author event, or something else entirely — I'm open to the conversation.",
        "d0_cta_label": "Start the Conversation",
        "d0_cta_url": WHOLESALE_URL,
        "d3_body": """A few ways we've worked with organizations so far:<br/><br/>
<strong>Bulk orders</strong> — wholesale pricing for 10+ copies, returnable terms available.<br/><br/>
<strong>Author events</strong> — in-person or virtual talks, panels, and Q&amp;A sessions.<br/><br/>
<strong>Content partnerships</strong> — exclusive excerpts, guest posts, interviews for newsletters or publications.<br/><br/>
<strong>Community programs</strong> — reading group guides, curriculum materials, health program support.<br/><br/>
Hit reply and tell me more about what you're imagining — we'll figure out if there's a fit.""",
        "d3_cta_label": "See Partnership Options",
        "d3_cta_url": WHOLESALE_URL,
        "d7_body": """The book is on Amazon in paperback, hardcover, Kindle, and Audible — but the best partnerships we've built have been with organizations that put the book in front of the right people at the right time.<br/><br/>
My grandmother passed from cancer after years of type 2 diabetes and high blood pressure. Three chronic illnesses. That's what drove me to write this book — and it's why I care about getting it to communities that are paying attention to their health, not just individuals who already are.""",
        "d7_cta_label": "Learn More",
        "d7_cta_url": WHOLESALE_URL,
        "d14_ask": "What would a partnership look like for you? I'd love to find a way to make this work.",
        "d21_close": "Last note. If the timing wasn't right or something shifted, no problem at all — just reply whenever it does make sense. Happy to pick the conversation back up.",
    },
}


def _get(bt: str) -> dict:
    return _COPY.get(bt, _COPY["other"])


# ── Email templates ───────────────────────────────────────────────────────────

def _wrap(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;">
{content}
<tr><td style="padding:16px 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
<a href="{UNSUBSCRIBE_URL}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
&middot; Partnerships &middot; What Is Healthy?
</p></td></tr>
</table></td></tr></table></body></html>"""


def _cta(label: str, url: str) -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" style="margin:0 0 24px;"><tr>'
        f'<td bgcolor="#1e40af" style="border-radius:5px;">'
        f'<a href="{url}" style="display:block;padding:12px 24px;color:#ffffff;'
        f'font-size:15px;font-weight:600;text-decoration:none;">{label}</a>'
        f'</td></tr></table>'
    )


def _sig(short: bool = False) -> str:
    if short:
        return """<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Kortney</p>"""
    return """<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Talk soon,<br/>Kortney Lee<br/>
<span style="font-size:14px;color:#6b7280;">Author, <em>What Is Healthy?</em> &middot; partnerships@vowels.org</span></p>"""


def _render_b2b_day0(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    company = f" at {company_name}" if company_name else ""
    return _wrap(f"""
<tr><td style="padding:40px 40px 8px;">
<img src="{BOOK_IMAGE_URL}" width="80" alt="What Is Healthy?" style="display:block;margin:0 0 28px;border:0;" />
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['d0_intro']}{company}.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['d0_context']}</p>
<p style="margin:0 0 24px;font-size:16px;line-height:1.8;color:#374151;">
{c['d0_offer']}</p>
{_cta(c['d0_cta_label'], c['d0_cta_url'])}
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Or just hit reply — happy to answer questions directly.</p>
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
{_sig()}
</td></tr>""")


def _render_b2b_day3(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 8px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Following up on my note from a few days ago — wanted to share a little more about what we're seeing with the book.</p>
<p style="margin:0 0 24px;font-size:16px;line-height:1.8;color:#374151;">
{c['d3_body']}</p>
{_cta(c['d3_cta_label'], c['d3_cta_url'])}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
{_sig()}
</td></tr>""")


def _render_b2b_day7(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 8px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 24px;font-size:16px;line-height:1.8;color:#374151;">
{c['d7_body']}</p>
{_cta(c['d7_cta_label'], c['d7_cta_url'])}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
{_sig()}
</td></tr>""")


def _render_b2b_day14(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 8px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['d14_ask']}</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Just hit reply — that's the fastest way to make this happen.</p>
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
{_sig()}
</td></tr>""")


def _render_b2b_day21(first_name: str, business_type: str, company_name: str) -> str:
    c = _get(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 8px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Last note from me — I don't want to fill your inbox.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['d21_close']}</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
partnerships@vowels.org — reach out any time.</p>
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
{_sig(short=True)}
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
