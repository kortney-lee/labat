import os, sys
sys.path.insert(0, '.')
os.environ.setdefault('GCP_PROJECT', 'wihy-ai')
from google.cloud import firestore
from datetime import datetime, timezone

db = firestore.Client(project='wihy-ai')
now = datetime.now(timezone.utc)

docs = list(db.collection('book_leads').where('sequence_status', '==', 'active').stream())
print(f'Active leads: {len(docs)}')
print()

missing_next_at = 0
future_next_at = 0
overdue = 0

for d in docs:
    x = d.to_dict()
    email = x.get('email', '')
    stage = x.get('nurture_stage', 0)
    next_at = x.get('nurture_next_at')
    created = x.get('created_at')

    if next_at is None:
        missing_next_at += 1
        print(f'  MISSING nurture_next_at | stage={stage} | email={email} | created={created}')
    elif next_at > now:
        future_next_at += 1
    else:
        overdue += 1

print()
print(f'Missing nurture_next_at: {missing_next_at}')
print(f'Scheduled in future:     {future_next_at}')
print(f'Overdue (should have sent): {overdue}')
