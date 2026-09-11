"""
Schemas for fico/api/ar_router.py.

Mirrors ap_schemas.py -- `/process-ar` streams a file (or, on a currency
mismatch, a JSON review payload), while `/validate-ar` returns the full
reconciliation report as JSON.
"""

from typing import Optional

from pydantic import BaseModel

from .common_schemas import CurrencyMismatchRow, CurrencyReviewResponse, ReconciliationValidationResponse


# ============================================================
# POST /process-ar
# ============================================================

class ProcessARRequest(BaseModel):
    """
    Documents the multipart form fields accepted by `/process-ar`.
    Not used as a FastAPI dependency directly -- see ProcessAPRequest
    for why.
    """
    file: str  # Excel (.xlsx/.xls) upload, field name "file"
    currency_action: Optional[str] = None  # "KEEP" | "DELETE"


class ARCurrencyMismatchRow(CurrencyMismatchRow):
    """AR mismatch rows always carry `customer` (no `supplier`/`reference`)."""
    customer: Optional[str] = None


class ARCurrencyReviewResponse(CurrencyReviewResponse):
    """
    Body returned by `/process-ar` (in place of the Excel file) when the
    registry has company-code / currency mismatches and no
    `currency_action` was supplied yet.
    """
    mismatches: list[ARCurrencyMismatchRow] = []


# ============================================================
# POST /validate-ar
# ============================================================

class ARValidationResponse(ReconciliationValidationResponse):
    """Response body for `/validate-ar`."""
    process: str = "AR"
