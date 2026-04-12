#!/usr/bin/env python3
"""
notion-crm-toolkit / 02_link_companies.py
------------------------------------------
Matches contacts without a linked company to companies in your CRM.

Matching strategy (in order):
1. Exact email domain match  (contact@nexans.com → company website nexans.com)
2. Fuzzy domain match        (hmc-heerema.com ≈ heerema.com)
3. Domain base = company name (nexans.com → company "NEXANS")
4. Fuzzy name match          (vanoord.com ≈ "Van OORD")

Contacts with no match → exported to unlinked_contacts.csv for manual enrichment.

Usage:
    python 02_link_companies.py
"""

import requests
import re
import csv
import time
from urllib.parse import urlparse
from difflib import SequenceMatcher

# ── Config ───────────────────────────────────────────────────────────────────

NOTION_TOKEN   = input("Notion integration token (secret_xxx): ").strip()
CONTACTS_URL   = input("Contacts database URL: ").strip()
COMPANIES_URL  = input("Companies database URL: ").strip()

def extract_id(url):
    raw = url.split("notion.so/")[-1].split("?")[0].split("/")[-1].replace("-", "")
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"

CONTACTS_DB  = extract_id(CONTACTS_URL)
COMPANIES_DB = extract_id(COMPANIES_URL)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "live.com", "msn.com", "me.com", "aol.com", "protonmail.com",
    "orange.fr", "free.fr", "sfr.fr", "laposte.net",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_text(prop):
    if not prop: return ""
    items = prop.get("rich_text") or prop.get("title") or []
    return "".join(t.get("plain_text", "") for t in items).strip()

def get_email(prop):
    if not prop: return ""
    return (prop.get("email") or "").strip().lower()

def get_url(prop):
    if not prop: return ""
    return (prop.get("url") or "").strip().lower()

def normalize(s):
    return re.sub(r'[^a-z0-9]', '', s.lower()) if s else ""

def extract_domain(email):
    if "@" not in email: return None
    return email.split("@")[1].strip().lower()

def extract_company_domain(website):
    if not website: return None
    if not website.startswith("http"): website = "https://" + website
    try:
        parsed = urlparse(website)
        domain = parsed.netloc or parsed.path
        return re.sub(r'^www\.', '', domain).strip().lower() or None
    except: return None

def fuzzy_match(a, b, threshold=0.85):
    if not a or not b: return False
    if a == b: return True
    if a.split(".")[0] == b.split(".")[0]: return True
    return SequenceMatcher(None, a.split(".")[0], b.split(".")[0]).ratio() >= threshold

# ── Notion API ───────────────────────────────────────────────────────────────

def query_db(db_id, filter_body=None):
    pages, cursor = [], None
    page_num = 0
    while True:
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        if filter_body: body["filter"] = filter_body
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=HEADERS, json=body
        )
        r.raise_for_status()
        data = r.json()
        pages.extend(data["results"])
        page_num += 1
        print(f"  page {page_num} ({len(pages)} items)...")
        if not data.get("has_more"): break
        cursor = data["next_cursor"]
        time.sleep(0.3)
    return pages

def link_company(contact_id, company_id):
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{contact_id}",
        headers=HEADERS,
        json={"properties": {"Company": {"relation": [{"id": company_id}]}}}
    )
    return r.status_code == 200

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n📋 Fetching contacts without a company...")
    contacts = query_db(CONTACTS_DB, {"property": "Company", "relation": {"is_empty": True}})
    print(f"✅ {len(contacts)} unlinked contacts.\n")

    print("🏢 Fetching companies...")
    companies = query_db(COMPANIES_DB)
    print(f"✅ {len(companies)} companies loaded.\n")

    # Build indexes
    by_domain, by_name = {}, {}
    for c in companies:
        props = c.get("properties", {})
        name    = get_text(props.get("Name"))
        website = get_url(props.get("website") or props.get("Website") or props.get("URL") or {})
        domain  = extract_company_domain(website)
        if domain: by_domain[domain] = (c["id"], name)
        if name:
            norm = normalize(name)
            if norm: by_name[norm] = (c["id"], name)

    print(f"🔍 {len(by_domain)} companies with domain | {len(by_name)} with name.\n")

    auto_linked, to_csv = [], []

    for contact in contacts:
        props = contact.get("properties", {})
        name    = get_text(props.get("Name"))
        first   = get_text(props.get("First Name"))
        last    = get_text(props.get("Last Name"))
        email   = get_email(props.get("Email Address"))
        domain  = extract_domain(email)
        display = name or f"{first} {last}".strip() or "Unknown"

        if not domain or domain in GENERIC_DOMAINS:
            to_csv.append({"Contact Name": display, "Email": email, "Domain": domain or "", 
                          "Suggested Company": "", "Match Type": "generic/no email", "Page ID": contact["id"]})
            continue

        matched_id, matched_name, match_type = None, "", ""

        # 1. Exact domain
        if domain in by_domain:
            matched_id, matched_name = by_domain[domain]
            match_type = "exact domain"
        else:
            # 2. Fuzzy domain
            for d, (cid, cname) in by_domain.items():
                if fuzzy_match(domain, d):
                    matched_id, matched_name, match_type = cid, cname, f"fuzzy domain ({d})"
                    break

        if not matched_id:
            base = normalize(domain.split(".")[0])
            # 3. Domain base = company name
            if base in by_name:
                matched_id, matched_name = by_name[base]
                match_type = "name = domain base"
            else:
                # 4. Fuzzy name
                best = 0
                for norm, (cid, cname) in by_name.items():
                    ratio = SequenceMatcher(None, base, norm).ratio()
                    if ratio > best and ratio >= 0.88:
                        best = ratio
                        matched_id, matched_name, match_type = cid, cname, f"fuzzy name ({cname}, {ratio:.0%})"

        if matched_id:
            auto_linked.append({"contact_id": contact["id"], "contact_name": display,
                                "email": email, "company_id": matched_id,
                                "company_name": matched_name, "match_type": match_type})
        else:
            to_csv.append({"Contact Name": display, "Email": email, "Domain": domain,
                          "Suggested Company": "", "Match Type": "no match", "Page ID": contact["id"]})

    print(f"✅ Auto-linkable: {len(auto_linked)}")
    print(f"📄 No match (CSV): {len(to_csv)}\n")

    print("--- PREVIEW (first 15) ---")
    for item in auto_linked[:15]:
        print(f"  {item['contact_name']:<30} → {item['company_name']:<25} [{item['match_type']}]")
    print("--------------------------\n")

    confirm = input(f"Apply {len(auto_linked)} links in Notion? (yes/no): ").strip().lower()
    if confirm == "yes":
        linked, errors = 0, 0
        for i, item in enumerate(auto_linked):
            if link_company(item["contact_id"], item["company_id"]): linked += 1
            else: errors += 1
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(auto_linked)} | ✅ {linked} | ❌ {errors}")
            time.sleep(0.35)
        print(f"\n🎉 Linked: {linked} | Errors: {errors}")

    if to_csv:
        with open("unlinked_contacts.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Contact Name","Email","Domain","Suggested Company","Match Type","Page ID"])
            writer.writeheader()
            writer.writerows(to_csv)
        print(f"\n📊 {len(to_csv)} contacts exported → unlinked_contacts.csv")

if __name__ == "__main__":
    main()
