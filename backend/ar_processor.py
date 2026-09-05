# # ar_processor.py

# import io
# import datetime

# import pandas as pd
# import openpyxl
# from reference_mappings import load_but_mapping, map_business_partner

# # ... (existing constants and helper functions remain unchanged) ...

# COMPANY_CODE_MAPPING = {
#     "US01": "1000",
#     "US06": "1001",
#     "CA01": "1200",
# }

# REASON_CODE_MAPPING = {
#     "DIC": "048",
#     "FRW": "031",
#     "PEC": "021",
#     "PRC": "024",
#     "SSC": "036",
#     "UDC": "001",
#     "UPC": "011",
# }

# PAYMENT_TERMS_MAPPING = {
#     "001": "P210",
#     "003": "Z200",
#     "004": "P215",
#     "014": "P220",
#     "015": "Z251",
#     "016": "Z291",
#     "017": "Z261",
#     "018": "Z245",
#     "019": "Z230",
#     "020": "Z231",
#     "021": "Z232",
#     "022": "Z246",
#     "023": "Z233",
#     "024": "Z260",
#     "025": "Z305",
#     "026": "NT12",
#     "027": "Z160",
#     "029": "Z262",
#     "030": "Z276",
#     "035": "Z290",
#     "036": "Z130",
#     "038": "P030",
#     "039": "P230",
#     "040": "NT30",
#     "041": "NT60",
#     "042": "NT90",
#     "043": "NT45",
#     "044": "NT75",
#     "045": "NT15",
#     "046": "P025",
#     "048": "NT60",
#     "050": "Z400",
#     "052": "Z132",
#     "056": "Z216",
#     "058": "Z265",
#     "059": "Z263",
#     "060": "Z262",
#     "061": "Z264",
#     "062": "Z247",
#     "063": "Z161",
#     "064": "Z330",
#     "065": "Z146",
#     "070": "P260",
#     "072": "P225",
#     "073": "Z163",
#     "075": "Z505",
#     "091": "NTLC",
#     "094": "Z346",
#     "097": "Z164",
#     "100": "Z167",
#     "107": "Z316",
#     "109": "Z225",
#     "111": "Z234",
#     "112": "Z235",
#     "114": "P190",
#     "115": "P160",
#     "117": "P101",
#     "118": "Z162",
#     "119": "Z212",
#     "122": "Z131",
#     "129": "NT10",
#     "138": "Z165",
#     "139": "Z176",
#     "141": "E225",
#     "400": "Z166",
#     "401": "NT60",
#     "402": "NT10",
#     "403": "NT00",
#     "441": "NT65",
#     "442": "NT90",
#     "443": "NT45",
#     "444": "NT30",
#     "445": "NT75",
#     "33": "Z131",
# }

# def get_s4_payment_terms(ecc_payment_term):
#     """
#     Look up S/4 Payment Terms from ECC Payment Terms.

#     Leading zeroes are ignored, so values such as 033 and 33
#     are treated as the same ECC payment-term code.
#     """

#     # if ecc_payment_term is None or pd.isna(ecc_payment_term):
#     #     return ""
#     if ecc_payment_term is None or pd.isna(ecc_payment_term):
#         return "No payment terms in ECC"

#     payment_term = str(ecc_payment_term).strip().upper()

#     # Excel/Pandas may read numeric codes as 33.0.
#     if payment_term.endswith(".0") and payment_term[:-2].isdigit():
#         payment_term = payment_term[:-2]

#     normalized_term = payment_term.lstrip("0") or "0"

#     for ecc_code, s4_term in PAYMENT_TERMS_MAPPING.items():
#         normalized_code = ecc_code.lstrip("0") or "0"
#         if normalized_code == normalized_term:
#             return s4_term

#     return payment_term


# def clean_string(value):
#     if value is None or pd.isna(value):
#         return ""

#     if isinstance(value, float) and value.is_integer():
#         return str(int(value))

#     return str(value).strip()


# def clean_float(value, default=None):
#     if value is None or pd.isna(value):
#         return default

#     try:
#         return float(value)
#     except (ValueError, TypeError):
#         return default


# def clean_date(value):
#     if value is None or pd.isna(value):
#         return None

