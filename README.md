# Frosty Connections — AI Listing Generation System (v2)
**Built by Haxxcel Solutions**

---

## How It Works

1. Open the admin panel in any browser
2. Enter a business name or URL → click Generate
3. System scrapes the website (Firecrawl, including logo/cover/gallery images) → AI generates listing content (GPT-4o) → validates confidence → saves to Google Sheets
4. Approved listings go to **Approved** tab, flagged ones go to **Review Queue**
5. Click Export CSV → import into eDirectory

---

## What This System Generates vs. What You Manage Manually

This system was built to match Frosty Connections' actual **Add Listing** form. To keep things clean and avoid the AI making business/billing decisions, the scope is split as follows:

### Generated Automatically
- Listing Title
- Summary Description (250 chars)
- Description (long-form, formatted)
- Categories 1-5
- SEO Title, Slug URL, SEO Keywords (max 15), SEO Description
- Search Keywords (max 20, separate from SEO keywords — powers on-site search)
- E-mail, Phone, Additional Phone + Label, URL
- Address, Address2, Zip Code, Country, Reference (location landmark)
- Social links (Facebook, Instagram, X, LinkedIn, YouTube)
- Logo Image, Cover Image, Photo Gallery — URLs pulled directly from the business's website
- Renewal Date (auto-set to 1 year from generation)
- Product: **"N-P Free"** (fixed default)
- Listing Template: **"IP-Core"** (fixed default)
- Status: **"Active"**

### Managed Manually by You (Not Automated)
- **Account** — defaults to "No Owner" in eDirectory; listing stays unclaimed until the business claims it
- **Total Allowed Leads**
- **Disable Claim Feature** checkbox
- **Listing Badges** (Legacy Member, Founding Partner, Partner, Veteran) — these are designations you assign
- **Upgrading Product/Listing Template** for specific listings — this is a membership/billing decision, not content generation

