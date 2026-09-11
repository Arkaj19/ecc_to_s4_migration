"""
Schemas for fico/api/ap_router.py.

`/process-ap` and the download endpoints move binary Excel/PDF data, so
they're documented here but not wired up as `response_model` (FastAPI's
response_model validation doesn't apply to a StreamingResponse/FileResponse
body). The one JSON body `/process-ap` can return -- the currency review
payload raised via CurrencyReviewRequiredError -- gets its own model so
that payload is validated before it goes back to the caller.
"""

from typing import Optional

from pydantic import BaseModel

from .common_schemas import CurrencyMismatchRow, CurrencyReviewResponse, ReconciliationValidationResponse


# ============================================================
# POST /process-ap
# ============================================================

class ProcessAPRequest(BaseModel):
    """
    Documents the multipart form fields accepted by `/process-ap`.
    Not used as a FastAPI dependency directly (the route takes
    `UploadFile`/`Form` params so it can stream the upload), but keeps
    the expected shape in one place.
    """
    file: str  # Excel (.xlsx/.xls) upload, field name "file"
    currency_action: Optional[str] = None  # "KEEP" | "DELETE"


class APCurrencyMismatchRow(CurrencyMismatchRow):
    """AP mismatch rows always carry `supplier` and `reference`."""
    supplier: Optional[str] = None
    reference: Optional[str] = None


class APCurrencyReviewResponse(CurrencyReviewResponse):
    """
    Body returned by `/process-ap` (in place of the Excel file) when the
    registry has company-code / currency mismatches and no
    `currency_action` was supplied yet.
    """
    mismatches: list[APCurrencyMismatchRow] = []


# ============================================================
# POST /validate-ap-reconciliation
# ============================================================

class APValidationResponse(ReconciliationValidationResponse):
    """Response body for `/validate-ap-reconciliation`."""
    process: str = "AP"
