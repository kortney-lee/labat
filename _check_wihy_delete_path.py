import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-Admin-Token": os.getenv("INTERNAL_ADMIN_TOKEN", "").strip()}
pid = "937763702752161_1687653729065414"
for base in [
    "https://wihy-labat-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-wihy-n4l2vldq3q-uc.a.run.app",
]:
    r = requests.delete(f"{base}/api/labat/posts/{pid}", headers=headers, timeout=30)
    print({"base": base, "status": r.status_code, "body": r.text[:220]})