#     if isinstance(value, (datetime.date, datetime.datetime)):
#         return value.date() if isinstance(value, datetime.datetime) else value

#     value_string = str(value).strip()

#     if value_string in ("", "00/00/0000", "00.00.0000", "NaT"):
#         return None

#     for date_format in (
#         "%Y-%m-%d %H:%M:%S",
#         "%Y-%m-%d",
#         "%m/%d/%Y",
#         "%d/%m/%Y",
#         "%d.%m.%Y",
#         "%Y%m%d",
#     ):
#         try:
#             return datetime.datetime.strptime(
#                 value_string, date_format
#             ).date()
#         except ValueError:
#             continue

#     return value


# def get_s4_company_code(ecc_company_code):
#     return COMPANY_CODE_MAPPING.get(
#         clean_string(ecc_company_code).upper(),
#         "",
#     )


# def get_reason_code(reason_code):
#     return REASON_CODE_MAPPING.get(
#         clean_string(reason_code).upper(),
#         "",
#     )


# def normalize_amount(amount, debit_credit_indicator):
#     """
#     S -> positive
#     H -> negative

#     Positive values are written normally (500), not as '+500'.
#     """
#     amount = clean_float(amount)

#     if amount is None:
#         return None

#     amount = abs(amount)
#     indicator = clean_string(debit_credit_indicator).upper()

#     if indicator == "S":
#         return amount

#     if indicator == "H":
#         return -amount

#     return amount


# def get_reference_value(reference):
#     reference = clean_string(reference)
#     return reference if reference else "No reference in ECC"


# def get_document_type_mappings(
#     document_type,
#     assignment,
#     text,
#     reference,
#     document_number,
# ):
#     document_type = clean_string(document_type).upper()
#     assignment = clean_string(assignment)
#     text = clean_string(text)
#     reference = get_reference_value(reference)
#     document_number = clean_string(document_number)

#     # RV:
#     # Assignment -> Reference Document Number
#     # Reference  -> Assignment Number
#     # if document_type == "RV":
#     #     return {
#     #         "reference_document_number": assignment,
#     #         "assignment": reference,
#     #     }
#     if document_type == "RV":
#         return {
#             "reference_document_number": assignment if assignment else "No reference in ECC",
#             "assignment": reference,
#         }

#     # DZ:
#     # Reference -> Reference Document Number
#     # Text      -> Assignment Number
#     if document_type == "DZ":
#         return {
#             "reference_document_number": reference,
#             "assignment": text,
#         }

#     # All other document types:
#     # Document Number -> Reference Document Number
#     # Assignment      -> Assignment Number
#     return {
#         "reference_document_number": document_number,
#         "assignment": assignment,
#     }


# class RegistryMismatchError(ValueError):
#     pass

# # Add a list of technical field names that must be non-empty for each row
# MANDATORY_FIELDS = [
#     "BUKRS",   # Company Code
#     "KUNNR",   # Customer
#     "BLART",   # Document Type
#     "BLDAT",   # Document Date
#     "WAERS",   # Currency
#     "WRBTR",   # Amount
#     "MWSKZ",   # Tax Code
#     "XBLNR",   # Reference Document Number
# ]


# REQUIRED_AR_COLUMNS = [
#     "Company Code",
#     "Customer",
#     "Assignment",
#     "Document Number",
#     "Document Date",
#     "Currency",
#     "Reference",
#     "Document Type",
#     "Debit/Credit Ind.",
#     "Amount",
# ]




# def process_ar_registry(
#     registry_file,
#     template_path="templates/Merged File all DOC Types.xlsx",
#     but_path="reference_data/but0id_qs4_500.xlsx",
# ):
#     """
#     Processes the ECC Accounts Receivable registry and populates
#     the S/4 migration template. Returns (output_buffer, validation_errors).
#     """
#     df = pd.read_excel(registry_file)

#     if df.empty:
#         raise RegistryMismatchError(
#             "The uploaded AR registry is empty."
#         )

#     missing_columns = [
#         column for column in REQUIRED_AR_COLUMNS if column not in df.columns
#     ]
#     if missing_columns:
#         raise RegistryMismatchError(
#             "The uploaded file does not contain the required AR "
#             f"column(s): {', '.join(missing_columns)}."
#         )