### Why Product & Listing Template Are Fixed
These dropdowns (Professional, SPAerates content — it shouldn't decide what tier a business is on. Every generated listing defaults to the free RK Partner, IP-Expansion, etc.) are **membership/subscription tiers**, not content categories. The AI gentier (N-P Free / IP-Core) so it's live and functional. You can upgrade specific listings manually or in bulk through eDirectory whenever appropriate.

---

## Project Structure

```
frosty-ai/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── service_account.json     # you create this (see Step 2)
├── static/
│   └── index.html           # admin panel
├── models/
│   └── listing.py
├── routers/
│   ├── listings.py           # POST /listings/generate
│   └── export.py             # GET /export/csv, /export/stats, /export/categories
└── services/
    ├── scraper.py             # Firecrawl — content + image extraction
    ├── enricher.py            # GPT-4o — generates listing content
    ├── validator.py           # confidence scoring
    ├── sheets.py              # Google Sheets read/write
    └── exporter.py            # CSV generation
```

---

## Step 1 — Get Your API Keys

### OpenAI API Key
1. https://platform.openai.com → sign up/login
2. Profile → **API Keys** → Create new secret key
3. Add billing credit (minimum $5) at platform.openai.com/account/billing

### Firecrawl API Key
1. https://firecrawl.dev → sign up → Dashboard → API Keys
2. Free plan = 500 credits/month

---

## Step 2 — Google Sheets Setup

### 2a. Create the Sheet
1. https://sheets.google.com → new blank spreadsheet
2. Name it "Frosty Connections Listings"
3. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_PART/edit
   ```

### 2b. Create a Service Account
1. https://console.cloud.google.com → new project
2. Enable **Google Sheets API** and **Google Drive API**
3. Credentials → Create Credentials → Service Account → Create → Done
4. Open the service account → Keys → Add Key → Create new key → JSON
5. Save as `service_account.json` in project root

### 2c. Share the Sheet
1. Open `service_account.json`, find `client_email`
2. Share your Google Sheet with that email → role: **Editor**

The system auto-creates 4 tabs:
- **All Listings** — every generated listing
- **Approved** — score ≥ 0.75, ready for export
- **Review Queue** — needs manual review
- **Categories** — editable category list (see below)

---

## Step 3 — Configure Environment

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=sk-...
FIRECRAWL_API_KEY=fc-...
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
GOOGLE_SHEET_ID=your_google_sheet_id_here
CONFIDENCE_THRESHOLD=0.75
```

---

## Step 4 — Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open: **http://localhost:8000** (admin panel)
API docs: **http://localhost:8000/docs**

---

## Step 5 — Deploy to Railway

### Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/frosty-ai.git
git push -u origin main
```

### Deploy
1. https://railway.app → New Project → Deploy from GitHub repo
2. Select your repo — Railway auto-detects FastAPI

### Environment Variables (Railway → Variables tab)
```
OPENAI_API_KEY        = sk-...
FIRECRAWL_API_KEY     = fc-...
GOOGLE_SHEET_ID       = your_sheet_id
CONFIDENCE_THRESHOLD  = 0.75
```

### service_account.json on Railway
Paste the JSON contents as an environment variable, or use Railway's file mount (Pro plan). If using an env var, update `config.py` / `services/sheets.py` to read credentials from the env var instead of a file path.

### Start Command
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Your live URL: `https://your-app.up.railway.app` — this is the admin panel, share with Pothga directly.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Admin panel |
| POST | `/listings/generate` | Generate a listing |
| GET | `/export/csv` | Download approved listings as CSV |
| GET | `/export/stats` | Listing counts |
| GET | `/export/categories` | Current category list |
| GET | `/health` | Health check |
| GET | `/docs` | API documentation |

### Generate — Request
```json
{ "business_name": "Vilter Manufacturing", "url": "https://www.vilter.com" }
```
At least one of `business_name` or `url` is required.

### Generate — Response
```json
{
  "success": true,
  "listing": {
    "listing_title": "Vilter Manufacturing",
    "category_1": "Industrial Refrigeration->Equipment & Components",
    "seo_keywords": "ammonia compressors || industrial refrigeration || ...",
    "search_keywords": "...",
    "logo_image_url": "https://...",
    "cover_image_url": "https://...",
    "photo_gallery_urls": ["https://...", "https://..."],
    "confidence_score": 0.92,
    "review_status": "approved"
  },
  "message": "Listing approved and saved to Google Sheets."
}
```

---

## Managing Categories

Categories live in the **"Categories"** tab — auto-created on first run.

### Add a Category
Add a new row in `Parent->Child` format, e.g. `Industrial Refrigeration->Heat Exchangers`. No code changes needed.

### Remove a Category
Delete the row. The AI stops assigning it to new listings.

### Format Rules
- Always `Parent->Child` (no spaces around `->`)
- Each listing can have up to 5 categories (Category 1 required, 2-5 optional)
- If a listing doesn't fit any category well, it's flagged for review

### Check Current Categories
`GET https://your-app.up.railway.app/export/categories`

### Fallback
If the Categories tab is empty, the system uses 15 built-in defaults.

---

## Confidence Scoring

| Score | Status | Action |
|-------|--------|--------|
| ≥ 0.75, no hallucination flags | Approved | Auto-saved to Approved tab |
| < 0.75 or hallucination detected | Needs Review | Saved to Review Queue tab |

### What Triggers a Flag
- Phone/email in AI output but not found in scraped content (possible hallucination)
- Address not confirmed in source
- Missing required fields (title, descriptions, primary category, search keywords)
- Category (1-5) not in your Categories tab — that category removed, listing flagged
- No images found on the business website
- SEO/search keyword counts exceeding limits (15/20) — auto-truncated
- Description/title length over limits — auto-truncated

---

## Images

The system extracts three types of images directly from the business's website during scraping:

| Field | Recommended Size (per eDirectory) |
|-------|-----------------------------------|
| Logo Image | 250×250 px |
| Cover Image | 1920×480 px |
| Photo Gallery | 1024×768 px (multiple) |

These are saved as **URLs** — Pothga/eDirectory will need to download and re-upload these images when importing, or the CSV import may support image URLs directly depending on eDirectory's import tool. If a business's website doesn't have clear logo/cover/gallery images, these fields are left blank and flagged.

---

## Google Sheets — Column Structure

All 3 listing tabs (All Listings, Approved, Review Queue) share these 39 columns:

| # | Columns |
|---|---------|
| 1-3 | Listing Title, Summary Description, Description |
| 4-8 | Category 1-5 |
| 9-12 | Product, Listing Template, Status, Renewal Date |
| 13-22 | Email, URL, Phone, Additional Phone, Additional Phone Label, Address, Address2, Zip Code, Country, Reference |
| 23-27 | Facebook, Instagram, X, LinkedIn, YouTube |
| 28-32 | SEO Title, Slug URL, SEO Keywords, SEO Description, Search Keywords |
| 33-35 | Logo Image URL, Cover Image URL, Photo Gallery URLs |
| 36-39 | Confidence Score, Flags, Review Status, Generated At (internal — stripped from CSV export) |

CSV export = columns 1-35.

---

## Monthly Cost Estimate

| Service | Cost |
|---------|------|
| Railway hosting | $5–10/mo |
| Firecrawl API | $0–50/mo (500 free credits) |
| OpenAI API (GPT-4o) | $10–40/mo depending on volume |
| Google Sheets | Free |
| **Total** | **$15–100/mo** |

---

## Troubleshooting

**"Could not scrape URL"** — site may block scrapers. Try providing both business_name and url.

**"AI enrichment failed"** — check OpenAI API key and billing credit.

**Google Sheets not saving** — confirm service account has Editor access; confirm GOOGLE_SHEET_ID is just the ID, not the full URL.

**No images found** — some business websites don't have a dedicated logo/cover/gallery setup that Firecrawl can detect; these fields will be blank and the listing flagged for review.

**Railway deploy failing** — start command must be `uvicorn main:app --host 0.0.0.0 --port $PORT`; confirm all env vars are set.

---

*Haxxcel Solutions — contact@haxxcelsolutions.com*
*Built for Frosty Connections — Quote HX-2026-001*
