# # ar_processor.py

# import io
# import datetime

# import pandas as pd
# import openpyxl

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
# ):
#     document_type = clean_string(document_type).upper()
#     assignment = clean_string(assignment)
#     text = clean_string(text)
#     reference = get_reference_value(reference)

#     if document_type == "RV":
#         return {
#             "reference_document_number": assignment,
#             "assignment": "",
#         }

#     if document_type == "DZ":
#         return {
#             "reference_document_number": reference,
#             "assignment": text,
#         }

#     return {
#         "reference_document_number": assignment,
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

# class RegistryMismatchError(ValueError):
#     pass

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
#         )

#         amount = normalize_amount(
#             source_row.get("Amount"),
#             source_row.get("Debit/Credit Ind."),
#         )

#         if s4_company_code in ("1000", "1001"):
#             tax_code = "I0"
#         elif s4_company_code == "1200":
#             tax_code = "C0"
#         else:
#             tax_code = ""
#         #30 aug (XBLNR from source) to map to XREF1
#         document_number = clean_string(source_row.get("Document Number"))

#         mapped_values = {
#             "BUKRS": s4_company_code,
#             "XBLNR": doc_type_mappings["reference_document_number"],
#             "KUNNR": clean_string(source_row.get("Customer")),
#             "GKONT": "9999900000",          # hardcoded clearing account
#             "BLART": "UE",                  # target document type fixed
#             "BLDAT": clean_date(source_row.get("Document Date")),
#             "SGTXT": clean_string(source_row.get("Text")),
#             "WAERS": clean_string(source_row.get("Currency")),
#             "WRBTR": amount,
#             "MWSKZ": tax_code,
#             "ZTERM": clean_string(source_row.get("Terms of Payment")),
#             "ZFBDT": clean_date(source_row.get("Baseline Payment Dte")),
#             "ZBD1T": clean_string(source_row.get("Days 1")),
#             "ZBD1P": clean_float(source_row.get("Disc.percent 1")),
#             "ZBD2T": clean_string(source_row.get("Days 2")),
#             "ZBD2P": clean_float(source_row.get("Disc.percent 2")),
#             "ZBD3T": clean_string(source_row.get("Days Net")),
#             "SKFBT": clean_float(source_row.get("Discount base")),
#             "KKBER": clean_string(source_row.get("Credit Control Area")),
#             "ZUONR": doc_type_mappings["assignment"],
#             "RSTGR": get_reason_code(source_row.get("Reason code")),
#             "XREF1": document_number,

#         }

#         # Write values to the template
#         for tech_field, value in mapped_values.items():
#             if tech_field in technical_columns:
#                 ws.cell(
#                     row=current_row,
#                     column=technical_columns[tech_field],
#                     value=value,
#                 )

#         # --- Validation: check mandatory fields ---
#         sheet_name = ws.title
#         row_number = current_row
#         for field in MANDATORY_FIELDS:
#             # The field may not exist in technical_columns; if not, treat as missing.
#             if field not in technical_columns:
#                 # The field is missing in the template structure – log an error.
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
#                 # Check if value is empty or None
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
import copy

import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter

# ... (existing constants and helper functions remain unchanged) ...

COMPANY_CODE_MAPPING = {
    "US01": "1000",
    "US06": "1001",
    "CA01": "1200",
}

