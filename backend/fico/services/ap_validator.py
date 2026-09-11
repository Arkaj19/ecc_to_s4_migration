"""
AP (Accounts Payable) migration validator.

Compares an ECC AP registry (BSIK extract) against a filled-in S/4
"Vendor Open Items" template and runs a fixed set of reconciliation
checks between them.

This mirrors ar_validator.py's architecture exactly -- same result
shape, same helper functions, same one-function-per-check pattern --
so the two validators (and their frontends) behave identically. Only
the AP-specific field names, mappings, and sheet layout differ.

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
        "money": bool,                 # optional, present only when True
        ... detail-specific extra fields ...
    }

Adding a 4th check means writing one ``validate_*`` function with this
shape and adding it to ``CHECK_FUNCTIONS`` below -- nothing else changes.
"""

from typing import Any, Callable, Dict, Iterable, List, Optional

import pandas as pd
import openpyxl

from backend.fico.repo import mappings
from backend.fico.utils.format_utils import clean_string, normalize_series


# ============================================================
# AP Validation Configuration
# ============================================================

ECC_START_ROW = 2
S4_START_ROW = 9

S4_SHEET_NAME = "Vendor Open Items"

# ============================================================
# Company Code Mapping (ECC -> S/4)
# ============================================================
# Sourced from mappings.COMPANY_CODE_MAPPING (shared with
# ap_processor.py / ar_processor.py / asset_processor.py /
# credit_processor.py) rather than a local copy.
#
# This validator's own table was originally derived from the
# BSIK_AP_Registry.xlsx / AP_Data_Load_SIT2 sample files by aligning
# rows on XBLNR (Reference Document Number, identical on both sides
# for the same physical document) and cross-tabulating BUKRS on each
# side: {"CA01": "1200", "US01": "1000", "US09": "US09"}.
#
# Compared against mappings.COMPANY_CODE_MAPPING before consolidating:
# every overlapping key already agreed on its S/4 value (CA01, US01),
# so there was no conflict to resolve -- only a coverage gap on each
# side (this table was missing US06; mappings.py was missing the
# self-mapped US09). Both have now been folded into
# mappings.COMPANY_CODE_MAPPING as the single canonical table, so
# nothing here loses coverage.
# ============================================================


# ============================================================
# Payment Terms Mapping (ECC ZTERM -> S/4 ZTERM)
# ============================================================
# Sourced from mappings.AP_PAYMENT_TERMS_MAPPING rather than a local
# copy. This validator's own table held 24 ECC codes (A, B, BB, C, D,
# EE, G, H, J, L, N65, N110, N115, N120, N125, O, Q, R, T, T70, TT, Y,
# YY, ZZ) -- every one of them mapped to the exact same S/4 term in
# mappings.AP_PAYMENT_TERMS_MAPPING, so this was a strict subset with
# zero conflicts, not a separate table. mappings.py's table additionally
# covers about two dozen more ECC codes this validator previously
# treated as "unmapped" (silently excluded from the payment-terms-group
# check below) -- those will now resolve and be counted like any other
# code, which is a widening of coverage rather than a change in logic.
#
# Unlike AR (which groups into N / P / Z / E), AP payment terms group
# into only two buckets for this check:
#   N -> Net terms
#   Z -> Discount terms
# The single observed P-prefixed term (J -> P215, 2 occurrences) falls
# outside both groups and is silently excluded, same as AR excludes
# any prefix outside its defined group set.
# ============================================================

_NORMALIZED_PAYMENT_MAPPING = {
    key.upper(): value for key, value in mappings.AP_PAYMENT_TERMS_MAPPING.items()
}


# ============================================================
# Utility Functions
# ============================================================

