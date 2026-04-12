#!/usr/bin/env python3
"""
notion-crm-toolkit / 01_split_names.py
---------------------------------------
Splits a combined "Name" field into separate "First Name" + "Last Name" fields.

Works in two modes:
- If Name has 2+ words → split on first space
- If Name is a single word or missing → tries to infer from email address
- If still uncertain → sets "please fill to enrich"

Only updates contacts where First Name OR Last Name is currently empty.
Exports uncertain contacts to uncertain_contacts.json for manual review.

Usage:
    python 01_split_names.py
"""

import requests
import json
import re
import time

# ── Config ──────────────────────────────────────────────────────────────────

NOTION_TOKEN  = input("Notion integration token (secret_xxx): ").strip()
DATABASE_URL  = input("Contacts database URL: ").strip()
DATABASE_ID   = DATABASE_URL.split("notion.so/")[-1].split("?")[0].split("/")[-1].replace("-", "")
DATABASE_ID   = DATABASE_ID[:8] + "-" + DATABASE_ID[8:12] + "-" + DATABASE_ID[12:16] + "-" + DATABASE_ID[16:20] + "-" + DATABASE_ID[20:]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

PLACEHOLDER = "please fill to enrich"

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "live.com", "msn.com", "me.com", "aol.com", "protonmail.com",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_text(prop):
    if not prop: return ""
    items = prop.get("rich_text") or prop.get("title") or []
    return "".join(t.get("plain_text", "") for t in items).strip()

def get_email(prop):
    if not prop: return ""
    return (prop.get("email") or "").strip().lower()

def infer_from_email(email):
    if not email or "@" not in email: return None, None
    domain = email.split("@")[1]
    if domain in GENERIC_DOMAINS: return None, None
    local = re.sub(r'\d+', '', email.split("@")[0].lower())
    parts = [p.capitalize() for p in re.split(r'[.\-_]', local) if len(p) > 1]
    if len(parts) >= 2: return parts[0], parts[-1]
    if len(parts) == 1: return parts[0], None
    return None, None

def parse_name(name, email):
    """Returns (first_name, last_name, confident)"""
    name = (name or "").strip()
    if name:
        tokens = name.split()
        if len(tokens) >= 2:
            return tokens[0], " ".join(tokens[1:]), True
        fn, ln = infer_from_email(email)
        if fn and ln: return fn, ln, False
        return tokens[0], PLACEHOLDER, False
    fn, ln = infer_from_email(email)
    if fn and ln: return fn, ln, False
    if fn: return fn, PLACEHOLDER, False
    return PLACEHOLDER, PLACEHOLDER, False

# ── Notion API ───────────────────────────────────────────────────────────────

def fetch_all_pages():
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
        pages.extend(data["results"])
        page_num += 1
        print(f"  Fetched page {page_num} ({len(pages)} contacts)...")
        if not data.get("has_more"): break
        cursor = data["next_cursor"]
        time.sleep(0.3)
    return pages

def update_contact(page_id, first_name, last_name):
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=HEADERS,
        json={"properties": {
            "First Name": {"rich_text": [{"text": {"content": first_name}}]},
            "Last Name":  {"rich_text": [{"text": {"content": last_name}}]},
        }}
    )
    return r.status_code == 200

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n📋 Fetching contacts...")
    pages = fetch_all_pages()
    print(f"✅ {len(pages)} contacts loaded.\n")

    to_update = []
    for p in pages:
        props = p.get("properties", {})
        fn = get_text(props.get("First Name"))
        ln = get_text(props.get("Last Name"))
        if fn and ln and fn != PLACEHOLDER and ln != PLACEHOLDER:
            continue
        name  = get_text(props.get("Name"))
        email = get_email(props.get("Email Address"))
        first, last, confident = parse_name(name, email)
        to_update.append({
            "id": p["id"], "name": name, "email": email,
            "first_name": first, "last_name": last, "confident": confident,
        })

    print(f"📝 {len(to_update)} contacts to update.\n")
    print("--- PREVIEW (first 10) ---")
    for c in to_update[:10]:
        tag = "✅" if c["confident"] else "⚠️ "
        print(f"  {tag} '{c['name']}' / '{c['email']}' → '{c['first_name']}' | '{c['last_name']}'")
    print("--------------------------\n")

    confirm = input(f"Update {len(to_update)} contacts? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return

    updated, errors, uncertain = 0, 0, []
    for i, c in enumerate(to_update):
        ok = update_contact(c["id"], c["first_name"], c["last_name"])
        if ok:
            updated += 1
            if not c["confident"]: uncertain.append(c)
        else:
            errors += 1
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(to_update)} | ✅ {updated} | ❌ {errors}")
        time.sleep(0.35)

    print(f"\n🎉 Done! Updated: {updated} | Errors: {errors}")
    if uncertain:
        with open("uncertain_contacts.json", "w") as f:
            json.dump(uncertain, f, indent=2, ensure_ascii=False)
        print(f"⚠️  {len(uncertain)} uncertain → saved to uncertain_contacts.json")

if __name__ == "__main__":
    main()