REASON_CODE_MAPPING = {
    "DIC": "048",
    "FRW": "031",
    "PEC": "021",
    "PRC": "024",
    "SSC": "036",
    "UDC": "001",
    "UPC": "011",
}


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
):
    document_type = clean_string(document_type).upper()
    assignment = clean_string(assignment)
    text = clean_string(text)
    reference = get_reference_value(reference)

    if document_type == "RV":
        return {
            "reference_document_number": assignment,
            "assignment": "",
        }

    if document_type == "DZ":
        return {
            "reference_document_number": reference,
            "assignment": text,
        }

    return {
        "reference_document_number": assignment,
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

class RegistryMismatchError(ValueError):
    pass

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


def copy_sheet_headers_and_formatting(source_ws, target_wb, target_sheet_name):
    """
    Copies the header rows (rows 1-8) and column formats from source_ws to a new sheet.
    """
    # Create a new sheet in the target workbook
    if target_sheet_name in target_wb.sheetnames:
        # If sheet already exists, remove it first
        std = target_wb[target_sheet_name]
        target_wb.remove(std)
    
    target_ws = target_wb.create_sheet(target_sheet_name)
    
    # Copy rows 1-8 (headers, technical info, formatting)
    for row in range(1, 9):  # rows 1-8
        for col in range(1, source_ws.max_column + 1):
            source_cell = source_ws.cell(row=row, column=col)
            target_cell = target_ws.cell(row=row, column=col)
            
            # Copy value
            target_cell.value = source_cell.value
            
            # Copy formatting (font, fill, border, etc.)
            if source_cell.has_style:
                target_cell.font = copy.copy(source_cell.font)
                target_cell.border = copy.copy(source_cell.border)
                target_cell.fill = copy.copy(source_cell.fill)
                target_cell.number_format = source_cell.number_format
                target_cell.protection = copy.copy(source_cell.protection)
                target_cell.alignment = copy.copy(source_cell.alignment)
    
    # Copy column widths
    for col in range(1, source_ws.max_column + 1):
        col_letter = get_column_letter(col)
        if source_ws.column_dimensions[col_letter].width:
            target_ws.column_dimensions[col_letter].width = source_ws.column_dimensions[col_letter].width
    
    return target_ws


def process_ar_registry(
    registry_file,
    template_path="templates/Merged File all DOC Types.xlsx",
):
    """
    Processes the ECC Accounts Receivable registry and populates
    the S/4 migration template. Returns (output_buffer, validation_errors).
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

    # Create a new sheet for Canada data, copying the header and formatting
    canada_ws = copy_sheet_headers_and_formatting(ws, wb, "Canada Open Items")
    
    # Clear any existing data rows in the Canada sheet
    for row in range(data_start_row, canada_ws.max_row + 1):
        for col in range(1, canada_ws.max_column + 1):
            canada_ws.cell(row=row, column=col).value = None

    current_row = data_start_row
    canada_current_row = data_start_row
    validation_errors = []   # list of dicts: sheet, row, field_label

    for idx, source_row in df.iterrows():
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
        )

        amount = normalize_amount(
            source_row.get("Amount"),
            source_row.get("Debit/Credit Ind."),
        )

        if s4_company_code in ("1000", "1001"):
            tax_code = "I0"
        elif s4_company_code == "1200":
            tax_code = "C0"
        else:
            tax_code = ""

        # Get the document number (XBLNR from source) to map to XREF1
        document_number = clean_string(source_row.get("Document Number"))

        mapped_values = {
            "BUKRS": s4_company_code,
            "XBLNR": doc_type_mappings["reference_document_number"],
            "KUNNR": clean_string(source_row.get("Customer")),
            "GKONT": "9999900000",          # hardcoded clearing account
            "BLART": "UE",                  # target document type fixed
            "BLDAT": clean_date(source_row.get("Document Date")),
            "SGTXT": clean_string(source_row.get("Text")),
            "WAERS": clean_string(source_row.get("Currency")),
            "WRBTR": amount,
            "MWSKZ": tax_code,
            "ZTERM": clean_string(source_row.get("Terms of Payment")),
            "ZFBDT": clean_date(source_row.get("Baseline Payment Dte")),
            "ZBD1T": clean_string(source_row.get("Days 1")),
            "ZBD1P": clean_float(source_row.get("Disc.percent 1")),
            "ZBD2T": clean_string(source_row.get("Days 2")),
            "ZBD2P": clean_float(source_row.get("Disc.percent 2")),
            "ZBD3T": clean_string(source_row.get("Days Net")),
            "SKFBT": clean_float(source_row.get("Discount base")),
            "KKBER": clean_string(source_row.get("Credit Control Area")),
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

        # --- Write to Canada Open Items sheet if company code is CA01 ---
        if ecc_company_code.upper() == "CA01":
            for tech_field, value in mapped_values.items():
                if tech_field in technical_columns:
                    canada_ws.cell(
                        row=canada_current_row,
                        column=technical_columns[tech_field],
                        value=value,
                    )
            
            # --- Validation for Canada sheet ---
            canada_sheet_name = canada_ws.title
            canada_row_number = canada_current_row
            for field in MANDATORY_FIELDS:
                if field not in technical_columns:
                    validation_errors.append({
                        "sheet": canada_sheet_name,
                        "row": canada_row_number,
                        "field_label": field,
                        "value": None,
                    })
                else:
                    cell_value = canada_ws.cell(
                        row=canada_current_row,
                        column=technical_columns[field]
                    ).value
                    if cell_value is None or (isinstance(cell_value, str) and cell_value.strip() == ""):
                        validation_errors.append({
                            "sheet": canada_sheet_name,
                            "row": canada_row_number,
                            "field_label": field,
                            "value": cell_value,
                        })
            
            canada_current_row += 1

        current_row += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output, validation_errors