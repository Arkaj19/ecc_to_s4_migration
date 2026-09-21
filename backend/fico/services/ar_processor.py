# ar_processor.py

import io
import datetime

import pandas as pd
import openpyxl
from openpyxl.styles import PatternFill
from backend.config import BUT_REFERENCE_PATH
from backend.fico.repo import mappings
from backend.fico.repo.reference_mappings import load_but_mapping, map_business_partner
from backend.fico.utils.format_utils import clean_string, clean_date, clean_float
# NOTE: AR currently uses the plain (non-accounting-format) clean_float --
# see utils/format_utils.py docstring for the open question on whether AR
# registries can contain SAP accounting-style negatives ("5,114.43-"); if
# so, switch this to clean_float_accounting like ap_processor.py does.

# ... (existing constants and helper functions remain unchanged) ...

# ---------------------------------------------------------------------
# Company Code <-> Currency sanity check
#
# S/4 company code 1200 (Canada) should only ever carry CAD, and 1000
# (US) should only ever carry USD. A row with the "wrong" currency for
# its company code most likely points at a mis-tagged registry entry,
# so these combinations are flagged for the user to review rather than
# silently migrated.
# ---------------------------------------------------------------------

INVALID_CURRENCY_FOR_COMPANY_CODE = {
    "1200": "USD",
    "1000": "CAD",
}

# The other side of the same mapping -- what each company code SHOULD
# carry -- surfaced to the frontend so the review table can show
# "Expected" next to the offending "Currency" value.
EXPECTED_CURRENCY_FOR_COMPANY_CODE = {
    "1200": "CAD",
    "1000": "USD",
}

CURRENCY_MISMATCH_HIGHLIGHT_FILL = PatternFill(
    start_color="FFC7CE",
    end_color="FFC7CE",
    fill_type="solid",
)


def is_currency_mismatch(s4_company_code, currency):
    s4_company_code = clean_string(s4_company_code)
    currency = clean_string(currency).upper()
    return INVALID_CURRENCY_FOR_COMPANY_CODE.get(s4_company_code) == currency


class CurrencyReviewRequiredError(Exception):
    """
    Raised when the AR registry contains company-code / currency
    combinations that need an explicit user decision (keep or delete)
    before the file can be migrated. Callers should surface
    `review_payload` to the user and re-invoke `process_ar_registry`
    with the chosen `currency_action` ("KEEP" or "DELETE") once the
    user has decided.
    """

    def __init__(self, review_payload):
        self.review_payload = review_payload
        super().__init__(
            "Company code / currency mismatches require user review "
            "before the AR registry can be processed."
        )


def find_currency_mismatches(df):
    """
    Scans the raw registry dataframe for rows whose S/4 company code
    does not match an allowed currency (1200 -> CAD only, 1000 -> USD
    only) and returns a list of mismatch details, one per offending row.
    """
    mismatches = []

    for idx, source_row in df.iterrows():
        ecc_company_code = clean_string(source_row.get("Company Code"))
        s4_company_code = mappings.get_s4_ar_company_code(ecc_company_code)
        currency = clean_string(source_row.get("Currency")).upper()

        if is_currency_mismatch(s4_company_code, currency):
            mismatches.append({
                # +2 accounts for the 1-based Excel row and the header row
                "row": int(idx) + 2,
                "company_code": ecc_company_code,
                "s4_company_code": s4_company_code,
                "currency": currency,
                "expected_currency": EXPECTED_CURRENCY_FOR_COMPANY_CODE.get(s4_company_code),
                "customer": clean_string(source_row.get("Customer")),
                "document_number": clean_string(
                    source_row.get("Document Number")
                ),
                "amount": clean_float(source_row.get("Amount")),
            })

    return mismatches


def build_currency_mismatch_dump(df, mismatch_row_indices):
    """
    Builds a standalone workbook containing only the raw registry rows
    that were flagged for a company code / currency mismatch and then
    deleted, so the user has a record of what was removed.
    """
    dump_df = df.loc[sorted(mismatch_row_indices)]

    dump_wb = openpyxl.Workbook()
    dump_ws = dump_wb.active
    dump_ws.title = "Deleted - Currency Mismatch"

    dump_ws.append(list(dump_df.columns))
    for _, row in dump_df.iterrows():
        dump_ws.append([
            clean_string(value) if isinstance(value, float) and pd.isna(value)
            else value
            for value in row.tolist()
        ])

    dump_buffer = io.BytesIO()
    dump_wb.save(dump_buffer)
    dump_buffer.seek(0)
    return dump_buffer

REASON_CODE_MAPPING = {
    "DIC": "048",
    "FRW": "031",
    "PEC": "021",
    "PRC": "024",
    "SSC": "036",
    "UDC": "001",
    "UPC": "011",
}

def get_reason_code(reason_code):
    return REASON_CODE_MAPPING.get(
        clean_string(reason_code).upper(),
        "",
    )


