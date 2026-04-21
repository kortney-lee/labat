"""Quick script to list Meta lead forms via live API."""
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("INTERNAL_ADMIN_TOKEN", "")
print(f"Token set: {bool(token)}")

base = "https://wihy-labat-n4l2vldq3q-uc.a.run.app"

# 1. List forms
r = httpx.get(f"{base}/api/labat/leads/forms?limit=100", headers={"X-Admin-Token": token}, timeout=20)
print(f"Forms status: {r.status_code}")
data = r.json()
forms = data.get("data", [])
print(f"Forms found: {len(forms)}")
total_meta_leads = 0
for f in forms:
    status = f.get("status", "?")
    name = f.get("name", "?")
    leads = f.get("leads_count") or 0
    fid = f.get("id")
    total_meta_leads += leads
    print(f"  [{status}] {name} | leads={leads} | id={fid}")

print(f"\nTotal Meta leads (all forms): {total_meta_leads}")

# 2. Trigger sync
print("\n=== TRIGGERING SYNC ===")
r2 = httpx.post(f"{base}/api/labat/leads/sync", headers={"X-Admin-Token": token}, timeout=120)
print(f"Sync status: {r2.status_code}")
if r2.status_code == 200:
    result = r2.json()
    print(f"Forms processed: {result.get('forms_processed')}")
    print(f"Total synced:    {result.get('total_synced')}")
    print(f"Total errors:    {result.get('total_errors')}")
    for fr in result.get("results", []):
        synced = fr.get("synced", 0)
        skipped = fr.get("skipped", 0)
        errors = fr.get("errors", 0)
        total = fr.get("total_fetched", 0)
        print(f"  form {fr.get('form_id')}: fetched={total} synced={synced} skipped={skipped} errors={errors}")
        for lead in fr.get("leads", []):
            print(f"    -> {lead.get('email')} ({lead.get('brand')})")
else:
    print(r2.text[:500])
