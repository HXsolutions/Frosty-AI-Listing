import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from openai import AsyncOpenAI
from config import settings
from models.listing import Listing, SocialLinks

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """
You are a content writer for Frosty Connections — a specialized industrial refrigeration
directory focused on ammonia refrigeration, natural refrigerants, safety compliance,
and workforce development in the USA.

STRICT RULES:
- Never invent phone, address, email, or social links not present in the source content
- If a field cannot be confirmed from the source, return null
- summary_description:
  - 180-250 characters
  - Single sentence
  - Clearly describe the company, primary services, and target industries
  - Professional and factual
  - No marketing language
- - description must be a professional business directory profile between 300 and 700 words.
- Write 4-6 substantial paragraphs.
- Paragraph 1: company overview and primary specialization.
- Paragraph 2: core products, services, and capabilities.
- Paragraph 3: industries served, technologies, and operational strengths.
- Paragraph 4: geographic reach, facilities, partnerships, certifications, or notable differentiators when available.
- Additional paragraphs may be included if sufficient verified information exists.
- Use a neutral, factual, directory-style tone.
- Do not use marketing hype or promotional language.
- Never copy source text verbatim.
- Fully paraphrase all information.
- Incorporate verified details from all available source content.
- End with:
  "Verified information was obtained from [Company]'s public website and related corporate resources."
- seo_title: max 60 characters
- slug_url: lowercase, hyphenated, URL-safe (e.g. "vilter-manufacturing")
- seo_keywords: pipe-separated, MAXIMUM 15 keywords — "kw1 || kw2 || kw3"
- seo_description: max 250 characters
- search_keywords:
  - Generate up to 20 highly relevant search phrases
  - Include services, products, technologies, industries served, and specialties
  - Use both broad and niche industry terminology
  - Avoid duplicates
  - Format: kw1 || kw2 || kw3 — "kw1 || kw2 || kw3"
  (search_keywords can be broader than seo_keywords — they power on-site search)
- category_1 through category_5: use ONLY values from the provided categories list,
  in Parent->Child format. category_1 is required, others optional.
- map_reference: minimum state-level location text. If city/state known use both.
  If global company write scope e.g. "Global provider of cold storage solutions."
  This field is REQUIRED — always return something, never null.
- country: "United States" if US-based
- confidence_notes: structured verification notes in this exact format:
  "VERIFIED: [list what was confirmed from the source — URL, phone, address, services, etc.]
   INFERRED: [list what was reasonably inferred but not explicitly stated — e.g. category selection]
   MISSING: [list what could not be found — e.g. Address 2 not publicly listed]"
  Be specific and honest. This is for internal review quality control.
- Do NOT generate: product, listing_template, status, renewal_date, account,
  total_allowed_leads, disable_claim_feature, or listing_badges.
- All content must be paraphrased from verified sources — never copy verbatim text.
QUALITY STANDARD:

Descriptions should resemble professionally researched supplier-directory profiles.

The generated listing should be comparable in depth and structure to entries found in major B2B directories, logistics directories, industrial supplier databases, and trade association membership directories.

When sufficient information exists, maximize useful detail rather than producing generic summaries.

Return ONLY valid JSON. No markdown fences. No explanation.
"""

PROMPT = """
Business Name: {business_name}
URL: {url}

Scraped Content:
{markdown}

Extracted Data:
{extracted}

Available Categories:
{categories}

Return JSON with these exact fields:
{{
  "listing_title": "string",
  "summary_description": "string (max 250 chars)",
  "description": "string (300-700 words, professional business directory profile, 4-6 substantial paragraphs, fully paraphrased, basic HTML allowed)",
  "category_1": "string or null",
  "category_2": "string or null",
  "category_3": "string or null",
  "category_4": "string or null",
  "category_5": "string or null",
  "email": "string or null",
  "url": "string or null",
  "phone": "string or null",
  "additional_phone": "string or null",
  "additional_phone_label": "string or null",
  "address": "string or null",
  "address2": "string or null",
  "zip_code": "string or null",
  "country": "string or null",
  "map_reference": "string — REQUIRED, minimum state-level location context",
  "social_links": {{
    "facebook": "string or null",
    "instagram": "string or null",
    "x": "string or null",
    "linkedin": "string or null",
    "youtube": "string or null"
  }},
  "seo_title": "string (max 60 chars)",
  "slug_url": "string (url-safe slug)",
  "seo_keywords": "kw1 || kw2 || ... (max 15)",
  "seo_description": "string (max 250 chars)",
  "search_keywords": "kw1 || kw2 || ... (max 20)",
  "confidence_notes": "VERIFIED: ...\\nINFERRED: ...\\nMISSING: ..."
}}
"""