def normalize_amount(amount, debit_credit_indicator):
    """
    S -> positive
    H -> negative

    Positive values are written normally (500), not as '+500'.
    """
    amount = clean_float(amount)

    if amount is None:
        return None

    amount = abs(amount)
    indicator = clean_string(debit_credit_indicator).upper()

    if indicator == "S":
        return amount

    if indicator == "H":
        return -amount

    return amount


def get_reference_value(reference):
    reference = clean_string(reference)
    return reference if reference else "No reference in ECC"


def get_document_type_mappings(
    document_type,
    assignment,
    text,
    reference,
    document_number,
):
    document_type = clean_string(document_type).upper()
    assignment = clean_string(assignment)
    text = clean_string(text)
    reference = get_reference_value(reference)
    document_number = clean_string(document_number)

    # RV:
    # Assignment -> Reference Document Number
    # Reference  -> Assignment Number
    if document_type == "RV":
        return {
            "reference_document_number": assignment if assignment else "No reference in ECC",
            "assignment": reference,
        }

    # DZ:
    # Reference -> Reference Document Number
    # Text      -> Assignment Number
    if document_type == "DZ":
        return {
            "reference_document_number": reference,
            "assignment": text,
        }

    # All other document types:
    # Document Number -> Reference Document Number
    # Assignment      -> Assignment Number
    return {
        "reference_document_number": document_number,
        "assignment": assignment,
    }


class RegistryMismatchError(ValueError):
    pass

# Add a list of technical field names that must be non-empty for each row
MANDATORY_FIELDS = [
    "BUKRS",   # Company Code
    "KUNNR",   # Customer
    "BLART",   # Document Type
    "BLDAT",   # Document Date
    "WAERS",   # Currency
    "WRBTR",   # Amount
    "MWSKZ",   # Tax Code
    "XBLNR",   # Reference Document Number
]


REQUIRED_AR_COLUMNS = [
    "Company Code",
    "Customer",
    "Assignment",
    "Document Number",
    "Document Date",
    "Currency",
    "Reference",
    "Document Type",
    "Debit/Credit Ind.",
    "Amount",
]


