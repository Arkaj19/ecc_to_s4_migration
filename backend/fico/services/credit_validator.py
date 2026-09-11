"""
Credit migration validator.

Compares an ECC Credit registry against a filled-in S/4 "Profile -
Credit MD for Cust." template and runs a fixed set of reconciliation
checks between them.

This mirrors ap_validator.py's architecture exactly -- same result
shape, same helper functions, same one-function-per-check pattern --
so all three validators (and their frontends) behave identically. Only
the Credit-specific field names and sheet layout differ.

Design notes
------------
Every check returns a dict of the shape::

    {
        "check_name": str,
        "status": "PASS" | "FAIL",
        "message": str,
        "details": [ <detail>, ... ],   # may be empty
        ... check-specific extra fields ...
    }

and every entry in ``details`` shares one schema::

    {
        "label": str,
        "left_count": number | None,   # ECC side
        "right_count": number | None,  # S/4 side
        "status": "PASS" | "FAIL" | "MAPPING_ERROR",
        "message": str,
        ... detail-specific extra fields ...
    }

Adding a 3rd check means writing one ``validate_*`` function with this
shape and adding it to ``CHECK_FUNCTIONS`` below -- nothing else changes.
"""

from typing import Any, Callable, Dict, Iterable, List, Optional

import pandas as pd
import openpyxl

from backend.fico.utils.format_utils import clean_string
# NOTE: normalize_credit_rep_group() below is still duplicated verbatim
# from credit_processor.py (confirmed identical) -- same pattern as the
# clean_* functions, just Credit-specific rather than generic, so it's
# a candidate for a small backend/fico/services/credit_common.py (not
# utils/format_utils.py, since it has SAP Credit domain meaning) as a
# follow-up.


# ============================================================
# Credit Validation Configuration
# ============================================================

S4_START_ROW = 9

S4_PROFILE_SHEET_NAME = "Profile - Credit MD for Cust."

# The four known Credit Rep Group codes. Anything else that shows up
# (either side) still gets its own dynamically-discovered group -- this
# list only controls the highlighted-blank label below.
BLANK_CREDIT_GROUP_LABEL = "(blank)"


# ============================================================
# Utility Functions
# ============================================================

def normalize_credit_rep_group(raw_value: Any) -> str:
    """
    Mirrors credit_processor.py's normalize_credit_rep_group() exactly.

    The Credit Rep Group is a 2-digit code with a leading zero
    ('01', '02', ...). If the registry stores it as a plain number
    rather than text, pandas reads it back as an int/float and the
    leading zero is lost -- this restores it so the expected value
    matches what the processor actually wrote to CREDIT_GROUP.
    Non-numeric values are passed through as a plain string unchanged.
    Blank/NaN values become "" -- reported under BLANK_CREDIT_GROUP_LABEL.
    """
    if pd.isna(raw_value) or raw_value is None:
        return ""
    try:
        return str(int(float(raw_value))).zfill(2)
    except (ValueError, TypeError):
        return str(raw_value).strip()


def is_non_empty(value: Any) -> bool:
    """Returns True when an Excel cell contains an actual value."""
    if value is None:
        return False

    if isinstance(value, str):
        return value.strip() != ""

    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass

    return True


# ============================================================
# Result-Building Helpers
# ============================================================

def pass_fail(is_match: bool) -> str:
    """Map a boolean match into the "PASS" / "FAIL" status string."""
    return "PASS" if is_match else "FAIL"


