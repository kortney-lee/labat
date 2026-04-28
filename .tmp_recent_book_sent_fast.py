from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
import asyncio

from src.services.book_leads_service import _get_firestore, COLLECTION

cutoff = datetime.now(timezone.utc) - timedelta(days=7)
db = _get_firestore()
fields = [
    'nurture_book_delivery_sent_at',
    'nurture_did_you_get_this_sent_at',
    'nurture_big_benefit_sent_at',
    'nurture_got_questions_sent_at',
    'nurture_social_proof_sent_at',
    'nurture_im_surprised_sent_at',
    'nurture_last_chance_sent_at',
    'nurture_buy_now_offer_sent_at',
]

async def run():
    for field in fields:
        try:
            query = db.collection(COLLECTION).where(field, '>=', cutoff).order_by(field, direction=firestore.Query.DESCENDING).limit(5)
            docs = [doc async for doc in query.stream()]
            print('\nFIELD=', field, 'count=', len(docs))
            for d in docs:
                x = d.to_dict() or {}
                print((x.get(field), x.get('email'), x.get('first_name'), x.get('utm_content')))
        except Exception as e:
            print('\nFIELD=', field, 'error=', str(e))

asyncio.run(run())
