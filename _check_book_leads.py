import os, sys
sys.path.insert(0, '.')
os.environ.setdefault('GCP_PROJECT', 'wihy-ai')
from google.cloud import firestore
from datetime import datetime, timezone, timedelta
from collections import Counter

db = firestore.Client(project='wihy-ai')
cutoff = datetime.now(timezone.utc) - timedelta(days=30)

docs = list(db.collection('book_leads').stream())
total = len(docs)
stages = Counter()
statuses = Counter()
recent = 0
variants = Counter()

for d in docs:
    x = d.to_dict()
    stage = x.get('nurture_stage', 0)
    stages[stage] += 1
    status = x.get('sequence_status', 'active')
    statuses[status] += 1
    variant = x.get('utm_content', '') or x.get('variant', '') or 'unknown'
    variants[variant] += 1
    created = x.get('created_at')
    if created:
        try:
            ts = created if getattr(created, 'tzinfo', None) else created.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                recent += 1
        except:
            pass

print(f'=== BOOK LEADS ===')
print(f'Total leads:         {total}')
print(f'Signed up (30 days): {recent}')
print()
print('Sequence status breakdown:')
for s, c in sorted(statuses.items()):
    print(f'  {s}: {c}')
print()
print('Nurture stage breakdown:')
stage_labels = {
    0: 'stage 0 (no email yet)',
    1: 'stage 1 (Day 0 sent)',
    2: 'stage 2 (Day 1 sent)',
    3: 'stage 3 (Day 3 sent)',
    4: 'stage 4 (Day 5 sent)',
    5: 'stage 5 (Day 7 sent)',
    6: 'stage 6 (Day 10 sent)',
    7: 'stage 7 (complete)',
}
for s in sorted(stages):
    print(f'  {stage_labels.get(s, f"stage {s}")}: {stages[s]}')
print()
print('Top variants (utm_content):')
for v, c in variants.most_common(15):
    print(f'  {v}: {c}')