def is_non_empty(value: Any) -> bool:
    """
    Returns True when an Excel cell contains an actual value.
    """
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
    money: bool = False,
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

    if money:
        detail["money"] = True

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
    Read the ECC AP registry (BSIK extract).

    Row 1 is the header row; records begin from row 2.
    """

    df = pd.read_excel(
        registry_file,
        header=0,
    )

    # Remove completely empty rows.
    df = df.dropna(how="all")

    return df


def read_s4_vendor_open_items(filled_file) -> pd.DataFrame:
    """
    Read the S/4 Vendor Open Items sheet.

    S/4 template structure:
        Row 5 = technical field names (BUKRS, LIFNR, BLART, etc.)
        Row 8 = human-readable field descriptions
        Row 9 onward = actual records

    The validator uses the technical field names so that
    validations can consistently refer to fields such as BUKRS.
    """

    wb = openpyxl.load_workbook(
        filled_file,
        read_only=True,
        data_only=True,
    )

    if S4_SHEET_NAME not in wb.sheetnames:
        raise ValueError(
            f'S/4 file does not contain the required sheet '
            f'"{S4_SHEET_NAME}".'
        )

    ws = wb[S4_SHEET_NAME]

    # ------------------------------------------------------------
    # Row 5 contains the technical field names:
    # BUKRS, LIFNR, BLART, ZTERM, XREF1, etc.
    # ------------------------------------------------------------
    technical_headers = [
        clean_string(cell.value)
        for cell in ws[5]
    ]

    # ------------------------------------------------------------
    # Row 8 contains human-readable labels.
    # We don't use these as DataFrame column names, but we
    # retain the structure of the template.
    # ------------------------------------------------------------
    descriptive_headers = [
        clean_string(cell.value)
        for cell in ws[8]
    ]

    # ------------------------------------------------------------
    # Read actual data beginning from row 9.
    # ------------------------------------------------------------
    records = []

    for row in ws.iter_rows(
        min_row=S4_START_ROW,
        values_only=True,
    ):
        # Ignore completely empty rows.
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
# Company Code Distribution
# ============================================================

def validate_company_code_counts(ecc_df: pd.DataFrame, s4_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Dynamically determine all ECC company codes and compare
    their counts against the corresponding S/4 company codes.

    Example:

        ECC       S/4
        US01  ->  1000
        CA01  ->  1200
        US09  ->  US09

    The company codes are NOT hardcoded into the validation
    logic itself -- they are discovered from the registry and
    looked up in mappings.COMPANY_CODE_MAPPING.
    """

    missing = first_missing_column(ecc_df, ["BUKRS"])
    if missing:
        return missing_column_check("Company Code Distribution", "ECC registry", missing)

    missing = first_missing_column(s4_df, ["BUKRS"])
    if missing:
        return missing_column_check("Company Code Distribution", "S/4 file", missing)

    ecc_codes = normalize_series(ecc_df["BUKRS"])
    s4_codes = normalize_series(s4_df["BUKRS"])

    # Discover company codes dynamically from ECC.
    distinct_ecc_codes = ecc_codes.replace("", pd.NA).dropna().unique()

    details = []

    for ecc_code in distinct_ecc_codes:
        ecc_code = ecc_code.upper()
        ecc_count = int((ecc_codes == ecc_code).sum())

        # Look up ECC -> S/4 mapping.
        s4_code = mappings.COMPANY_CODE_MAPPING.get(ecc_code)

        if not s4_code:
            details.append(make_detail(
                label=f"{ecc_code} (no mapping)",
                left_count=ecc_count,
                right_count=None,
                status="MAPPING_ERROR",
                message=f"No ECC -> S/4 company code mapping exists for {ecc_code}.",
                ecc_code=ecc_code,
                s4_code=None,
            ))
            continue

        s4_code = clean_string(s4_code).upper()
        s4_count = int((s4_codes == s4_code).sum())

        details.append(make_detail(
            label=f"{ecc_code} \u2192 {s4_code}",
            left_count=ecc_count,
            right_count=s4_count,
            message=(
                "Company code count matches."
                if ecc_count == s4_count
                else f"Company code count mismatch: ECC={ecc_count}, S/4={s4_count}."
            ),
            ecc_code=ecc_code,
            s4_code=s4_code,
        ))

    return make_check(
        check_name="Company Code Distribution",
        details=details,
        passing_message="All company code counts match.",
        failing_message="One or more company code counts do not match.",
    )


