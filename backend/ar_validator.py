import io

import pandas as pd
import openpyxl

import mappings


# ============================================================
# AR Validation Configuration
# ============================================================

ECC_START_ROW = 2
S4_START_ROW = 9

S4_SHEET_NAME = "Customer Open Items"

COMPANY_CODE_MAPPING = mappings.COMPANY_CODE_MAPPING


# ============================================================
# Utility Functions
# ============================================================

def clean_string(value):
    """
    Convert a cell value to a clean string.

    Empty/NaN values become "".
    Numeric values such as 1000.0 become "1000".
    """
    if value is None or pd.isna(value):
        return ""

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value).strip()


def is_non_empty(value):
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
# Excel Reading
# ============================================================

def read_ecc_registry(registry_file):
    """
    Read the ECC AR registry.

    ECC data begins from Excel row 2, so row 2 is treated
    as the header row and records begin from row 3.
    """

    df = pd.read_excel(
        registry_file,
        header=0,
    )

    # Remove completely empty rows.
    df = df.dropna(how="all")

    return df


def read_s4_customer_open_items(filled_file):
    """
    Read the S/4 Customer Open Items sheet.

    S/4 template structure:
        Row 5 = technical field names (BUKRS, KUNNR, BLART, etc.)
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
    # BUKRS, KUNNR, BLART, BLDAT, etc.
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
# Total Record Count
# ============================================================

def validate_record_count(ecc_df, s4_df):
    """
    Compare the total number of ECC records against
    the total number of S/4 records.
    """

    ecc_count = len(ecc_df)
    s4_count = len(s4_df)

    difference = ecc_count - s4_count

    status = "PASS" if difference == 0 else "FAIL"

    if status == "PASS":
        message = (
            f"Record count matches. "
            f"Both ECC and S/4 contain {ecc_count} records."
        )
    else:
        message = (
            f"Record count mismatch. "
            f"ECC contains {ecc_count} records while "
            f"S/4 contains {s4_count} records."
        )

    return {
        "check_name": "Total Record Count",
        "status": status,
        "ecc_count": ecc_count,
        "s4_count": s4_count,
        "difference": difference,
        "message": message,
    }


# ============================================================
# Validation 2
# Company Code Distribution
# ============================================================

def validate_company_code_counts(ecc_df, s4_df):
    """
    Dynamically determine all ECC company codes and compare
    their counts against the corresponding S/4 company codes.

    Example:

        ECC       S/4
        US01  ->  1000
        US06  ->  1001
        CA01  ->  1200

    The company codes are NOT hardcoded into the validation
    logic. They are discovered from the registry.
    """

    if "Company Code" not in ecc_df.columns:
        return {
            "check_name": "Company Code Distribution",
            "status": "FAIL",
            "details": [],
            "message": (
                'ECC registry does not contain a "Company Code" column.'
            ),
        }

    if "BUKRS" not in s4_df.columns:
        return {
            "check_name": "Company Code Distribution",
            "status": "FAIL",
            "details": [],
            "message": (
                'S/4 file does not contain a "BUKRS" column.'
            ),
        }

    # Discover company codes dynamically from ECC.
    ecc_company_codes = (
        ecc_df["Company Code"]
        .apply(clean_string)
        .replace("", pd.NA)
        .dropna()
        .unique()
    )

    details = []
    overall_pass = True

    for ecc_code in ecc_company_codes:

        ecc_code = clean_string(ecc_code).upper()

        # Look up ECC -> S/4 mapping.
        s4_code = COMPANY_CODE_MAPPING.get(ecc_code)

        # Mapping does not exist.
        if not s4_code:
            details.append({
                "ecc_code": ecc_code,
                "s4_code": None,
                "ecc_count": int(
                    (
                        ecc_df["Company Code"]
                        .apply(clean_string)
                        .str.upper()
                        == ecc_code
                    ).sum()
                ),
                "s4_count": None,
                "difference": None,
                "status": "MAPPING_ERROR",
                "message": (
                    f"No ECC -> S/4 company code mapping exists "
                    f"for {ecc_code}."
                ),
            })

            overall_pass = False
            continue

        s4_code = clean_string(s4_code)

        # Count ECC company code.
        ecc_count = int(
            (
                ecc_df["Company Code"]
                .apply(clean_string)
                .str.upper()
                == ecc_code
            ).sum()
        )

        # Count corresponding S/4 company code.
        s4_count = int(
            (
                s4_df["BUKRS"]
                .apply(clean_string)
                == s4_code
            ).sum()
        )

        difference = ecc_count - s4_count

        status = "PASS" if difference == 0 else "FAIL"

        if status == "FAIL":
            overall_pass = False

        details.append({
            "ecc_code": ecc_code,
            "s4_code": s4_code,
            "ecc_count": ecc_count,
            "s4_count": s4_count,
            "difference": difference,
            "status": status,
            "message": (
                "Company code count matches."
                if status == "PASS"
                else (
                    f"Company code count mismatch: "
                    f"ECC={ecc_count}, S/4={s4_count}."
                )
            ),
        })

    return {
        "check_name": "Company Code Distribution",
        "status": "PASS" if overall_pass else "FAIL",
        "details": details,
        "message": (
            "All company code counts match."
            if overall_pass
            else "One or more company code counts do not match."
        ),
    }

# ============================================================
# Validation 3
# Sign Validation
# ============================================================

def validate_sign(ecc_df, s4_df):
    """
    Validate the sign of amounts between ECC and S/4.

    ECC:
        Debit/Credit Ind. = S -> amount is positive
        Debit/Credit Ind. = H -> amount is negative

    S/4:
        Positive WRBTR values must match ECC S total.
        Negative WRBTR values must match ECC H total
        in absolute value.
    """

    # --------------------------------------------------------
    # ECC amounts
    # --------------------------------------------------------

    ecc_amounts = pd.to_numeric(
        ecc_df["Amount"],
        errors="coerce"
    ).fillna(0)

    ecc_indicator = (
        ecc_df["Debit/Credit Ind."]
        .apply(clean_string)
        .str.upper()
    )

    # S = positive
    ecc_s_total = ecc_amounts[ecc_indicator == "S"].abs().sum()

    # H = negative
    ecc_h_total = ecc_amounts[ecc_indicator == "H"].abs().sum()

    # --------------------------------------------------------
    # S/4 WRBTR amounts
    # --------------------------------------------------------

    s4_amounts = pd.to_numeric(
        s4_df["WRBTR"],
        errors="coerce"
    ).fillna(0)

    # Positive S/4 amounts
    s4_positive_total = s4_amounts[s4_amounts > 0].sum()

    # Negative S/4 amounts
    s4_negative_total = s4_amounts[s4_amounts < 0].abs().sum()

    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    s_match = abs(ecc_s_total - s4_positive_total) < 0.01
    h_match = abs(ecc_h_total - s4_negative_total) < 0.01

    status = "PASS" if s_match and h_match else "FAIL"

    if status == "PASS":
        message = (
            "ECC S/H amount totals match the corresponding "
            "positive/negative S/4 WRBTR totals."
        )
    else:
        message = (
            "Sign validation failed. One or both ECC S/H totals "
            "do not match the corresponding S/4 positive/negative totals."
        )

    return {
        "check_name": "Amount Sign Validation",
        "status": status,
        "ecc_s_total": float(ecc_s_total),
        "s4_positive_total": float(s4_positive_total),
        "s_difference": float(
            ecc_s_total - s4_positive_total
        ),
        "ecc_h_total": float(ecc_h_total),
        "s4_negative_total": float(
            -s4_negative_total
        ),
        "h_difference": float(
            -ecc_h_total + s4_negative_total
        ),
        "s_status": "PASS" if s_match else "FAIL",
        "h_status": "PASS" if h_match else "FAIL",
        "message": message,
    }

# ============================================================
# Validation 4
# Payment Terms Blank Count
# ============================================================

def validate_payment_terms_blank_count(ecc_df, s4_df):
    """
    Validate that the number of blank Terms of Payment values
    in the ECC registry matches the number of
    'No payment terms in ECC' values in S/4 ZTERM.
    """

    # --------------------------------------------------------
    # ECC: Count blank Terms of Payment
    # --------------------------------------------------------

    ecc_payment_terms = ecc_df["Terms of Payment"]

    ecc_blank_count = int(
        ecc_payment_terms.apply(
            lambda value: not is_non_empty(value)
        ).sum()
    )

    # --------------------------------------------------------
    # S/4: Count 'No payment terms in ECC' in ZTERM
    # --------------------------------------------------------

    s4_payment_terms = s4_df["ZTERM"]

    s4_no_payment_terms_count = int(
        s4_payment_terms.apply(
            lambda value: clean_string(value) == "No payment terms in ECC"
        ).sum()
    )

    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    difference = ecc_blank_count - s4_no_payment_terms_count

    status = "PASS" if difference == 0 else "FAIL"

    if status == "PASS":
        message = (
            "Payment terms blank count matches. "
            f"ECC contains {ecc_blank_count} blank Terms of Payment values "
            f"and S/4 contains {s4_no_payment_terms_count} "
            "'No payment terms in ECC' values in ZTERM."
        )
    else:
        message = (
            "Payment terms blank count mismatch. "
            f"ECC contains {ecc_blank_count} blank Terms of Payment values "
            f"while S/4 contains {s4_no_payment_terms_count} "
            "'No payment terms in ECC' values in ZTERM."
        )

    return {
        "check_name": "Payment Terms Blank Count",
        "status": status,
        "ecc_blank_count": ecc_blank_count,
        "s4_no_payment_terms_count": s4_no_payment_terms_count,
        "difference": difference,
        "message": message,
    }


# ============================================================
# Overall Validation
# ============================================================



def calculate_overall_status(checks):
    """
    Overall validation passes only when every check passes.
    """

    for check in checks:
        if check.get("status") != "PASS":
            return "FAIL"

    return "PASS"


# ============================================================
# Main AR Validation Function
# ============================================================

def validate_ar_files(registry_file, filled_file):
    """
    Run all currently implemented AR validations.

    Returns a structured dictionary that can be used by:
        1. FastAPI
        2. Frontend
        3. Future DOCX report generator
    """

    ecc_df = read_ecc_registry(registry_file)

    s4_df = read_s4_customer_open_items(filled_file)

    checks = []

    # --------------------------------------------------------
    # Check 1: Total record count
    # --------------------------------------------------------

    checks.append(
        validate_record_count(
            ecc_df,
            s4_df,
        )
    )

    # --------------------------------------------------------
    # Check 2: Company code distribution
    # --------------------------------------------------------

    checks.append(
        validate_company_code_counts(
            ecc_df,
            s4_df,
        )
    )

    # --------------------------------------------------------
    # Check 3: Amount sign validation
    # --------------------------------------------------------

    checks.append(
        validate_sign(
            ecc_df,
            s4_df,
        )
    )

    # --------------------------------------------------------
    # Check 4: Payment Terms Blank Count
    # --------------------------------------------------------

    checks.append(
        validate_payment_terms_blank_count(
            ecc_df,
            s4_df,
        )
    )

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    overall_status = calculate_overall_status(checks)

    return {
        "process": "AR",
        "overall_status": overall_status,
        "summary": {
            "total_checks": len(checks),
            "passed": sum(
                1
                for check in checks
                if check["status"] == "PASS"
            ),
            "failed": sum(
                1
                for check in checks
                if check["status"] == "FAIL"
            ),
        },
        "checks": checks,
    }