def process_ar_registry(
    registry_file,
    template_path="templates/Merged File all DOC Types.xlsx",
    but_path=BUT_REFERENCE_PATH,
    currency_action=None,
):
    """
    Processes the ECC Accounts Receivable registry and populates
    the S/4 migration template. Returns (output_buffer, validation_errors).

    currency_action controls how company-code / currency mismatches
    (1200 + USD, 1000 + CAD) are handled:
      - None (default): if any mismatches exist, no file is written.
        A CurrencyReviewRequiredError is raised instead, carrying a
        `review_payload` the caller can present to the user with a
        keep/delete choice.
      - "KEEP": mismatched rows are migrated as normal, but highlighted
        in red in the output workbook.
      - "DELETE": mismatched rows are excluded from the output workbook
        and instead written to a separate "dump" workbook, returned via
        `output.currency_review["dump_buffer"]`.

    Accepts "keep"/"delete" in any case -- normalized to upper below.
    """
    df = pd.read_excel(registry_file)

    if df.empty:
        raise RegistryMismatchError(
            "The uploaded AR registry is empty."
        )

    missing_columns = [
        column for column in REQUIRED_AR_COLUMNS if column not in df.columns
    ]
    if missing_columns:
        raise RegistryMismatchError(
            "The uploaded file does not contain the required AR "
            f"column(s): {', '.join(missing_columns)}."
        )

    # Normalize once, here, so every comparison below (and the
    # dump-branch, and the status string) can rely on it being
    # exactly None, "KEEP", or "DELETE" -- no more case mismatches.
    if currency_action is not None:
        currency_action = currency_action.strip().upper()

    if currency_action not in (None, "KEEP", "DELETE"):
        raise ValueError(
            f"Unrecognized currency_action: {currency_action!r}. "
            "Expected 'KEEP' or 'DELETE'."
        )

    # ---------------------------------------------------------
    # Company Code / Currency review
    # ---------------------------------------------------------

    currency_mismatches = find_currency_mismatches(df)
    mismatch_row_indices = {
        mismatch["row"] - 2 for mismatch in currency_mismatches
    }

    if currency_mismatches and currency_action is None:
        raise CurrencyReviewRequiredError({
            "status": "review_required",
            "action": None,
            "mismatch_count": len(currency_mismatches),
            "mismatches": currency_mismatches,
        })

    # ---------------------------------------------------------
    # Customer -> Business Partner mapping
    # ---------------------------------------------------------

    customer_but_mapping = load_but_mapping(
        but_path,
        id_type="DAP"
    )

    wb = openpyxl.load_workbook(template_path)

    if "Customer Open Items" in wb.sheetnames:
        ws = wb["Customer Open Items"]
    else:
        ws = wb[wb.sheetnames[0]]

    technical_columns = {}
    for col in range(1, ws.max_column + 1):
        value = clean_string(ws.cell(row=5, column=col).value)
        if value:
            technical_columns[value] = col

    reason_code_column = 64

    if not technical_columns:
        for col in range(1, ws.max_column + 1):
            value = clean_string(ws.cell(row=1, column=col).value)
            if value:
                technical_columns[value] = col

    data_start_row = 9

    for row in range(data_start_row, ws.max_row + 1):
        for col in range(1, ws.max_column + 1):
            ws.cell(row=row, column=col).value = None

    current_row = data_start_row
    validation_errors = []

    for idx, source_row in df.iterrows():
        if currency_action == "DELETE" and idx in mismatch_row_indices:
            continue

        ecc_company_code = clean_string(source_row.get("Company Code"))
        s4_company_code = mappings.get_s4_ar_company_code(ecc_company_code)

        original_document_type = clean_string(
            source_row.get("Document Type")
        ).upper()

        doc_type_mappings = get_document_type_mappings(
            document_type=original_document_type,
            assignment=source_row.get("Assignment"),
            text=source_row.get("Text"),
            reference=source_row.get("Reference"),
            document_number=source_row.get("Document Number"),
        )

        amount = normalize_amount(
            source_row.get("Amount"),
            source_row.get("Debit/Credit Ind."),
        )

        if s4_company_code in ("1000", "1001"):
            tax_code = "I0"
        elif s4_company_code == "1200":
            tax_code = "Z0"
        else:
            tax_code = ""

        document_number = clean_string(source_row.get("Document Number"))

        mapped_values = {
            "BUKRS": s4_company_code,
            "XBLNR": doc_type_mappings["reference_document_number"],
            "KUNNR": map_business_partner(
                    customer_but_mapping,
                    source_row.get("Customer")
                ),
            "GKONT": "9999900000",
            "BLART": "UE",
            "BLDAT": clean_date(source_row.get("Document Date")),
            "SGTXT": clean_string(source_row.get("Text")),
            "WAERS": clean_string(source_row.get("Currency")),
            "WRBTR": amount,
            "MWSKZ": tax_code,
            "ZTERM": mappings.get_s4_ar_payment_terms(
                    source_row.get("Terms of Payment")
                ),
            "ZFBDT": clean_date(source_row.get("Baseline Payment Dte")),
            "ZBD1T": clean_string(source_row.get("Days 1")),
            "ZBD1P": clean_float(source_row.get("Disc.percent 1")),
            "ZBD2T": clean_string(source_row.get("Days 2")),
            "ZBD2P": clean_float(source_row.get("Disc.percent 2")),
            "ZBD3T": clean_string(source_row.get("Days Net")),
            "SKFBT": normalize_amount(
                        source_row.get("Discount base"),
                        source_row.get("Debit/Credit Ind.")
                    ),
            "KKBER": s4_company_code,
            "ZUONR": doc_type_mappings["assignment"],
            "RSTGR": get_reason_code(source_row.get("Reason code")),
            "XREF1": document_number,
        }

        for tech_field, value in mapped_values.items():
            if tech_field in technical_columns:
                ws.cell(
                    row=current_row,
                    column=technical_columns[tech_field],
                    value=value,
                )

        reason_code = get_reason_code(
            source_row.get("Reason code")
        )

        ws.cell(
            row=current_row,
            column=reason_code_column,
            value=reason_code,
        )

        # Fixed: was comparing against lowercase "keep", which could
        # never match the uppercase-only currency_action validated
        # above -- so this fill never applied.
        if currency_action == "KEEP" and idx in mismatch_row_indices:
            for col in range(1, ws.max_column + 1):
                ws.cell(row=current_row, column=col).fill = (
                    CURRENCY_MISMATCH_HIGHLIGHT_FILL
                )

        sheet_name = ws.title
        row_number = current_row
        for field in MANDATORY_FIELDS:
            if field not in technical_columns:
                validation_errors.append({
                    "sheet": sheet_name,
                    "row": row_number,
                    "field_label": field,
                    "value": None,
                })
            else:
                cell_value = ws.cell(
                    row=current_row,
                    column=technical_columns[field]
                ).value
                if cell_value is None or (isinstance(cell_value, str) and cell_value.strip() == ""):
                    validation_errors.append({
                        "sheet": sheet_name,
                        "row": row_number,
                        "field_label": field,
                        "value": cell_value,
                    })

        current_row += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    if currency_mismatches:
        dump_rows = len(mismatch_row_indices) if currency_action == "DELETE" else 0
        currency_review = {
            # Fixed: was comparing against lowercase "keep" too, so
            # this always fell through to "deleted" even on a KEEP run.
            "status": "kept" if currency_action == "KEEP" else "deleted",
            "action": currency_action,
            "mismatch_count": len(currency_mismatches),
            "dump_rows": dump_rows,
            "retained_rows": len(df) - dump_rows,
            "mismatches": currency_mismatches,
        }

        if currency_action == "DELETE":
            currency_review["dump_buffer"] = build_currency_mismatch_dump(
                df, mismatch_row_indices
            )

        output.currency_review = currency_review

    return output, validation_errors