# 🗂️ Notion CRM Toolkit

**Free, open-source Python scripts for founders who built their CRM on Notion.**

No SaaS. No subscriptions. Just scripts you run locally that talk directly to your Notion database.

---

## Scripts

| # | Script | What it does | Requires |
|---|--------|-------------|---------|
| 01 | `split_names.py` | Splits a single "Full Name" field into "First Name" + "Last Name" | Notion token |
| 02 | `link_companies.py` | Matches contacts to companies via email domain + fuzzy name matching | Notion token |
| 03 | `find_linkedin.py` | Finds missing LinkedIn profiles using First Name + Last Name + Company | Notion token + Serper API key |

> More scripts coming. PRs welcome.

---

## Quickstart

### 1. Get your Notion integration token

1. Go to [notion.so/my-integrations](https://notion.so/my-integrations)
2. Click **"New integration"** → give it a name → copy the token (`secret_xxx`)
3. Open your Notion database → click **"..."** → **"Connections"** → add your integration

### 2. Install dependencies

```bash
pip install requests
```

### 3. Run any script

```bash
python scripts/01_split_names.py
```

Each script will prompt you for your token and database URL — nothing is hardcoded.

---

## Requirements

- Python 3.8+
- `requests` library
- A Notion account with an integration token
- Your database URL (copy from browser address bar)

---

## Philosophy

- ✅ **Local only** — your data never leaves your machine
- ✅ **No setup hell** — one file, one command
- ✅ **Safe by default** — every script previews changes before writing anything
- ✅ **Open source** — fork it, adapt it, build on it

---

## Contributing

Built something useful for your Notion CRM? Open a PR.
Each script should follow the same pattern: prompt for token → preview → confirm → execute.

---

Built with ☕ by [Seavium](https://seavium.com) — offshore vessel intelligence platform.
