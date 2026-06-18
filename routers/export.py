import io
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from services.exporter import generate_csv
from services.sheets import get_stats, get_categories

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/csv")
async def export_csv():
    """Download all approved listings as eDirectory-compatible CSV."""
    csv_content = await generate_csv()
    if not csv_content:
        return JSONResponse(
            status_code=404,
            content={"message": "No approved listings to export yet."}
        )
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=frosty_connections_listings.csv"
        }
    )


@router.get("/stats")
async def get_listing_stats():
    """Return listing counts — used by the admin dashboard."""
    return await get_stats()


@router.get("/categories")
async def list_categories():
    """Return the current category list (editable via Google Sheets)."""
    categories = await get_categories()
    return {"categories": categories, "count": len(categories)}
