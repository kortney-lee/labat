import os
import httpx
from dotenv import load_dotenv

load_dotenv(".env.production")
token = os.getenv("META_SYSTEM_USER_TOKEN", "")
base = "https://graph.facebook.com/v21.0"
biz_id = "4867231843349033"

for edge in ["business_asset_groups", "owned_business_asset_groups"]:
    print(f"=== {edge} ===")
    r = httpx.get(
        f"{base}/{biz_id}/{edge}",
        params={"fields": "id,name", "access_token": token, "limit": 50},
        timeout=15,
    )
    d = r.json()
    if "data" in d:
        for item in d["data"]:
            gid = item["id"]
            gname = item["name"]
            print(f"  GROUP: {gid} - {gname}")

            # Try multiple edge name variants for each asset type
            asset_edges = {
                "Pages": [
                    ("contained_pages", "id,name,username"),
                    ("pages", "id,name,username"),
                ],
                "AdAccts": [
                    ("contained_ad_accounts", "id,name,account_id"),
                    ("contained_adaccounts", "id,name,account_id"),
                    ("ad_accounts", "id,name,account_id"),
                    ("adaccounts", "id,name,account_id"),
                ],
                "IG": [
                    ("contained_instagram_accounts", "id,username,name"),
                    ("instagram_accounts", "id,username,name"),
                ],
                "Pixels": [
                    ("contained_pixels", "id,name"),
                    ("pixels", "id,name"),
                    ("adspixels", "id,name"),
                    ("contained_adspixels", "id,name"),
                ],
                "Apps": [
                    ("contained_applications", "id,name"),
                    ("applications", "id,name"),
                    ("apps", "id,name"),
                ],
                "CustomConv": [
                    ("contained_custom_conversions", "id,name"),
                    ("custom_conversions", "id,name"),
                ],
                "OfflineConv": [
                    ("contained_offline_conversion_data_sets", "id,name"),
                    ("offline_conversion_data_sets", "id,name"),
                ],
                "ProductCatalogs": [
                    ("contained_product_catalogs", "id,name"),
                    ("product_catalogs", "id,name"),
                ],
            }

            for label, variants in asset_edges.items():
                found = False
                for edge_name, fields in variants:
                    r2 = httpx.get(
                        f"{base}/{gid}/{edge_name}",
                        params={"fields": fields, "access_token": token, "limit": 50},
                        timeout=15,
                    )
                    p2 = r2.json()
                    if "data" in p2:
                        if p2["data"]:
                            for p in p2["data"]:
                                detail = p.get("username", p.get("account_id", ""))
                                print(f"    {label} [{edge_name}]: {p.get('name','')} ({p['id']}) {detail}")
                        else:
                            print(f"    {label} [{edge_name}]: (empty)")
                        found = True
                        break
                if not found:
                    print(f"    {label}: no valid edge found")

            print()
    elif "error" in d:
        print(f"  Error: {d['error']['message'][:120]}")
    else:
        print("  Empty")
    print()