def make_detail(
    label: str,
    left_count: Optional[float],
    right_count: Optional[float],
    message: str,
    status: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """
    Build one row of a check's `details` list.

    `status` defaults to a straight left == right comparison; pass it
    explicitly for cases that need other logic (e.g. a missing mapping).
    """
    if status is None:
        status = pass_fail(left_count == right_count)

    detail: Dict[str, Any] = {
        "label": label,
        "left_count": left_count,
        "right_count": right_count,
        "status": status,
        "message": message,
    }

    detail.update(extra)
    return detail


def make_check(
    check_name: str,
    details: List[Dict[str, Any]],
    passing_message: str,
    failing_message: str,
    **extra: Any,
) -> Dict[str, Any]:
    """
    Build a check's top-level result from its already-built `details`.

    Overall status is PASS only when every detail row is PASS.
    """
    overall_pass = all(detail["status"] == "PASS" for detail in details)

    check: Dict[str, Any] = {
        "check_name": check_name,
        "status": pass_fail(overall_pass),
        "details": details,
        "message": passing_message if overall_pass else failing_message,
    }
    check.update(extra)
    return check


def missing_column_check(check_name: str, source_label: str, column: str) -> Dict[str, Any]:
    """Short-circuit result for a check whose required column is absent."""
    return {
        "check_name": check_name,
        "status": "FAIL",
        "details": [],
        "message": f'{source_label} does not contain a "{column}" column.',
    }


def first_missing_column(df: pd.DataFrame, columns: Iterable[str]) -> Optional[str]:
    """Return the first of `columns` not present in `df`, or None."""
    for column in columns:
        if column not in df.columns:
            return column
    return None


# ============================================================
# Excel Reading
# ============================================================

def read_ecc_registry(registry_file) -> pd.DataFrame:
    """
    Read the ECC Credit registry.

    Row 1 is the header row; records begin from row 2. Rows with a
    blank CustomerNumber are dropped here -- process_credit_registry()
    in credit_processor.py skips those rows too (`if not
    raw_customer_number: continue`), so excluding them here keeps the
    ECC-side counts aligned with what actually made it into the S/4
    file, rather than over-counting rows the processor never wrote.
    """

    df = pd.read_excel(
        registry_file,
        header=0,
    )

    df = df.dropna(how="all")

    if "CustomerNumber" in df.columns:
        df = df[df["CustomerNumber"].apply(clean_string) != ""].copy()

    return df


def read_s4_credit_profile(filled_file) -> pd.DataFrame:
    """
    Read the S/4 "Profile - Credit MD for Cust." sheet.

    S/4 template structure:
        Row 5 = technical field names (KUNNR, RUN_ID, CREDIT_GROUP, etc.)
        Row 8 = human-readable field descriptions
        Row 9 onward = actual records

    The validator uses the technical field names so that validations
    can consistently refer to fields such as KUNNR and CREDIT_GROUP.
    """

    wb = openpyxl.load_workbook(
        filled_file,
        read_only=True,
        data_only=True,
    )

    if S4_PROFILE_SHEET_NAME not in wb.sheetnames:
        raise ValueError(
            f'S/4 file does not contain the required sheet '
            f'"{S4_PROFILE_SHEET_NAME}".'
        )

    ws = wb[S4_PROFILE_SHEET_NAME]

    # ------------------------------------------------------------
    # Row 5 contains the technical field names:
    # KUNNR, RUN_ID, RISK_CLASS, CREDIT_GROUP, etc.
    # ------------------------------------------------------------
    technical_headers = [
        clean_string(cell.value)
        for cell in ws[5]
    ]

    # ------------------------------------------------------------
    # Read actual data beginning from row 9.
    # ------------------------------------------------------------
    records = []

    for row in ws.iter_rows(
        min_row=S4_START_ROW,
        values_only=True,
    ):
        if not any(is_non_empty(value) for value in row):
            continue

        record = {}

        for index, value in enumerate(row):
            if index < len(technical_headers):
                technical_field = technical_headers[index]

                if technical_field:
                    record[technical_field] = value

        records.append(record)

    wb.close()

    return pd.DataFrame(records)


# ============================================================
# Validation 1
# Credit Rep Group Distribution (New Credit Rep Group -> CREDIT_GROUP)
# ============================================================

def validate_credit_rep_group_counts(ecc_df: pd.DataFrame, s4_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compare, per normalized Credit Rep Group code, how many ECC rows
    carry that code against how many S/4 rows have a matching
    CREDIT_GROUP.

    The ECC side is normalized through the exact same
    normalize_credit_rep_group() logic credit_processor.py uses to
    build CREDIT_GROUP, so a "2.0" in the registry and a "02" in the
    filled file are correctly treated as the same group. Blank/NaN
    values on either side are grouped together under
    BLANK_CREDIT_GROUP_LABEL rather than excluded, since a blank
    Credit Rep Group is itself a value the processor deliberately
    writes through (CREDIT_GROUP = "").
    """

    missing = first_missing_column(ecc_df, ["New Credit Rep Group"])
    if missing:
        return missing_column_check("Credit Rep Group Distribution", "ECC registry", missing)

    missing = first_missing_column(s4_df, ["CREDIT_GROUP"])
    if missing:
        return missing_column_check("Credit Rep Group Distribution", "S/4 file", missing)

    ecc_groups = ecc_df["New Credit Rep Group"].apply(normalize_credit_rep_group)
    s4_groups = s4_df["CREDIT_GROUP"].apply(clean_string)

    # Discover every distinct group from either side, so a code that
    # only appears in one file still gets its own row instead of being
    # silently dropped.
    distinct_groups = sorted(
        set(ecc_groups.unique()) | set(s4_groups.unique()),
        key=lambda g: (g == "", g),
    )

    details = []

    for group in distinct_groups:
        label = BLANK_CREDIT_GROUP_LABEL if group == "" else group

        ecc_count = int((ecc_groups == group).sum())
        s4_count = int((s4_groups == group).sum())

        details.append(make_detail(
            label=label,
            left_count=ecc_count,
            right_count=s4_count,
            message=(
                "Credit Rep Group count matches."
                if ecc_count == s4_count
                else f"Credit Rep Group count mismatch: ECC={ecc_count}, S/4={s4_count}."
            ),
            credit_group=group,
        ))

    return make_check(
        check_name="Credit Rep Group Distribution",
        details=details,
        passing_message="All Credit Rep Group counts match.",
        failing_message="One or more Credit Rep Group counts do not match.",
    )


# ============================================================
# Validation 2
# Company Code Distribution (via KUNNR -> ECC CustomerNumber -> Company Code)
# ============================================================

def validate_company_code_counts(ecc_df: pd.DataFrame, s4_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compare, per Company Code, how many ECC rows belong to that
    company code against how many S/4 rows resolve to it.

    Unlike AP/AR, the Credit S/4 output never writes a company code of
    its own -- KUNNR in the filled file is the raw registry
    CustomerNumber unchanged (see credit_processor.py: the
    map_business_partner() call is commented out). So the S/4 side's
    company code has to be looked up indirectly, by tracing each row's
    KUNNR back to the ECC registry's own CustomerNumber -> Company
    Code mapping.

    That lookup assumes the mapping is unambiguous -- each
    CustomerNumber maps to exactly one Company Code in the registry.
    Any CustomerNumber that maps to more than one Company Code is
    reported as its own MAPPING_ERROR row instead of being silently
    assigned to one of them, since picking either would produce a
    misleading count. Any S/4 KUNNR with no match at all in the ECC
    registry is reported the same way, under "(unmatched KUNNR)".
    """

    missing = first_missing_column(ecc_df, ["CustomerNumber", "Company Code"])
    if missing:
        return missing_column_check("Company Code Distribution", "ECC registry", missing)

    missing = first_missing_column(s4_df, ["KUNNR"])
    if missing:
        return missing_column_check("Company Code Distribution", "S/4 file", missing)

    ecc_customer = ecc_df["CustomerNumber"].apply(clean_string)
    ecc_company_code = ecc_df["Company Code"].apply(clean_string).str.upper()

    # Build CustomerNumber -> Company Code, flagging any CustomerNumber
    # that maps to more than one distinct Company Code rather than
    # silently keeping "the last one seen".
    mapping_groups = (
        pd.DataFrame({"customer": ecc_customer, "company_code": ecc_company_code})
        .loc[lambda d: d["customer"] != ""]
        .groupby("customer")["company_code"]
        .agg(lambda codes: sorted(set(codes)))
    )

    ambiguous_customers = {
        customer: codes
        for customer, codes in mapping_groups.items()
        if len(codes) > 1
    }
    customer_to_company_code = {
        customer: codes[0]
        for customer, codes in mapping_groups.items()
        if len(codes) == 1
    }

    # ECC-side counts: how many registry rows belong to each company
    # code (unambiguous customers only -- an ambiguous CustomerNumber's
    # rows are excluded from every company code's count and reported
    # separately below instead).
    ecc_code_counts: Dict[str, int] = {}
    for customer, code in zip(ecc_customer, ecc_company_code):
        if customer in ambiguous_customers:
            continue
        ecc_code_counts[code] = ecc_code_counts.get(code, 0) + 1

    # S/4-side counts: resolve each row's KUNNR back to a company code
    # via the mapping built above.
    s4_kunnr = s4_df["KUNNR"].apply(clean_string)

    s4_code_counts: Dict[str, int] = {}
    unmatched_count = 0
    s4_ambiguous_count = 0

    for kunnr in s4_kunnr:
        if kunnr in ambiguous_customers:
            s4_ambiguous_count += 1
            continue
        code = customer_to_company_code.get(kunnr)
        if code is None:
            unmatched_count += 1
            continue
        s4_code_counts[code] = s4_code_counts.get(code, 0) + 1

    details = []

    distinct_codes = sorted(set(ecc_code_counts) | set(s4_code_counts))

    for code in distinct_codes:
        ecc_count = ecc_code_counts.get(code, 0)
        s4_count = s4_code_counts.get(code, 0)

        details.append(make_detail(
            label=code,
            left_count=ecc_count,
            right_count=s4_count,
            message=(
                "Company code count matches."
                if ecc_count == s4_count
                else f"Company code count mismatch: ECC={ecc_count}, S/4={s4_count}."
            ),
            company_code=code,
        ))

    # Ambiguous-mapping and unmatched-KUNNR rows are surfaced as their
    # own detail entries so they're visible in the report rather than
    # silently dropped from every company code's count.
    if ambiguous_customers:
        details.append(make_detail(
            label="(ambiguous CustomerNumber -> multiple Company Codes)",
            left_count=sum(
                1 for c in ecc_customer if c in ambiguous_customers
            ),
            right_count=s4_ambiguous_count,
            status="MAPPING_ERROR",
            message=(
                f"{len(ambiguous_customers)} CustomerNumber(s) map to more than one "
                "Company Code in the ECC registry and were excluded from every "
                "company code's count."
            ),
            customers=sorted(ambiguous_customers.keys()),
        ))

    if unmatched_count:
        details.append(make_detail(
            label="(unmatched KUNNR)",
            left_count=None,
            right_count=unmatched_count,
            status="MAPPING_ERROR",
            message=(
                f"{unmatched_count} S/4 row(s) have a KUNNR that does not match any "
                "CustomerNumber in the ECC registry."
            ),
        ))

    return make_check(
        check_name="Company Code Distribution",
        details=details,
        passing_message="All company code counts match.",
        failing_message="One or more company code counts do not match.",
    )


# ============================================================
# Check Registry
# ============================================================
# The single place that lists which checks run. Adding a check means
# writing one validate_* function above and appending it here --
# nothing in validate_credit_files needs to change.
# ============================================================

CHECK_FUNCTIONS: List[Callable[[pd.DataFrame, pd.DataFrame], Dict[str, Any]]] = [
    validate_credit_rep_group_counts,
    validate_company_code_counts,
]


# ============================================================
# Overall Validation
# ============================================================

def calculate_overall_status(checks: List[Dict[str, Any]]) -> str:
    """Overall validation passes only when every check passes."""
    return pass_fail(all(check.get("status") == "PASS" for check in checks))


def summarize_checks(checks: List[Dict[str, Any]]) -> Dict[str, int]:
    """Roll up per-check statuses into the summary block."""
    passed = sum(1 for check in checks if check["status"] == "PASS")
    return {
        "total_checks": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
    }


# ============================================================
# Main Credit Validation Function
# ============================================================

def validate_credit_files(registry_file, filled_file) -> Dict[str, Any]:
    """
    Run every check in CHECK_FUNCTIONS against the ECC registry and the
    filled S/4 template.

    Returns a structured dictionary that can be used by:
        1. FastAPI
        2. Frontend
        3. Future DOCX report generator
    """

    ecc_df = read_ecc_registry(registry_file)
    s4_df = read_s4_credit_profile(filled_file)

    checks = [check_fn(ecc_df, s4_df) for check_fn in CHECK_FUNCTIONS]

    return {
        "process": "CREDIT",
        "overall_status": calculate_overall_status(checks),
        "summary": summarize_checks(checks),
        "checks": checks,
    }