async def enrich_listing(
    business_name: str,
    url: str,
    scraped: dict,
    categories: list[str],
) -> Optional[Listing]:

    extracted = scraped.get("extracted", {})

    prompt = PROMPT.format(
        business_name=business_name or "Unknown",
        url=url or "Unknown",
        markdown=scraped.get("markdown", "")[:35000],
        extracted=json.dumps(extracted, indent=2),
        categories="\n".join(f"- {c}" for c in categories),
    )

    try:
        res = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2200,
            response_format={"type": "json_object"},
        )
        data = json.loads(res.choices[0].message.content)

        social = data.get("social_links", {}) or {}
        social_links = SocialLinks(
            facebook=social.get("facebook") or extracted.get("facebook"),
            instagram=social.get("instagram") or extracted.get("instagram"),
            x=social.get("x") or extracted.get("x_twitter"),
            linkedin=social.get("linkedin") or extracted.get("linkedin"),
            youtube=social.get("youtube") or extracted.get("youtube"),
        )

        # Renewal date — 1 year from generation date
        renewal_date = (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d")

        # Images — pulled directly from scraped extraction (not AI-generated)
        logo_image_url = extracted.get("logo_image_url")
        cover_image_url = extracted.get("cover_image_url")
        gallery = extracted.get("gallery_image_urls", []) or []
        if not isinstance(gallery, list):
            gallery = []

        return Listing(
            listing_title=data["listing_title"],
            summary_description=data["summary_description"][:250],
            description=data["description"],
            category_1=data.get("category_1"),
            category_2=data.get("category_2"),
            category_3=data.get("category_3"),
            category_4=data.get("category_4"),
            category_5=data.get("category_5"),
            product="N-P Free",
            listing_template="IP-Core",
            status="Active",
            renewal_date=renewal_date,
            email=data.get("email") or extracted.get("email"),
            url=data.get("url") or url,
            phone=data.get("phone") or extracted.get("phone"),
            additional_phone=data.get("additional_phone") or extracted.get("additional_phone"),
            additional_phone_label=data.get("additional_phone_label"),
            address=data.get("address") or extracted.get("address"),
            address2=data.get("address2") or extracted.get("address2"),
            zip_code=data.get("zip_code") or extracted.get("zip_code"),
            country=data.get("country") or extracted.get("country"),
            reference=data.get("map_reference") or data.get("reference") or extracted.get("landmark_reference"),
            map_reference=data.get("map_reference") or data.get("reference") or extracted.get("landmark_reference"),
            social_links=social_links,
            seo_title=data["seo_title"][:60],
            slug_url=data["slug_url"],
            seo_keywords=_limit_pipe_list(data.get("seo_keywords", ""), 15),
            seo_description=data["seo_description"][:250],
            search_keywords=_limit_pipe_list(data.get("search_keywords", ""), 20),
            logo_image_url=logo_image_url,
            cover_image_url=cover_image_url,
            photo_gallery_urls=gallery[:20],
            confidence_notes=data.get("confidence_notes"),
        )

    except json.JSONDecodeError as e:
        logger.error(f"GPT invalid JSON: {e}")
        return None
    except KeyError as e:
        logger.error(f"Missing GPT field: {e}")
        return None
    except Exception as e:
        logger.error(f"Enrichment error: {e}")
        return None


def _limit_pipe_list(value: str, max_items: int) -> str:
    """Trim a '||'-separated keyword string down to max_items entries."""
    if not value:
        return ""
    items = [v.strip() for v in value.split("||") if v.strip()]
    return " || ".join(items[:max_items])