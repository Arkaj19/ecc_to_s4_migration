"""
Schemas for fico/api/credit_router.py.

`/process-credit` streams a file, so it isn't wired up as a
`response_model`. `/validate-credit` (quick mandatory-field check) and
`/validate-credit-reconciliation` (full ECC vs S/4 reconciliation report)
both return JSON and reuse the shared shapes from common_schemas.py.
"""

from pydantic import BaseModel

from .common_schemas import FieldValidationResponse, ReconciliationValidationResponse


# ============================================================
# POST /process-credit
# ============================================================

class ProcessCreditRequest(BaseModel):
    """
    Documents the multipart form field accepted by `/process-credit`.
    Not used as a FastAPI dependency directly -- the route takes an
    `UploadFile` so it can stream the upload.
    """
    file: str  # Excel (.xlsx/.xls) upload, field name "file"


# ============================================================
# POST /validate-credit
# ============================================================

class CreditFieldValidationResponse(FieldValidationResponse):
    """Response body for `/validate-credit` (mandatory-field check only)."""
    pass


# ============================================================
# POST /validate-credit-reconciliation
# ============================================================

class CreditValidationResponse(ReconciliationValidationResponse):
    """Response body for `/validate-credit-reconciliation`."""
    process: str = "CREDIT"