#     # ---------------------------------------------------------
#     # Customer -> Business Partner mapping
#     # ---------------------------------------------------------

#     customer_but_mapping = load_but_mapping(
#         but_path,
#         id_type="DAP"
#     )

#     wb = openpyxl.load_workbook(template_path)

#     # Prefer a customer open-item sheet if the template contains one.
#     if "Customer Open Items" in wb.sheetnames:
#         ws = wb["Customer Open Items"]
#     else:
#         ws = wb[wb.sheetnames[0]]

#     # Technical target field identifiers are normally stored in Row 5.
#     technical_columns = {}
#     for col in range(1, ws.max_column + 1):
#         value = clean_string(ws.cell(row=5, column=col).value)
#         if value:
#             technical_columns[value] = col

#     # ---------------------------------------------------------
#     # Reason Code
#     # Fixed target column in the AR template
#     # BL = Column 64
#     # ---------------------------------------------------------

#     reason_code_column = 64

#     # Fallback: some templates have technical headers in Row 1.
#     if not technical_columns:
#         for col in range(1, ws.max_column + 1):
#             value = clean_string(ws.cell(row=1, column=col).value)
#             if value:
#                 technical_columns[value] = col

#     data_start_row = 9

#     # Clear existing example data (preserve formatting)
#     for row in range(data_start_row, ws.max_row + 1):
#         for col in range(1, ws.max_column + 1):
#             ws.cell(row=row, column=col).value = None

#     # # Create a new sheet for Canada data, copying the header and formatting
#     # canada_ws = copy_sheet_headers_and_formatting(ws, wb, "Canada Open Items")
    
#     # # Clear any existing data rows in the Canada sheet
#     # for row in range(data_start_row, canada_ws.max_row + 1):
#     #     for col in range(1, canada_ws.max_column + 1):
#     #         canada_ws.cell(row=row, column=col).value = None

#     current_row = data_start_row
#     validation_errors = []   # list of dicts: sheet, row, field_label

#     for idx, source_row in df.iterrows():
#         ecc_company_code = clean_string(source_row.get("Company Code"))
#         s4_company_code = get_s4_company_code(ecc_company_code)

#         original_document_type = clean_string(
#             source_row.get("Document Type")
#         ).upper()

#         doc_type_mappings = get_document_type_mappings(
#             document_type=original_document_type,
#             assignment=source_row.get("Assignment"),
#             text=source_row.get("Text"),
#             reference=source_row.get("Reference"),
#             document_number=source_row.get("Document Number"),
#         )

#         amount = normalize_amount(
#             source_row.get("Amount"),
#             source_row.get("Debit/Credit Ind."),
#         )

#         if s4_company_code in ("1000", "1001"):
#             tax_code = "I0"
#         elif s4_company_code == "1200":
#             tax_code = "Z0"
#         else:
#             tax_code = ""

#         # Get the document number from the registry (Column I) to map to XREF1
#         document_number = clean_string(source_row.get("Document Number"))

#         mapped_values = {
#             "BUKRS": s4_company_code,
#             "XBLNR": doc_type_mappings["reference_document_number"],
#             "KUNNR": map_business_partner(
#                     customer_but_mapping,
#                     source_row.get("Customer")
#                 ),
#             "GKONT": "9999900000",          # hardcoded clearing account
#             "BLART": "UE",                  # target document type fixed
#             "BLDAT": clean_date(source_row.get("Document Date")),
#             "SGTXT": clean_string(source_row.get("Text")),
#             "WAERS": clean_string(source_row.get("Currency")),
#             "WRBTR": amount,
#             "MWSKZ": tax_code,
#             "ZTERM": get_s4_payment_terms(
#                     source_row.get("Terms of Payment")
#                 ),
#             "ZFBDT": clean_date(source_row.get("Baseline Payment Dte")),
#             "ZBD1T": clean_string(source_row.get("Days 1")),
#             "ZBD1P": clean_float(source_row.get("Disc.percent 1")),
#             "ZBD2T": clean_string(source_row.get("Days 2")),
#             "ZBD2P": clean_float(source_row.get("Disc.percent 2")),
#             "ZBD3T": clean_string(source_row.get("Days Net")),
#             # "SKFBT": clean_float(source_row.get("Discount base")),
#             "SKFBT": normalize_amount(
#                         source_row.get("Discount base"),
#                         source_row.get("Debit/Credit Ind.")
#                     ),
#             # "KKBER": clean_string(source_row.get("Credit Control Area")),
#             "KKBER": s4_company_code,
#             "ZUONR": doc_type_mappings["assignment"],
#             "RSTGR": get_reason_code(source_row.get("Reason code")),
#             # Map the document number from the source to XREF1 (Reference Key 1)
#             "XREF1": document_number,
#         }

