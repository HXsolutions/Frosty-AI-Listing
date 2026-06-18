import logging
from fastapi import APIRouter, HTTPException
from models.listing import ListingInput, ListingResponse
from services.scraper import scrape_url, search_business
from services.enricher import enrich_listing
from services.validator import validate_listing
from services.sheets import save_listing, get_categories

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/listings", tags=["Listings"])


@router.post("/generate", response_model=ListingResponse)
async def generate_listing(data: ListingInput):
    """
    Main pipeline:
    Input → Scrape (incl. images) → AI Enrich → Validate → Save to Google Sheets
    """
    url = data.url
    name = data.business_name or ""

    if not url and not name:
        raise HTTPException(status_code=400, detail="Provide business_name or url")

    # Step 1 — resolve URL if only name given
    if not url:
        logger.info(f"Searching URL for: {name}")
        url = await search_business(name)
        if not url:
            return ListingResponse(
                success=False,
                error=f"Could not find a website for '{name}'. Please provide the URL directly."
            )

    # Step 2 — scrape (content + images)
    logger.info(f"Scraping: {url}")
    scraped = await scrape_url(url)
    if not scraped:
        return ListingResponse(
            success=False,
            error=f"Could not scrape {url}. The site may be blocking automated access."
        )

    if not name:
        name = scraped.get("extracted", {}).get("company_name", "")

    # Step 3 — fetch current categories (Pothga-editable in Google Sheets)
    categories = await get_categories()

    # Step 4 — AI enrichment
    logger.info(f"Enriching: {name}")
    listing = await enrich_listing(name, url, scraped, categories)
    if not listing:
        return ListingResponse(success=False, error="AI enrichment failed. Please try again.")

    # Step 5 — validate + score
    listing = validate_listing(listing, scraped, categories)
    logger.info(f"Score: {listing.confidence_score} | Status: {listing.review_status}")

    # Step 6 — save to Google Sheets
    await save_listing(listing)

    msg = (
        "Listing approved and saved to Google Sheets."
        if listing.review_status.value == "approved"
        else f"Saved to Review Queue. Flags: {', '.join(listing.flags)}"
    )

    return ListingResponse(success=True, listing=listing, message=msg)