# ============================================================
# Validation 2
# Amount Sign Validation (DMBTR, company-code wise)
# ============================================================

def validate_sign(ecc_df: pd.DataFrame, s4_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate S/H amount totals company-code-wise.

    ECC carries DMBTR as an unsigned amount plus a separate SHKZG
    (S = debit, H = credit) indicator. S/4 carries the sign directly
    in DMBTR (positive = debit, negative = credit). For each company
    code we sum the absolute ECC amounts per indicator and compare
    against the sum of the correspondingly-signed S/4 amounts.
    """
    missing = first_missing_column(ecc_df, ["BUKRS", "DMBTR", "SHKZG"])
    if missing:
        return missing_column_check("Amount Sign Validation", "ECC registry", missing)

    missing = first_missing_column(s4_df, ["BUKRS", "DMBTR"])
    if missing:
        return missing_column_check("Amount Sign Validation", "S/4 file", missing)

    ecc_codes = normalize_series(ecc_df["BUKRS"])
    s4_codes = normalize_series(s4_df["BUKRS"])
    ecc_amounts = pd.to_numeric(ecc_df["DMBTR"], errors="coerce").fillna(0)
    ecc_indicator = normalize_series(ecc_df["SHKZG"])
    s4_amounts = pd.to_numeric(s4_df["DMBTR"], errors="coerce").fillna(0)

    TOLERANCE = 0.01
    details = []
    distinct_ecc_codes = ecc_codes.replace("", pd.NA).dropna().unique()

    for ecc_code in distinct_ecc_codes:
        ecc_code = ecc_code.upper()
        s4_code = mappings.COMPANY_CODE_MAPPING.get(ecc_code)

        if not s4_code:
            for direction, label in [("S", "S / Debit (positive)"), ("H", "H / Credit (negative)")]:
                details.append(make_detail(
                    label=f"{ecc_code} (no mapping) | {label}",
                    left_count=None, right_count=None, status="MAPPING_ERROR",
                    message=f"No ECC -> S/4 company code mapping exists for {ecc_code}.",
                    money=True, ecc_code=ecc_code, s4_code=None, direction=direction,
                ))
            continue

        s4_code = clean_string(s4_code).upper()
        ecc_mask = ecc_codes == ecc_code
        s4_mask = s4_codes == s4_code
        ecc_s_total = float(ecc_amounts[ecc_mask & (ecc_indicator == "S")].abs().sum())
        ecc_h_total = float(ecc_amounts[ecc_mask & (ecc_indicator == "H")].abs().sum())
        s4_positive_total = float(s4_amounts[s4_mask & (s4_amounts > 0)].sum())
        s4_negative_total = float(s4_amounts[s4_mask & (s4_amounts < 0)].abs().sum())
        s_match = abs(ecc_s_total - s4_positive_total) < TOLERANCE
        h_match = abs(ecc_h_total - s4_negative_total) < TOLERANCE

        details.append(make_detail(
            label=f"{ecc_code} -> {s4_code} | S / Debit (positive)",
            left_count=ecc_s_total, right_count=s4_positive_total, status=pass_fail(s_match),
            message=("S (debit) total matches S/4 positive DMBTR total." if s_match else f"S (debit) mismatch: ECC={ecc_s_total:.2f}, S/4 positive={s4_positive_total:.2f}."),
            money=True, ecc_code=ecc_code, s4_code=s4_code, direction="S",
        ))
        details.append(make_detail(
            label=f"{ecc_code} -> {s4_code} | H / Credit (negative)",
            left_count=ecc_h_total, right_count=s4_negative_total, status=pass_fail(h_match),
            message=("H (credit) total matches S/4 negative DMBTR total." if h_match else f"H (credit) mismatch: ECC={ecc_h_total:.2f}, S/4 negative={s4_negative_total:.2f}."),
            money=True, ecc_code=ecc_code, s4_code=s4_code, direction="H",
        ))

    return make_check(
        check_name="Amount Sign Validation", details=details,
        passing_message="ECC S/H DMBTR totals match S/4 positive/negative DMBTR totals for every company code.",
        failing_message="Amount sign validation failed for one or more company codes.",
        tolerance=TOLERANCE, company_code_wise=True,
    )


# ============================================================
# Validation 3
# Unique Document Number Count (BELNR vs XREF1)
# ============================================================

# def validate_unique_document_number_counts(ecc_df: pd.DataFrame, s4_df: pd.DataFrame) -> Dict[str, Any]:
#     """Compare unique ECC BELNR vs S/4 XREF1 counts by company code."""
#     missing = first_missing_column(ecc_df, ["BUKRS", "BELNR"])
#     if missing:
#         return missing_column_check("Unique Document Number Count", "ECC registry", missing)
#     missing = first_missing_column(s4_df, ["BUKRS", "XREF1"])
#     if missing:
#         return missing_column_check("Unique Document Number Count", "S/4 file", missing)

#     ecc_codes = normalize_series(ecc_df["BUKRS"])
#     s4_codes = normalize_series(s4_df["BUKRS"])
#     ecc_documents = ecc_df["BELNR"].apply(clean_string)
#     s4_xref1 = s4_df["XREF1"].apply(clean_string)
#     details = []

#     for ecc_code in ecc_codes.replace("", pd.NA).dropna().unique():
#         ecc_code = ecc_code.upper()
#         s4_code = COMPANY_CODE_MAPPING.get(ecc_code)
#         if not s4_code:
#             details.append(make_detail(
#                 label=f"{ecc_code} (no mapping)", left_count=None, right_count=None,
#                 status="MAPPING_ERROR",
#                 message=f"No ECC -> S/4 company code mapping exists for {ecc_code}.",
#                 ecc_code=ecc_code, s4_code=None,
#             ))
#             continue

#         s4_code = clean_string(s4_code).upper()
#         ecc_mask = ecc_codes == ecc_code
#         s4_mask = s4_codes == s4_code
#         ecc_unique = int(ecc_documents[ecc_mask & (ecc_documents != "")].nunique())
#         s4_unique = int(s4_xref1[s4_mask & (s4_xref1 != "")].nunique())

#         details.append(make_detail(
#             label=f"{ecc_code} -> {s4_code}", left_count=ecc_unique, right_count=s4_unique,
#             message=("Unique document number count matches." if ecc_unique == s4_unique else f"Unique document number count mismatch: ECC BELNR={ecc_unique}, S/4 XREF1={s4_unique}."),
#             ecc_code=ecc_code, s4_code=s4_code,
#             ecc_unique_belnr_count=ecc_unique, s4_unique_xref1_count=s4_unique,
#         ))

#     return make_check(
#         check_name="Unique Document Number Count", details=details,
#         passing_message="Unique ECC BELNR counts match unique S/4 XREF1 counts for every company code.",
#         failing_message="Unique document number count validation failed for one or more company codes.",
#         company_code_wise=True,
#     )

def validate_unique_document_number_counts(ecc_df: pd.DataFrame, s4_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compare unique ECC document identifiers (mapped to XREF1) against unique S/4 XREF1 counts.

    Replicates the XREF1 mapping logic from ap_processor.py:
        - If document type (BLART) is 'KR' or 'RE', XREF1 = BELNR (Document Number)
        - Otherwise, XREF1 = Reference Key 1 (XREF1)  [may be blank]

    Non‑empty values are counted uniquely per company code.
    """
    # Validate required columns exist
    ecc_req = ["BUKRS", "BELNR"]
    # We also need document type; check both possible column names
    doc_type_col = None
    if "BLART" in ecc_df.columns:
        doc_type_col = "BLART"
    elif "Document Type" in ecc_df.columns:
        doc_type_col = "Document Type"
    else:
        return missing_column_check("Unique Document Number Count", "ECC registry", "BLART or Document Type")

    # We need Reference Key 1; check both possible names
    xref1_col = None
    if "XREF1" in ecc_df.columns:
        xref1_col = "XREF1"
    elif "Reference Key 1" in ecc_df.columns:
        xref1_col = "Reference Key 1"
    else:
        # If absent, treat as all blank (the processor also treats missing as blank)
        xref1_col = None

    if doc_type_col is None:
        return missing_column_check("Unique Document Number Count", "ECC registry", "BLART or Document Type")

    missing = first_missing_column(s4_df, ["BUKRS", "XREF1"])
    if missing:
        return missing_column_check("Unique Document Number Count", "S/4 file", missing)

    ecc_codes = normalize_series(ecc_df["BUKRS"])
    s4_codes = normalize_series(s4_df["BUKRS"])
    s4_xref1 = s4_df["XREF1"].apply(clean_string)

    details = []
    distinct_ecc_codes = ecc_codes.replace("", pd.NA).dropna().unique()

    for ecc_code in distinct_ecc_codes:
        ecc_code = ecc_code.upper()
        s4_code = mappings.COMPANY_CODE_MAPPING.get(ecc_code)
        if not s4_code:
            details.append(make_detail(
                label=f"{ecc_code} (no mapping)", left_count=None, right_count=None,
                status="MAPPING_ERROR",
                message=f"No ECC -> S/4 company code mapping exists for {ecc_code}.",
                ecc_code=ecc_code, s4_code=None,
            ))
            continue

        s4_code = clean_string(s4_code).upper()
        ecc_mask = ecc_codes == ecc_code

        # Build expected XREF1 for each ECC row in this company code
        expected_xref1_values = []
        for idx, row in ecc_df[ecc_mask].iterrows():
            doc_type = clean_string(row.get(doc_type_col)).upper()
            belnr = clean_string(row.get("BELNR"))
            xref1_raw = clean_string(row.get(xref1_col)) if xref1_col else ""

            if doc_type in ("KR", "RE"):
                val = belnr
            else:
                val = xref1_raw

            if val:  # non‑empty
                expected_xref1_values.append(val)

        ecc_unique = len(set(expected_xref1_values))

        # S/4 side
        s4_mask = s4_codes == s4_code
        s4_unique = int(s4_xref1[s4_mask & (s4_xref1 != "")].nunique())

        details.append(make_detail(
            label=f"{ecc_code} -> {s4_code}",
            left_count=ecc_unique,
            right_count=s4_unique,
            message=(
                "Unique expected XREF1 count matches S/4 XREF1 count."
                if ecc_unique == s4_unique
                else f"Unique expected XREF1 mismatch: ECC={ecc_unique}, S/4={s4_unique}."
            ),
            ecc_code=ecc_code,
            s4_code=s4_code,
            ecc_unique_expected_xref1=ecc_unique,
            s4_unique_xref1=s4_unique,
        ))

    return make_check(
        check_name="Unique Document Number Count",
        details=details,
        passing_message="Unique expected XREF1 counts match S/4 XREF1 counts for every company code.",
        failing_message="Unique document number (XREF1) validation failed for one or more company codes.",
        company_code_wise=True,
    )

# ============================================================
# Validation 4
# Payment Terms Group Count (by first letter of S/4 term)
# ============================================================

def validate_payment_terms_group_counts(ecc_df: pd.DataFrame, s4_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compare payment-term counts grouped by the first letter of the mapped S/4 term.

    Groups (AP only uses two, unlike AR's four):
      - Net (N): S/4 terms starting with 'N'
      - Discount (Z): S/4 terms starting with 'Z'

    For each ECC row, we look up its ZTERM in PAYMENT_TERMS_MAPPING,
    take the first character of the mapped S/4 term, and assign to
    one of the two groups. For each S/4 row, we take the first
    character of ZTERM directly and assign accordingly.
    Counts are compared per group.

    ECC terms with no mapping, and terms (on either side) whose prefix
    isn't N/Z (e.g. the observed P215), are excluded from every
    group's count -- this check only reports on the two groups
    themselves, not on what didn't make it into one. Blank ZTERM
    values are excluded on both sides.
    """

    missing = first_missing_column(ecc_df, ["ZTERM"])
    if missing:
        return missing_column_check("Payment Terms Group Count", "ECC registry", missing)

    missing = first_missing_column(s4_df, ["ZTERM"])
    if missing:
        return missing_column_check("Payment Terms Group Count", "S/4 file", missing)

    ecc_terms_raw = normalize_series(ecc_df["ZTERM"])
    s4_terms_raw = normalize_series(s4_df["ZTERM"])

    # Prepare counters -- AP only has N and Z groups.
    groups = {
        "N": {"label": "Net (N)", "ecc_count": 0, "s4_count": 0},
        "Z": {"label": "Discount (Z)", "ecc_count": 0, "s4_count": 0},
    }

    # Process ECC: unmapped terms, blanks, and terms that map to a
    # prefix outside N/Z, are silently skipped -- they don't count
    # toward any group.
    for term in ecc_terms_raw:
        if term == "":
            continue
        mapped = _NORMALIZED_PAYMENT_MAPPING.get(term)
        if mapped is None:
            continue
        first_char = mapped[0] if mapped else ""
        if first_char in groups:
            groups[first_char]["ecc_count"] += 1

    # Process S/4: ZTERM values whose prefix isn't N/Z are silently
    # skipped, same as on the ECC side.
    for term in s4_terms_raw:
        if term == "":
            continue
        first_char = term[0] if term else ""
        if first_char in groups:
            groups[first_char]["s4_count"] += 1

    # Build details list -- just the two groups, nothing else.
    details = []
    failed_groups = []

    for prefix, data in groups.items():
        ecc_cnt = data["ecc_count"]
        s4_cnt = data["s4_count"]
        status = pass_fail(ecc_cnt == s4_cnt)
        if status == "FAIL":
            failed_groups.append(data["label"])
        details.append(make_detail(
            label=data["label"],
            left_count=ecc_cnt,
            right_count=s4_cnt,
            status=status,
            message=(
                f"{data['label']} counts match."
                if ecc_cnt == s4_cnt
                else f"{data['label']} mismatch: ECC={ecc_cnt}, S/4={s4_cnt}."
            ),
            prefix=prefix,
        ))

    # Build final check
    total_ecc = sum(g["ecc_count"] for g in groups.values())
    total_s4 = sum(g["s4_count"] for g in groups.values())

    passing_msg = "Both payment term groups (N, Z) have matching counts."
    failing_msg = (
        "Payment term group validation failed. Mismatched groups: "
        + ", ".join(failed_groups) + "."
    )

    return make_check(
        check_name="Payment Terms Group Count",
        details=details,
        passing_message=passing_msg,
        failing_message=failing_msg,
        ecc_total_count=total_ecc,
        s4_total_count=total_s4,
        difference=total_ecc - total_s4,
        groups=groups,
    )


# ============================================================
# Check Registry
# ============================================================
# The single place that lists which checks run. Adding a check means
# writing one validate_* function above and appending it here --
# nothing in validate_ap_files needs to change.
# ============================================================

CHECK_FUNCTIONS: List[Callable[[pd.DataFrame, pd.DataFrame], Dict[str, Any]]] = [
    validate_company_code_counts,
    validate_sign,
    validate_unique_document_number_counts,
    validate_payment_terms_group_counts,
]


# ============================================================
# Overall Validation
# ============================================================

def calculate_overall_status(checks: List[Dict[str, Any]]) -> str:
    """
    Overall validation passes only when every check passes.
    """
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
# Main AP Validation Function
# ============================================================

def validate_ap_files(registry_file, filled_file) -> Dict[str, Any]:
    """
    Run every check in CHECK_FUNCTIONS against the ECC registry and the
    filled S/4 template.

    Returns a structured dictionary that can be used by:
        1. FastAPI
        2. Frontend
        3. Future DOCX report generator
    """

    ecc_df = read_ecc_registry(registry_file)
    s4_df = read_s4_vendor_open_items(filled_file)

    checks = [check_fn(ecc_df, s4_df) for check_fn in CHECK_FUNCTIONS]

    return {
        "process": "AP",
        "overall_status": calculate_overall_status(checks),
        "summary": summarize_checks(checks),
        "checks": checks,
    }