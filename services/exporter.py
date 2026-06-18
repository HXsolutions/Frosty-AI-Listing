import csv
import io
import logging
from services.sheets import get_approved_rows, EXPORT_HEADERS, EXPORT_COL_COUNT

logger = logging.getLogger(__name__)


async def generate_csv() -> str:
    """
    Fetch approved listings from Google Sheets.
    Strip internal tracking columns (Confidence Score, Flags, Review Status, Generated At).
    Return CSV string ready for import into eDirectory.
    """
    rows = await get_approved_rows()

    if not rows or len(rows) < 2:
        return ""

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(EXPORT_HEADERS)

    for row in rows[1:]:   # skip header row
        export_row = row[:EXPORT_COL_COUNT]
        while len(export_row) < EXPORT_COL_COUNT:
            export_row.append("")
        writer.writerow(export_row)

    return out.getvalue()
