# 🗂️ Notion CRM Toolkit
**Free, open-source scripts and no-code playbooks for founders who built their CRM on Notion.**  
No SaaS. No subscriptions. Just tools you run locally or wire up in Make.com that talk directly to your Notion database.

---

## 🐍 Scripts

| # | Script | What it does | Requires |
|---|--------|-------------|---------|
| 01 | `split_names.py` | Splits a single "Full Name" field into "First Name" + "Last Name" | Notion token |
| 02 | `link_companies.py` | Matches contacts to companies via email domain + fuzzy name matching | Notion token |
| 03 | `find_linkedin.py` | Finds missing LinkedIn profiles using First Name + Last Name + Company | Notion token + Serper API key |

> More scripts coming. PRs welcome.

---

## ⚡ Playbooks (No-code automations)

Make.com workflows that extend your Notion CRM without writing code.

| # | Playbook | What it does | Requires |
|---|----------|-------------|---------|
| 01 | [Get Phone from C-Level](https://github.com/adrien-seavium/notion-crm-toolkit/blob/main/playbooks/fullenrich-notion-make-playbook.md) | Enriches a contact's phone number via FullEnrich, updates Notion, notifies by email | Make.com + FullEnrich + Gmail |

> More playbooks coming. Built one? Open a PR.

---

## Quickstart

### Python scripts

#### 1. Get your Notion integration token
1. Go to [notion.so/my-integrations](https://notion.so/my-integrations)
2. Click **"New integration"** → give it a name → copy the token (`secret_xxx`)
3. Open your Notion database → click **"..."** → **"Connections"** → add your integration

#### 2. Install dependencies
```bash
pip install requests
```

#### 3. Run any script
```bash
python scripts/01_split_names.py
```
Each script will prompt you for your token and database URL — nothing is hardcoded.

### Make.com playbooks

Each playbook in `/playbooks` includes:
- Full step-by-step module configuration
- Exact field mappings
- Router logic and filter conditions
- Tips, gotchas, and GDPR notes

Follow the instructions in each playbook's README. No coding required.

---

## Requirements

**Python scripts:**
- Python 3.8+
- `requests` library
- A Notion account with an integration token
- Your database URL (copy from browser address bar)

**Make.com playbooks:**
- A [Make.com](https://make.com) account (free tier works for low volume)
- A Notion Internal Integration token
- API keys for third-party tools (FullEnrich, etc.) — linked in each playbook

---

## Philosophy

- ✅ **Local only** — your data never leaves your machine (scripts)
- ✅ **No setup hell** — one file, one command
- ✅ **Safe by default** — every script previews changes before writing anything
- ✅ **No credentials in code** — tokens stay in your environment or Make's connection manager
- ✅ **Open source** — fork it, adapt it, build on it

---

## Contributing

Built something useful for your Notion CRM? Open a PR.

**Scripts** should follow the same pattern: prompt for token → preview → confirm → execute.  
**Playbooks** should follow the same structure: stack → architecture → step-by-step → Notion fields → tips.

---

Built with ☕ by [Seavium](https://seavium.com) — offshore vessel intelligence platform.
