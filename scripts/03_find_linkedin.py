#!/usr/bin/env python3
"""
notion-crm-toolkit / 03_find_linkedin.py
-----------------------------------------
Finds missing LinkedIn profile URLs for contacts in your Notion CRM.

Strategy:
  Uses Google Search (via Serper.dev) to query:
  "FirstName LastName" "CompanyName" site:linkedin.com/in

Confidence levels:
  ✅ HIGH   — result URL contains both name parts
  ⚠️  MEDIUM — result found but match is partial
  ❌ LOW    — no result or ambiguous → skipped, logged to review

Only updates contacts where the LinkedIn field is currently empty.
Exports low-confidence results to linkedin_review.csv.

Requirements:
  pip install requests
  Free Serper.dev account → 2,500 searches/month free tier

Usage:
  python 03_find_linkedin.py
"""

import requests
import re
import csv
import time

# ── Config ───────────────────────────────────────────────────────────────────

NOTION_TOKEN  = input("Notion integration token (secret_xxx): ").strip()
SERPER_KEY    = input("Serper.dev API key (serper.dev → free signup): ").strip()
DATABASE_URL  = input("Contacts database URL: ").strip()

def extract_id(url):
    raw = url.split("notion.so/")[-1].split("?")[0].split("/")[-1].replace("-", "")
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"

DATABASE_ID = extract_id(DATABASE_URL)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# Name of the LinkedIn field in your Notion database
# Change this if your field has a different name
LINKEDIN_FIELD = "LinkedIn"

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_text(prop):
    if not prop: return ""
    items = prop.get("rich_text") or prop.get("title") or []
    return "".join(t.get("plain_text", "") for t in items).strip()

def get_url_prop(prop):
    if not prop: return ""
    return (prop.get("url") or "").strip()

def normalize(s):
    return re.sub(r'[^a-z]', '', s.lower()) if s else ""

def name_in_url(first, last, url):
    """Check if first and last name appear in the LinkedIn URL slug."""
    url_lower = url.lower()
    norm_first = normalize(first)
    norm_last  = normalize(last)
    return norm_first in url_lower and norm_last in url_lower

# ── Search ───────────────────────────────────────────────────────────────────

def search_linkedin(first_name, last_name, company):
    """Search Google for the LinkedIn profile using Serper."""
    query = f'"{first_name} {last_name}" "{company}" site:linkedin.com/in'
    r = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
        json={"q": query, "num": 3}
    )
    if r.status_code != 200:
        return None, "api_error"

    results = r.json().get("organic", [])
    for result in results:
        link = result.get("link", "")
        if "linkedin.com/in/" in link:
            if name_in_url(first_name, last_name, link):
                return link, "high"
            else:
                return link, "medium"

    # Fallback: try without company name
    if company:
        query2 = f'"{first_name} {last_name}" site:linkedin.com/in'
        r2 = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query2, "num": 3}
        )
        if r2.status_code == 200:
            for result in r2.json().get("organic", []):
                link = result.get("link", "")
                if "linkedin.com/in/" in link and name_in_url(first_name, last_name, link):
                    return link, "medium"

    return None, "not_found"

# ── Notion API ───────────────────────────────────────────────────────────────

def fetch_contacts_without_linkedin():
    """Fetch contacts that have no LinkedIn URL."""
    pages, cursor = [], None
    page_num = 0
    while True:
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
            headers=HEADERS, json=body
        )
        r.raise_for_status()
        data = r.json()
        # Filter client-side for missing LinkedIn
        for page in data["results"]:
            props = page.get("properties", {})
            linkedin = get_url_prop(props.get(LINKEDIN_FIELD))
            if not linkedin:
                pages.append(page)
        page_num += 1
        print(f"  page {page_num} ({len(pages)} without LinkedIn so far)...")
        if not data.get("has_more"): break
        cursor = data["next_cursor"]
        time.sleep(0.3)
    return pages

def update_linkedin(page_id, url):
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=HEADERS,
        json={"properties": {LINKEDIN_FIELD: {"url": url}}}
    )
    return r.status_code == 200

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n🔍 Fetching contacts without LinkedIn...")
    contacts = fetch_contacts_without_linkedin()
    print(f"✅ {len(contacts)} contacts to enrich.\n")

    # Filter out those without a usable name
    enrichable = []
    skipped = []
    for c in contacts:
        props = c.get("properties", {})
        first   = get_text(props.get("First Name"))
        last    = get_text(props.get("Last Name"))
        name    = get_text(props.get("Name"))
        company = ""

        # Get company name from relation
        company_rel = props.get("Company", {}).get("relation", [])
        if not first and not last and name:
            parts = name.split()
            first = parts[0] if parts else ""
            last  = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Skip placeholders
        if not first or not last or first == "please fill to enrich":
            skipped.append(c)
            continue

        enrichable.append({
            "id": c["id"],
            "first": first,
            "last": last,
            "company": company,
            "display": f"{first} {last}",
        })

    print(f"📝 {len(enrichable)} enrichable | {len(skipped)} skipped (no usable name)\n")

    # Estimate cost
    print(f"ℹ️  This will use ~{len(enrichable)}-{len(enrichable)*2} Serper searches.")
    print(f"   Free tier = 2,500/month. Paid = $50/month for 50,000.\n")

    confirm = input(f"Start enriching {len(enrichable)} contacts? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return

    found_high, found_medium, not_found, errors = 0, 0, 0, 0
    to_review = []

    for i, contact in enumerate(enrichable):
        linkedin_url, confidence = search_linkedin(
            contact["first"], contact["last"], contact["company"]
        )

        if linkedin_url and confidence == "high":
            ok = update_linkedin(contact["id"], linkedin_url)
            if ok:
                found_high += 1
                print(f"  ✅ {contact['display']:<30} → {linkedin_url}")
            else:
                errors += 1

        elif linkedin_url and confidence == "medium":
            found_medium += 1
            to_review.append({
                "Name": contact["display"],
                "Company": contact["company"],
                "Found URL": linkedin_url,
                "Confidence": "medium",
                "Notion Page ID": contact["id"],
            })
            print(f"  ⚠️  {contact['display']:<30} → {linkedin_url} (needs review)")

        else:
            not_found += 1

        # Progress
        if (i + 1) % 25 == 0:
            print(f"\n  [{i+1}/{len(enrichable)}] ✅ {found_high} high | ⚠️ {found_medium} medium | ❌ {not_found} not found\n")

        time.sleep(0.5)  # Respect rate limits

    print(f"\n🎉 Done!")
    print(f"  ✅ Auto-updated (high confidence): {found_high}")
    print(f"  ⚠️  Needs review (medium):          {found_medium}")
    print(f"  ❌ Not found:                       {not_found}")
    print(f"  🔴 Errors:                          {errors}")

    if to_review:
        with open("linkedin_review.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Name","Company","Found URL","Confidence","Notion Page ID"])
            writer.writeheader()
            writer.writerows(to_review)
        print(f"\n📊 {len(to_review)} medium-confidence results → linkedin_review.csv")
        print("   Review manually and update in Notion if correct.")

if __name__ == "__main__":
    main()
