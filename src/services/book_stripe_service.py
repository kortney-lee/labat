"""
Book Stripe Checkout Service
Creates Stripe Checkout Sessions for paperback book purchases.
"""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_API = "https://api.stripe.com/v1"
PAPERBACK_PRICE_CENTS = 2499  # $24.99
SUCCESS_URL = os.getenv("BOOK_CHECKOUT_SUCCESS_URL", "https://whatishealthy.org/thank-you.html?purchase=1")
CANCEL_URL = os.getenv("BOOK_CHECKOUT_CANCEL_URL", "https://whatishealthy.org/oto.html?canceled=1")


async def create_checkout_session(email: Optional[str] = None) -> dict:
    """Create a Stripe Checkout Session for the paperback book.

    Returns {"url": "https://checkout.stripe.com/..."} on success.
    """
    if not STRIPE_SECRET_KEY:
        logger.error("STRIPE_SECRET_KEY not set")
        raise RuntimeError("Stripe is not configured")

    line_items = {
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][product_data][name]": "What Is Healthy? \u2014 Paperback Edition",
        "line_items[0][price_data][product_data][description]": "Full-color premium paperback with quick-reference label guide",
        "line_items[0][price_data][unit_amount]": str(PAPERBACK_PRICE_CENTS),
        "line_items[0][quantity]": "1",
        "mode": "payment",
        "success_url": SUCCESS_URL,
        "cancel_url": CANCEL_URL,
        "shipping_address_collection[allowed_countries][]": "US",
        "payment_intent_data[statement_descriptor]": "VOWELS",
    }

    if email:
        line_items["customer_email"] = email

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{STRIPE_API}/checkout/sessions",
            data=line_items,
            headers={"Authorization": f"Bearer {STRIPE_SECRET_KEY}"},
        )
        if resp.status_code != 200:
            logger.error(f"Stripe error {resp.status_code}: {resp.text}")
            raise RuntimeError("Failed to create checkout session")

        session = resp.json()
        logger.info(f"Stripe checkout session created: {session.get('id')}")
        return {"url": session["url"], "session_id": session["id"]}
