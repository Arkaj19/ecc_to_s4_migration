"""
Shared request/response schemas for the fico module.

Mirrors the layered pattern used by INVENTORY/schemas/inventory_schemas.py:
each API sub-folder gets its own schema file, but the four fico
validators (ap_validator.py, ar_validator.py, credit_validator.py) and
the asset/credit "quick validate" endpoints all build their JSON payloads
from the exact same handful of shapes. Those shared shapes live here so
ap_schemas.py / ar_schemas.py / asset_schemas.py / credit_schemas.py can
import and reuse them instead of redefining the same fields four times.

Design notes
------------
Every reconciliation check (see ar_validator.py's module docstring) and
every one of its detail rows carries a handful of check-specific "extra"
fields on top of the common shape (e.g. `prefix`, `groups`,
`ecc_total_count`). Rather than trying to enumerate every possible extra
field for every check, these models declare the fields that are always
present and allow additional ones through via `Config.extra = "allow"`.
That keeps the schema honest about what's guaranteed to exist while
still passing through the check-specific extras untouched.
"""

from typing import List, Optional

from pydantic import BaseModel


# ============================================================
# Reconciliation validation (AP / AR / Credit "*-reconciliation" style)
# ============================================================
# Shape produced by ar_validator.validate_ar_files / ap_validator.validate_ap_files
# / credit_validator.validate_credit_files, as documented in their module
# docstrings.
# ============================================================

class ValidationDetail(BaseModel):
    """One row of a check's `details` list."""
    label: str
    left_count: Optional[float] = None   # ECC side
    right_count: Optional[float] = None  # S/4 side
    status: str                          # "PASS" | "FAIL" | "MAPPING_ERROR"
    message: str
    money: Optional[bool] = None         # present only when True

    class Config:
        extra = "allow"  # e.g. "prefix" on the payment-terms-group check


class ValidationCheck(BaseModel):
    """One entry of the top-level `checks` list."""
    check_name: str
    status: str  # "PASS" | "FAIL"
    message: str
    details: List[ValidationDetail] = []

    class Config:
        extra = "allow"  # e.g. "ecc_total_count", "difference", "groups"


class ValidationSummary(BaseModel):
    total_checks: int
    passed: int
    failed: int


class ReconciliationValidationResponse(BaseModel):
    """
    Response body for the `/validate-*-reconciliation` (and `/validate-ar`)
    endpoints: the raw result of `validate_*_files()` plus the
    `report_available` / `report_file` fields the router adds once the
    PDF has been generated.
    """
    process: str  # "AP" | "AR" | "CREDIT"
    overall_status: str  # "PASS" | "FAIL"
    summary: ValidationSummary
    checks: List[ValidationCheck]
    report_available: Optional[bool] = None
    report_file: Optional[str] = None
    report_download_id: Optional[str] = None


# ============================================================
# "Quick" mandatory-field validation (Asset / Credit "/validate-*")
# ============================================================
# Shape built directly in asset_router.validate_asset / credit_router.validate_credit
# from the raw `validation_errors` list returned by the processor.
# ============================================================

class FieldValidationError(BaseModel):
    sheet: str
    column: str
    missing_rows: int
    message: str


class FieldValidationResponse(BaseModel):
    valid: bool
    errors: List[FieldValidationError] = []


# ============================================================
# Currency review (AP / AR "/process-*" currency_action flow)
# ============================================================
# Shape raised via CurrencyReviewRequiredError.review_payload and later
# attached to the output buffer as `out_buf.currency_review` once a
# currency_action has been supplied. Fields that only exist on one side
# (e.g. "supplier" on AP vs "customer" on AR) are optional here so the
# same model covers both.
# ============================================================

class CurrencyMismatchRow(BaseModel):
    row: int
    company_code: Optional[str] = None
    s4_company_code: Optional[str] = None
    currency: Optional[str] = None
    supplier: Optional[str] = None          # AP only
    expected_currency: Optional[str] = None   # AR only
    customer: Optional[str] = None          # AR only
    reference: Optional[str] = None         # AP only
    document_number: Optional[str] = None
    amount: Optional[float] = None


class CurrencyReviewResponse(BaseModel):
    """
    Returned as-is (no file) when a registry has company-code / currency
    mismatches and no `currency_action` was supplied yet.
    """
    status: str  # "review_required"
    action: Optional[str] = None
    mismatch_count: int
    mismatches: List[CurrencyMismatchRow] = []
    dump_rows: Optional[int] = None
    retained_rows: Optional[int] = None


# ============================================================
# Generic row-level validation error
# ============================================================
# Shape appended to `validation_errors` by ap_processor / ar_processor /
# asset_processor / credit_processor while filling the template. The
# exact extra keys differ per processor (see each processor's
# `validation_errors.append(...)` calls), so only the fields common to
# every processor are declared and the rest pass through.
# ============================================================

class RowValidationError(BaseModel):
    sheet: str
    field_label: str

    class Config:
        extra = "allow"  # e.g. "field", "source_row"/"row", "asset", "vendor", ...
