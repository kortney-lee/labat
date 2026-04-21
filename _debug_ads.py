"""Debug: find all ads in the account."""
import os, httpx
from dotenv import load_dotenv
load_dotenv(override=True)

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
BASE = "https://graph.facebook.com/v21.0"
ACCOUNT = "act_218581359635343"

# Check account status
r0 = httpx.get(f"{BASE}/{ACCOUNT}", params={
    "access_token": TOKEN,
    "fields": "id,name,account_status,disable_reason,amount_spent",
})
print("Account:", r0.json())

# Check total ad count
r_count = httpx.get(f"{BASE}/{ACCOUNT}/ads", params={
    "access_token": TOKEN,
    "fields": "id",
    "limit": 1,
    "summary": "true",
})
print(f"\nAds summary: {r_count.json()}")

# Try getting ALL ads including archived/deleted
r_all = httpx.get(f"{BASE}/{ACCOUNT}/ads", params={
    "access_token": TOKEN,
    "fields": "name,id,effective_status",
    "limit": 5,
    "date_preset": "maximum",
})
print(f"\nWith date_preset: {r_all.json()}")

# Check if we can read a specific known ad ID from the earlier run
# Let me check the _check_all_ads.py for known IDs
