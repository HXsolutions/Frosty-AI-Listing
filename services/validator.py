import re
import logging
from models.listing import Listing, ListingStatus
from config import settings

logger = logging.getLogger(__name__)


def validate_listing(listing: Listing, scraped: dict, categories: list[str]) -> Listing:
    flags = []
    score = 1.0
    raw = (scraped.get("markdown", "") + str(scraped.get("extracted", {}))).lower()

    # --- Phone ---
    if listing.phone:
        digits = re.sub(r"\D", "", listing.phone)
        if len(digits) < 7:
            flags.append("Phone number format looks invalid")
            score -= 0.1
        if digits and digits not in re.sub(r"\D", "", raw):
            flags.append("Phone not found in scraped content — may be hallucinated")
            score -= 0.2

    # --- Email ---
    if listing.email:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", listing.email):
            flags.append("Email format invalid")
            score -= 0.1
        if listing.email.lower() not in raw:
            flags.append("Email not found in scraped content — may be hallucinated")
            score -= 0.15

    # --- Address ---
    if listing.address:
        words = listing.address.lower().split()
        matches = sum(1 for w in words if len(w) > 3 and w in raw)
        if len(words) > 2 and matches < 1:
            flags.append("Address not confirmed in scraped content")
            score -= 0.15

    # --- Required fields ---
    if not listing.listing_title:
        flags.append("Missing listing title")
        score -= 0.3
    if not listing.summary_description:
        flags.append("Missing summary description")
        score -= 0.2
    if not listing.description:
        flags.append("Missing description")
        score -= 0.2
    if not listing.search_keywords:
        flags.append("No search keywords assigned")
        score -= 0.1
    if not listing.seo_keywords:
        flags.append("No SEO keywords assigned")
        score -= 0.05

    # --- Categories (1-5) ---
    if not listing.category_1:
        flags.append("No primary category assigned")
        score -= 0.15
    elif listing.category_1 not in categories:
        flags.append(f"Category '{listing.category_1}' not in approved category list")
        score -= 0.15

    for field_name in ["category_2", "category_3", "category_4", "category_5"]:
        val = getattr(listing, field_name)
        if val and val not in categories:
            flags.append(f"Category '{val}' not in approved category list — removed")
            setattr(listing, field_name, None)

    # --- Images ---
    if not listing.logo_image_url and not listing.cover_image_url and not listing.photo_gallery_urls:
        flags.append("No images found on business website")
        score -= 0.05

    # --- Length checks (auto-truncate) ---
    if len(listing.summary_description) > 250:
        flags.append("Summary description exceeds 250 chars — truncated")
        listing.summary_description = listing.summary_description[:250]
    if len(listing.seo_description) > 250:
        flags.append("SEO description exceeds 250 chars — truncated")
        listing.seo_description = listing.seo_description[:250]
    if len(listing.seo_title) > 60:
        flags.append("SEO title exceeds 60 chars — truncated")
        listing.seo_title = listing.seo_title[:60]

    # --- Keyword count checks ---
    seo_kw_count = len([k for k in listing.seo_keywords.split("||") if k.strip()])
    if seo_kw_count > 15:
        flags.append("SEO keywords exceed 15 — truncated")

    search_kw_count = len([k for k in listing.search_keywords.split("||") if k.strip()])
    if search_kw_count > 20:
        flags.append("Search keywords exceed 20 — truncated")

    score = max(0.0, min(1.0, round(score, 2)))
    hallucinated = any("hallucinated" in f for f in flags)

    listing.confidence_score = score
    listing.flags = flags
    listing.review_status = (
        ListingStatus.approved
        if score >= settings.confidence_threshold and not hallucinated
        else ListingStatus.needs_review
    )

    return listing