#         # Write values to the main Customer Open Items sheet (all data)
#         for tech_field, value in mapped_values.items():
#             if tech_field in technical_columns:
#                 ws.cell(
#                     row=current_row,
#                     column=technical_columns[tech_field],
#                     value=value,
#                 )

#         # ---------------------------------------------------------
#         # Reason Code
#         # Source: Reason code
#         # Target: BL (Column 64)
#         # ---------------------------------------------------------

#         reason_code = get_reason_code(
#             source_row.get("Reason code")
#         )

#         ws.cell(
#             row=current_row,
#             column=reason_code_column,
#             value=reason_code,
#         )

#         # --- Validation: check mandatory fields for main sheet ---
#         sheet_name = ws.title
#         row_number = current_row
#         for field in MANDATORY_FIELDS:
#             if field not in technical_columns:
#                 validation_errors.append({
#                     "sheet": sheet_name,
#                     "row": row_number,
#                     "field_label": field,
#                     "value": None,
#                 })
#             else:
#                 cell_value = ws.cell(
#                     row=current_row,
#                     column=technical_columns[field]
#                 ).value
#                 if cell_value is None or (isinstance(cell_value, str) and cell_value.strip() == ""):
#                     validation_errors.append({
#                         "sheet": sheet_name,
#                         "row": row_number,
#                         "field_label": field,
#                         "value": cell_value,
#                     })

#         current_row += 1

#     output = io.BytesIO()
#     wb.save(output)
#     output.seek(0)
#     return output, validation_errors

# ar_processor.py

import io
import datetime

import pandas as pd
import openpyxl
from openpyxl.styles import PatternFill
from reference_mappings import load_but_mapping, map_business_partner

# ... (existing constants and helper functions remain unchanged) ...

