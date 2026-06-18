import httpx
import logging
from typing import Optional
from urllib.parse import urlparse
from config import settings

logger = logging.getLogger(__name__)
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"

# Blocked URL patterns — prevent SSRF attacks
BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0",
    "169.254.169.254",   # AWS metadata
    "metadata.google.internal",  # GCP metadata
    "10.", "172.16.", "192.168.",  # Private ranges
}


def _is_safe_url(url: str) -> bool:
    """Block internal/private URLs to prevent SSRF attacks."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if not host:
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        for blocked in BLOCKED_HOSTS:
            if host == blocked or host.startswith(blocked):
                return False
        return True
    except Exception:
        return False


async def scrape_url(url: str) -> Optional[dict]:
    """
    Scrape a URL using Firecrawl.
    Returns markdown content, structured extraction, and discovered images.
    """
    if not _is_safe_url(url):
        logger.warning(f"Blocked unsafe URL: {url}")
        return None

    headers = {
        "Authorization": f"Bearer {settings.firecrawl_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "url": url,
        "formats": ["markdown", "extract"],
        "extract": {
            "schema": {
                "type": "object",
                "properties": {
                    "company_name":      {"type": "string"},
                    "phone":             {"type": "string"},
                    "additional_phone":  {"type": "string"},
                    "email":             {"type": "string"},
                    "address":           {"type": "string"},
                    "address2":          {"type": "string"},
                    "city":              {"type": "string"},
                    "state":             {"type": "string"},
                    "zip_code":          {"type": "string"},
                    "country":           {"type": "string"},
                    "description":       {"type": "string"},
                    "services":          {"type": "array", "items": {"type": "string"}},
                    "facebook":          {"type": "string"},
                    "instagram":         {"type": "string"},
                    "x_twitter":         {"type": "string"},
                    "linkedin":          {"type": "string"},
                    "youtube":           {"type": "string"},
                    "logo_image_url":    {"type": "string"},
                    "cover_image_url":   {"type": "string"},
                    "gallery_image_urls":{"type": "array", "items": {"type": "string"}},
                    "landmark_reference":{"type": "string"},
                },
            }
        },
        "onlyMainContent": False,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{FIRECRAWL_BASE}/scrape", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            if not data.get("success"):
                logger.warning(f"Firecrawl success=false for {url}")
                return None
            return {
                "markdown":  data.get("data", {}).get("markdown", ""),
                "extracted": data.get("data", {}).get("extract", {}),
                "metadata":  data.get("data", {}).get("metadata", {}),
            }
    except httpx.HTTPStatusError as e:
        logger.error(f"Firecrawl HTTP {e.response.status_code} for {url}")
        return None
    except Exception as e:
        logger.error(f"Firecrawl error for {url}: {e}")
        return None


async def search_business(business_name: str) -> Optional[str]:
    """Find a business URL from just a name using Firecrawl search."""
    # Sanitize input
    name = business_name.strip()[:200]
    if not name:
        return None

    headers = {
        "Authorization": f"Bearer {settings.firecrawl_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f"{FIRECRAWL_BASE}/search",
                headers=headers,
                json={"query": f"{name} official website industrial refrigeration", "limit": 3},
            )
            r.raise_for_status()
            results = r.json().get("data", [])
            for result in results:
                found_url = result.get("url", "")
                if _is_safe_url(found_url):
                    return found_url
            return None
    except Exception as e:
        logger.error(f"Firecrawl search error for '{name}': {e}")
        return None
