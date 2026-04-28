from dotenv import load_dotenv
from google.cloud import firestore
from datetime import datetime, timezone, timedelta
import os

load_dotenv()
project = os.getenv('GCP_PROJECT', 'wihy-ai')
print('project=', project, flush=True)
db = firestore.Client(project=project)
week_ago = datetime.now(timezone.utc) - timedelta(days=7)

for col in ['launch_leads', 'book_leads']:
    c = db.collection(col)
    try:
        total = c.count().get()[0][0].value
    except Exception:
        total = -1

    recent_docs = list(c.where('created_at', '>=', week_ago).order_by('created_at', direction=firestore.Query.DESCENDING).limit(10).stream())
    print(f'\n{col}: total={total} recent7d_sample={len(recent_docs)}', flush=True)

    sent_marker_docs = 0
    for d in recent_docs:
        x = d.to_dict() or {}
        markers = [k for k in x.keys() if 'sent_at' in k]
        sg_events = len(x.get('sendgrid_events', []) or [])
        if markers:
            sent_marker_docs += 1
        created = x.get('created_at')
        print(' ', d.id, 'created=', created, 'email=', bool(x.get('email')), 'brand=', x.get('brand') or x.get('source'), 'stage=', x.get('nurture_stage'), 'sent_markers=', len(markers), 'sg_events=', sg_events, flush=True)

    print(f'  recent_docs_with_sent_marker={sent_marker_docs}', flush=True)