COMPANY_CODE_MAPPING = {
    "US01": "1000",
    "US06": "1001",
    "CA01": "1200",
}

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
    with the chosen `currency_action` ("keep" or "delete") once the
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
        s4_company_code = get_s4_company_code(ecc_company_code)
        currency = clean_string(source_row.get("Currency")).upper()

        if is_currency_mismatch(s4_company_code, currency):
            mismatches.append({
                # +2 accounts for the 1-based Excel row and the header row
                "row": int(idx) + 2,
                "company_code": ecc_company_code,
                "s4_company_code": s4_company_code,
                "currency": currency,
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

PAYMENT_TERMS_MAPPING = {
    "001": "P210",
    "003": "Z200",
    "004": "P215",
    "014": "P220",
    "015": "Z251",
    "016": "Z291",
    "017": "Z261",
    "018": "Z245",
    "019": "Z230",
    "020": "Z231",
    "021": "Z232",
    "022": "Z246",
    "023": "Z233",
    "024": "Z260",
    "025": "Z305",
    "026": "NT12",
    "027": "Z160",
    "029": "Z262",
    "030": "Z276",
    "035": "Z290",
    "036": "Z130",
    "038": "P030",
    "039": "P230",
    "040": "NT30",
    "041": "NT60",
    "042": "NT90",
    "043": "NT45",
    "044": "NT75",
    "045": "NT15",
    "046": "P025",
    "048": "NT60",
    "050": "Z400",
    "052": "Z132",
    "056": "Z216",
    "058": "Z265",
    "059": "Z263",
    "060": "Z262",
    "061": "Z264",
    "062": "Z247",
    "063": "Z161",
    "064": "Z330",
    "065": "Z146",
    "070": "P260",
    "072": "P225",
    "073": "Z163",
    "075": "Z505",
    "091": "NTLC",
    "094": "Z346",
    "097": "Z164",
    "100": "Z167",
    "107": "Z316",
    "109": "Z225",
    "111": "Z234",
    "112": "Z235",
    "114": "P190",
    "115": "P160",
    "117": "P101",
    "118": "Z162",
    "119": "Z212",
    "122": "Z131",
    "129": "NT10",
    "138": "Z165",
    "139": "Z176",
    "141": "E225",
    "400": "Z166",
    "401": "NT60",
    "402": "NT10",
    "403": "NT00",
    "441": "NT65",
    "442": "NT90",
    "443": "NT45",
    "444": "NT30",
    "445": "NT75",
    "33": "Z131",
}

def get_s4_payment_terms(ecc_payment_term):
    """
    Look up S/4 Payment Terms from ECC Payment Terms.

    Leading zeroes are ignored, so values such as 033 and 33
    are treated as the same ECC payment-term code.
    """

    # if ecc_payment_term is None or pd.isna(ecc_payment_term):
    #     return ""
    if ecc_payment_term is None or pd.isna(ecc_payment_term):
        return "No payment terms in ECC"

    payment_term = str(ecc_payment_term).strip().upper()

    # Excel/Pandas may read numeric codes as 33.0.
    if payment_term.endswith(".0") and payment_term[:-2].isdigit():
        payment_term = payment_term[:-2]

    normalized_term = payment_term.lstrip("0") or "0"

    for ecc_code, s4_term in PAYMENT_TERMS_MAPPING.items():
        normalized_code = ecc_code.lstrip("0") or "0"
        if normalized_code == normalized_term:
            return s4_term

    return payment_term


def clean_string(value):
    if value is None or pd.isna(value):
        return ""

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value).strip()


def clean_float(value, default=None):
    if value is None or pd.isna(value):
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def clean_date(value):
    if value is None or pd.isna(value):
        return None

    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.date() if isinstance(value, datetime.datetime) else value

    value_string = str(value).strip()

    if value_string in ("", "00/00/0000", "00.00.0000", "NaT"):
        return None

    for date_format in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%Y%m%d",
    ):
        try:
            return datetime.datetime.strptime(
                value_string, date_format
            ).date()
        except ValueError:
            continue

    return value


