from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ListingStatus(str, Enum):
    approved = "approved"
    needs_review = "needs_review"


class ListingInput(BaseModel):
    business_name: Optional[str] = Field(None, max_length=300)
    url: Optional[str] = Field(None, max_length=2000)


class SocialLinks(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    x: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None


class Listing(BaseModel):
    # --- Basic Information ---
    listing_title: str
    summary_description: str            # max 250 chars
    description: str                    # long, formatted (HTML allowed)

    # --- Categories ---
    category_1: Optional[str] = None
    category_2: Optional[str] = None
    category_3: Optional[str] = None
    category_4: Optional[str] = None
    category_5: Optional[str] = None

    # --- Membership / Billing (fixed defaults — not AI decided) ---
    product: str = "N-P Free"
    listing_template: str = "IP-Core"
    status: str = "Active"
    renewal_date: Optional[str] = None  # auto-set, 1 year from generation

    # --- Contact Information ---
    email: Optional[str] = None
    url: Optional[str] = None
    phone: Optional[str] = None
    additional_phone: Optional[str] = None
    additional_phone_label: Optional[str] = None
    address: Optional[str] = None
    address2: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    reference: Optional[str] = None     # map reference — minimum state-level location
    map_reference: Optional[str] = None  # alias kept for clarity in enricher

    # --- Social Networks ---
    social_links: SocialLinks = SocialLinks()

    # --- SEO Block ---
    seo_title: str
    slug_url: str
    seo_keywords: str                   # pipe separated, max 15: kw1 || kw2
    seo_description: str                # max 250 chars

    # --- Search Keywords (separate from SEO keywords) ---
    search_keywords: str                # pipe separated, max 20: kw1 || kw2

    # --- Images (URLs scraped from business website) ---
    logo_image_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    photo_gallery_urls: list[str] = []

    # --- Confidence Notes (Verified / Inferred / Missing) ---
    confidence_notes: Optional[str] = None

    # --- Fields intentionally left for Pothga to manage manually ---
    # account: "No Owner" (default — listing stays unclaimed)
    # total_allowed_leads: not set by AI
    # disable_claim_feature: not set by AI (defaults to enabled)
    # listing_badges: Legacy Member / Founding Partner / Partner / Veteran — manual only

    # --- Internal tracking (not exported to CSV) ---
    confidence_score: float = 0.0
    review_status: ListingStatus = ListingStatus.needs_review
    flags: list[str] = []


class ListingResponse(BaseModel):
    success: bool
    listing: Optional[Listing] = None
    error: Optional[str] = None
    message: Optional[str] = None
