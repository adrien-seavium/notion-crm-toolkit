# 📞 Playbook — Get Phone Number from C-Level via FullEnrich + Make.com + Notion

> **Goal:** Automatically enrich a contact stored in a Notion CRM (phone number via FullEnrich) triggered by a webhook, then notify by email and update the Notion record based on the enrichment result.
>
> 💡 Part of the [notion-crm-toolkit](https://github.com/adrien-seavium/notion-crm-toolkit) — a collection of no-code/low-code automations for B2B sales teams built on top of Notion.

---

## 🧩 Stack

| Tool | Role |
|---|---|
| **Notion** | CRM source of truth — contacts DB with name, company, email, position |
| **FullEnrich** | Phone enrichment API (~10 credits per enrichment attempt) |
| **Make.com** | Automation backbone |
| **Gmail** | Notification on enrichment result (success or failure) |

---

## 🔁 Make.com Scenario — Full Architecture

```
Webhooks [1] → FullEnrich [4] → Router [9] ──► (1st: enrich success) → Gmail [8] → Notion [6]
                                            └──► (2nd: no enrich)     → Gmail [10]
```

---

## Step-by-step Configuration

---

### Module 1 — Webhooks (Custom webhook)

**What it does:** Entry point of the scenario. Listens for an inbound HTTP POST call triggered from Notion (via a button, automation, or external script).

**Setup:**
- Create a new Custom Webhook in Make → name it `enrich hook` (or any name)
- Make will generate a unique URL like `https://hook.eu2.make.com/xxxxxxxxxxxxxxxxx` — **keep this private, never commit it to Git**
- Click **"Redetermine data structure"** and send a test payload once to let Make learn the fields

**Expected inbound payload (example):**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "company": "TARGET_COMPANY",
  "email": "john.doe@targetcompany.com",
  "notion_page_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

> 💡 You can trigger this webhook from a Notion button linked to an automation, or manually via cURL / Postman for testing.

---

### Module 4 — FullEnrich (Enrich a Contact)

**What it does:** Takes contact info from the webhook payload and queries FullEnrich to find a mobile phone number.

**Connection:** Connect your FullEnrich account via API key (stored securely in Make's connection manager — never hardcode it).

**Field mapping (exact configuration from Make UI):**

| FullEnrich field | Make mapping |
|---|---|
| First Name *(required)* | `{{1.data.properties.First Name.rich_text[].plain_text}}` |
| Last Name *(required)* | `{{1.data.properties.Last Name.rich_text[].plain_text}}` |
| Company Name | `{{1.data.properties.enrich_company.formula.string}}` |
| Domain | *(leave empty — optional)* |
| LinkedIn URL | *(leave empty — optional but improves match rate)* |
| Webhook URL | *(leave empty for synchronous mode)* |

> 💡 `enrich_company` is a **Notion formula field** that normalizes the company name string for better FullEnrich matching. Create it in your Notion DB if needed (e.g. a formula that returns the company name as plain text).

**Output:** `{{4.phone}}` — the enriched mobile number, or empty if not found.

---

### Module 9 — Router

**What it does:** Splits the flow into two branches based on whether FullEnrich returned a phone number.

**Branch 1 — `enrich success`** (label visible in Make UI)
- **Condition:** `{{4.phone}}` exists / is not empty
- → Proceeds to Gmail [8] then Notion [6]

**Branch 2 — `no enrich`** (label visible in Make UI)
- **Condition:** `{{4.phone}}` does not exist / is empty
- → Proceeds to Gmail [10] (failure notification only)

---

### Module 8 — Gmail (Success notification)

**What it does:** Sends an email alert to the sales team when enrichment succeeds.

**Configuration:**
- **To:** `sales@yourcompany.com` *(your team sales inbox)*
- **Subject:** `New contact enriched`
- **Body type:** Collection of contents (text, images, etc.)
- **Body — Content 1 (Text):**

```
Hi team,

A new contact has just been enriched via FullEnrich. ✅

Name: [First Name] [Last Name]
Company: [Company]
Phone: [Enriched phone number]

The Notion record has been updated automatically.

— CRM Automation
```

> In Make, replace the bracketed values with the actual mapped variables from modules 1 and 4.

---

### Module 6 — Notion (Update record)

**What it does:** Writes the enriched phone number back into the Notion contact page.

**Connection:** Connect via Notion Internal Integration token (stored in Make — never exposed publicly).

> ⚠️ **Important:** Make will suggest switching from `Database (Legacy)` to `Data Source` — **do it**. It prevents future errors with multi-source Notion DBs. Re-check all field mappings after the switch.

**Configuration:**

| Field | Value |
|---|---|
| Update By | `Database (Legacy)` → migrate to `Data Source` when prompted |
| Database ID | Your Notion contacts DB ID (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) — find it in the Notion page URL |
| Database Item ID | The Notion page ID passed from the webhook payload (mapped from module 1) |
| Phone from FullEnrich | `{{4.phone}}` |
| Latest Update | `{{now}}` |

---

### Module 10 — Gmail (Failure notification)

**What it does:** Sends an alert when FullEnrich couldn't find a phone number so the team can act manually.

**Configuration:**
- **To:** `sales@yourcompany.com`
- **Subject:** `Enrichment failed`
- **Body type:** Collection of contents (text, images, etc.)
- **Body — Content 1 (Text):**

```
Hi team,

An enrichment attempt via FullEnrich did not return a phone number. ❌

Name: [First Name] [Last Name]
Company: [Company]
Email: [Email Address]

👉 Next steps:
- Try manual LinkedIn lookup
- Use the "Enrich Phone (50ct)" button directly on FullEnrich dashboard
- Double-check if company name / email domain is correct in Notion

— CRM Automation
```

---

## 🗃️ Notion Database — Required fields

| Field name | Type | Notes |
|---|---|---|
| First Name | Text (rich_text) | Required for enrichment |
| Last Name | Text (rich_text) | Required for enrichment |
| Email Address | Email | Used as enrichment signal |
| enrich_company | Formula | Normalized company name string — improves FullEnrich match rate |
| Phone | Phone | Manual / primary field |
| Phone from FullEnrich | Phone | Auto-populated by Make on success |
| Enrich Phone (50ct) | Button | Triggers the webhook manually from Notion |
| Position | Text | e.g. "Chartering Development Manager" |
| In touch with | Person | Assign to the team member managing the contact |
| Latest Update | Date | Auto-updated by Make on each enrichment run |

---

## 💡 Tips & Gotchas

- **Credit cost:** FullEnrich charges ~50 credits per attempt, successful or not. The Router avoids wasted calls by branching cleanly on empty results.
- **Webhook URL security:** Never commit your Make webhook URL to a public repo. Store it in a `.env` file or your team's secrets manager. Rotate it if leaked.
- **Notion Legacy → Data Source:** Migrate when Make prompts you — it avoids future bugs. Re-map all fields after migration.
- **Better match rate:** Adding a LinkedIn URL to the FullEnrich module significantly improves phone match success (~30% uplift in practice). Worth adding to your Notion DB as a field.
- **Batch mode:** To enrich multiple contacts at once, replace the webhook trigger with a "Watch Notion Database" trigger filtered on a `to_enrich = true` checkbox instead of per-contact webhooks.
- **Rate limits:** If running bulk enrichments, add a Make "Sleep" module (1–2 seconds) between iterations to avoid hitting FullEnrich rate limits.
- **GDPR:** Phone numbers sourced via third-party enrichment — ensure your use is covered under legitimate interest or explicit consent in your privacy policy.

---

## 🔗 Resources

- [FullEnrich](https://fullenrich.com) — phone & email enrichment API
- [Make.com Webhook Module docs](https://www.make.com/en/help/tools/webhooks)
- [Make.com Notion Integration docs](https://www.make.com/en/integrations/notion)
- [notion-crm-toolkit](https://github.com/adrien-seavium/notion-crm-toolkit) — this repo

---

*Built by the Seavium sales team — April 2026*  
*No-code automation. Ship fast. Close faster.*