def get_s4_company_code(ecc_company_code):
    return COMPANY_CODE_MAPPING.get(
        clean_string(ecc_company_code).upper(),
        "",
    )


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
    # if document_type == "RV":
    #     return {
    #         "reference_document_number": assignment,
    #         "assignment": reference,
    #     }
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
    but_path="reference_data/but0id_qs4_500.xlsx",
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
      - "keep": mismatched rows are migrated as normal, but highlighted
        in red in the output workbook.
      - "delete": mismatched rows are excluded from the output workbook
        and instead written to a separate "dump" workbook, returned via
        `output.currency_review["dump_buffer"]`.
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

    if currency_action not in (None, "KEEP", "DELETE"):
        raise ValueError(
            f"Unrecognized currency_action: {currency_action!r}. "
            "Expected 'KEEP' or 'DELETE'."
        )

    # ---------------------------------------------------------
    # Customer -> Business Partner mapping
    # ---------------------------------------------------------

    customer_but_mapping = load_but_mapping(
        but_path,
        id_type="DAP"
    )

    wb = openpyxl.load_workbook(template_path)

    # Prefer a customer open-item sheet if the template contains one.
    if "Customer Open Items" in wb.sheetnames:
        ws = wb["Customer Open Items"]
    else:
        ws = wb[wb.sheetnames[0]]

    # Technical target field identifiers are normally stored in Row 5.
    technical_columns = {}
    for col in range(1, ws.max_column + 1):
        value = clean_string(ws.cell(row=5, column=col).value)
        if value:
            technical_columns[value] = col

    # ---------------------------------------------------------
    # Reason Code
    # Fixed target column in the AR template
    # BL = Column 64
    # ---------------------------------------------------------

    reason_code_column = 64

    # Fallback: some templates have technical headers in Row 1.
    if not technical_columns:
        for col in range(1, ws.max_column + 1):
            value = clean_string(ws.cell(row=1, column=col).value)
            if value:
                technical_columns[value] = col

    data_start_row = 9

    # Clear existing example data (preserve formatting)
    for row in range(data_start_row, ws.max_row + 1):
        for col in range(1, ws.max_column + 1):
            ws.cell(row=row, column=col).value = None

    # # Create a new sheet for Canada data, copying the header and formatting
    # canada_ws = copy_sheet_headers_and_formatting(ws, wb, "Canada Open Items")
    
    # # Clear any existing data rows in the Canada sheet
    # for row in range(data_start_row, canada_ws.max_row + 1):
    #     for col in range(1, canada_ws.max_column + 1):
    #         canada_ws.cell(row=row, column=col).value = None

    current_row = data_start_row
    validation_errors = []   # list of dicts: sheet, row, field_label

    for idx, source_row in df.iterrows():
        # Rows flagged as a company code / currency mismatch and marked
        # for deletion are excluded from the migration output entirely —
        # they'll be captured in the separate dump workbook below.
        if currency_action == "DELETE" and idx in mismatch_row_indices:
            continue

        ecc_company_code = clean_string(source_row.get("Company Code"))
        s4_company_code = get_s4_company_code(ecc_company_code)

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

        # Get the document number from the registry (Column I) to map to XREF1
        document_number = clean_string(source_row.get("Document Number"))

        mapped_values = {
            "BUKRS": s4_company_code,
            "XBLNR": doc_type_mappings["reference_document_number"],
            "KUNNR": map_business_partner(
                    customer_but_mapping,
                    source_row.get("Customer")
                ),
            "GKONT": "9999900000",          # hardcoded clearing account
            "BLART": "UE",                  # target document type fixed
            "BLDAT": clean_date(source_row.get("Document Date")),
            "SGTXT": clean_string(source_row.get("Text")),
            "WAERS": clean_string(source_row.get("Currency")),
            "WRBTR": amount,
            "MWSKZ": tax_code,
            "ZTERM": get_s4_payment_terms(
                    source_row.get("Terms of Payment")
                ),
            "ZFBDT": clean_date(source_row.get("Baseline Payment Dte")),
            "ZBD1T": clean_string(source_row.get("Days 1")),
            "ZBD1P": clean_float(source_row.get("Disc.percent 1")),
            "ZBD2T": clean_string(source_row.get("Days 2")),
            "ZBD2P": clean_float(source_row.get("Disc.percent 2")),
            "ZBD3T": clean_string(source_row.get("Days Net")),
            # "SKFBT": clean_float(source_row.get("Discount base")),
            "SKFBT": normalize_amount(
                        source_row.get("Discount base"),
                        source_row.get("Debit/Credit Ind.")
                    ),
            # "KKBER": clean_string(source_row.get("Credit Control Area")),
            "KKBER": s4_company_code,
            "ZUONR": doc_type_mappings["assignment"],
            "RSTGR": get_reason_code(source_row.get("Reason code")),
            # Map the document number from the source to XREF1 (Reference Key 1)
            "XREF1": document_number,
        }

        # Write values to the main Customer Open Items sheet (all data)
        for tech_field, value in mapped_values.items():
            if tech_field in technical_columns:
                ws.cell(
                    row=current_row,
                    column=technical_columns[tech_field],
                    value=value,
                )

        # ---------------------------------------------------------
        # Reason Code
        # Source: Reason code
        # Target: BL (Column 64)
        # ---------------------------------------------------------

        reason_code = get_reason_code(
            source_row.get("Reason code")
        )

        ws.cell(
            row=current_row,
            column=reason_code_column,
            value=reason_code,
        )

        # ---------------------------------------------------------
        # Highlight rows kept despite a company code / currency
        # mismatch so they're easy to spot for manual review.
        # ---------------------------------------------------------

        if currency_action == "keep" and idx in mismatch_row_indices:
            for col in range(1, ws.max_column + 1):
                ws.cell(row=current_row, column=col).fill = (
                    CURRENCY_MISMATCH_HIGHLIGHT_FILL
                )

        # --- Validation: check mandatory fields for main sheet ---
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
            "status": "kept" if currency_action == "keep" else "deleted",
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