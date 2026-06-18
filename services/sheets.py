import logging
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from models.listing import Listing, ListingStatus
from config import settings
import json

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Tab names
TAB_APPROVED   = "Approved"
TAB_REVIEW     = "Review Queue"
TAB_ALL        = "All Listings"
TAB_CATEGORIES = "Categories"

# eDirectory-aligned export columns (matches Add Listing form layout)
EXPORT_HEADERS = [
    "Listing Title", "Summary Description", "Description",
    "Category 1", "Category 2", "Category 3", "Category 4", "Category 5",
    "Product", "Listing Template", "Status", "Renewal Date",
    "E-mail", "URL", "Phone", "Additional Phone", "Additional Phone Label",
    "Address", "Address2", "Zip Code", "Country", "Reference",
    "Facebook", "Instagram", "X", "LinkedIn", "YouTube",
    "SEO Title", "Slug URL", "SEO Keywords", "SEO Description", "Search Keywords",
    "Logo Image URL", "Cover Image URL", "Photo Gallery URLs",
    "Map Reference", "Confidence Notes",
]

EXPORT_COL_COUNT = len(EXPORT_HEADERS)

INTERNAL_HEADERS = ["Confidence Score", "Flags", "Review Status", "Generated At"]
ALL_HEADERS = EXPORT_HEADERS + INTERNAL_HEADERS

DEFAULT_CATEGORIES = [
    "Industrial Refrigeration->Contractors & Installers",
    "Industrial Refrigeration->Equipment & Components",
    "Industrial Refrigeration->Consulting & Engineering",
    "Industrial Refrigeration->Safety & Compliance",
    "Industrial Refrigeration->Distributors & Suppliers",
    "Industrial Refrigeration->Software & Controls",
    "Training & Education->Certification Programs",
    "Training & Education->Technical Schools",
    "Training & Education->Apprenticeship Programs",
    "Organizations->Industry Associations",
    "Organizations->Standards Bodies",
    "Safety & Compliance->OSHA Resources",
    "Safety & Compliance->EPA Compliance",
    "Safety & Compliance->PSM & RMP Guidance",
    "Research & Development->Labs & Universities",
]


def _get_client():
    service_account_info = json.loads(
        settings.google_service_account_json
    )

    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )

    return gspread.authorize(creds)



def _ensure_tabs(spreadsheet):
    existing = [ws.title for ws in spreadsheet.worksheets()]

    for tab in [TAB_APPROVED, TAB_REVIEW, TAB_ALL]:
        if tab not in existing:
            ws = spreadsheet.add_worksheet(title=tab, rows=2000, cols=len(ALL_HEADERS) + 5)
            ws.append_row(ALL_HEADERS)
            ws.freeze(rows=1)
            logger.info(f"Created tab: {tab}")

    if TAB_CATEGORIES not in existing:
        ws = spreadsheet.add_worksheet(title=TAB_CATEGORIES, rows=200, cols=1)
        ws.append_row(["Category (Parent->Child format)"])
        ws.append_rows([[c] for c in DEFAULT_CATEGORIES])
        ws.freeze(rows=1)
        logger.info(f"Created tab: {TAB_CATEGORIES} with default categories")


def _listing_to_row(listing: Listing) -> list:
    s = listing.social_links
    return [
        listing.listing_title or "",
        listing.summary_description or "",
        listing.description or "",
        listing.category_1 or "",
        listing.category_2 or "",
        listing.category_3 or "",
        listing.category_4 or "",
        listing.category_5 or "",
        listing.product or "N-P Free",
        listing.listing_template or "IP-Core",
        listing.status or "Active",
        listing.renewal_date or "",
        listing.email or "",
        listing.url or "",
        listing.phone or "",
        listing.additional_phone or "",
        listing.additional_phone_label or "",
        listing.address or "",
        listing.address2 or "",
        listing.zip_code or "",
        listing.country or "",
        listing.reference or "",
        s.facebook or "",
        s.instagram or "",
        s.x or "",
        s.linkedin or "",
        s.youtube or "",
        listing.seo_title or "",
        listing.slug_url or "",
        listing.seo_keywords or "",
        listing.seo_description or "",
        listing.search_keywords or "",
        listing.logo_image_url or "",
        listing.cover_image_url or "",
        " || ".join(listing.photo_gallery_urls) if listing.photo_gallery_urls else "",
        listing.map_reference or listing.reference or "",
        listing.confidence_notes or "",
        # Internal
        str(listing.confidence_score),
        " | ".join(listing.flags) if listing.flags else "",
        listing.review_status.value,
        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    ]


async def save_listing(listing: Listing) -> bool:
    """
    Save listing to:
    - All Listings tab (always)
    - Approved tab (if approved)
    - Review Queue tab (if needs review)
    """
    try:
        gc = _get_client()
        ss = gc.open_by_key(settings.google_sheet_id)
        _ensure_tabs(ss)
        row = _listing_to_row(listing)

        ss.worksheet(TAB_ALL).append_row(row)

        if listing.review_status == ListingStatus.approved:
            ss.worksheet(TAB_APPROVED).append_row(row)
            logger.info(f"'{listing.listing_title}' → Approved")
        else:
            ss.worksheet(TAB_REVIEW).append_row(row)
            logger.info(f"'{listing.listing_title}' → Review Queue (score: {listing.confidence_score})")

        return True

    except Exception as e:
        logger.error(f"Sheets save error: {e}")
        return False


async def get_approved_rows() -> list[list]:
    try:
        gc = _get_client()
        ss = gc.open_by_key(settings.google_sheet_id)
        ws = ss.worksheet(TAB_APPROVED)
        return ws.get_all_values()
    except Exception as e:
        logger.error(f"Sheets fetch error: {e}")
        return []


async def get_categories() -> list[str]:
    try:
        gc = _get_client()
        ss = gc.open_by_key(settings.google_sheet_id)
        _ensure_tabs(ss)
        ws = ss.worksheet(TAB_CATEGORIES)
        rows = ws.get_all_values()
        categories = [row[0].strip() for row in rows[1:] if row and row[0].strip()]
        if not categories:
            logger.warning("Categories tab is empty — using defaults")
            return DEFAULT_CATEGORIES
        return categories
    except Exception as e:
        logger.error(f"Error fetching categories: {e} — using defaults")
        return DEFAULT_CATEGORIES


async def get_stats() -> dict:
    try:
        gc = _get_client()
        ss = gc.open_by_key(settings.google_sheet_id)
        _ensure_tabs(ss)

        def count(tab):
            rows = ss.worksheet(tab).get_all_values()
            return max(0, len(rows) - 1)

        return {
            "total": count(TAB_ALL),
            "approved": count(TAB_APPROVED),
            "needs_review": count(TAB_REVIEW),
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total": 0, "approved": 0, "needs_review": 0}
