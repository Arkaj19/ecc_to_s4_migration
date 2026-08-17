import io
import pandas as pd
import openpyxl
import datetime


def clean_string(val):
    """
    Convert a value to a clean string.

    Prevents values such as 1.0 from being written when the
    source Excel contains an integer-like float.
    """
    if pd.isna(val) or val is None:
        return ""

    if isinstance(val, float) and val.is_integer():
        return str(int(val))

    return str(val).strip()


def clean_float(val, default=None):
    """
    Convert a value to float.

    Blank / NaN values return the supplied default.
    """
    if pd.isna(val) or val is None:
        return default

    try:
        return float(val)
    except (ValueError, TypeError):
        return val


def process_credit_registry(
    registry_file,
    template_path="templates/credit_load_template.xlsx"
) -> io.BytesIO:
    """
    Processes the Credit Registry spreadsheet and populates:

        1. Profile - Credit MD for Cust.
        2. Segment - Credit MD for Cust.

    Registry -> Credit Profile mapping:

        KUNNR              -> CustomerNumber
        RUN_ID             -> Sequential
        OWN_RATING         -> Blank
        CHECK_RULE         -> "01"
        LIMIT_RULE         -> "SAP_ALL"
        RATING_VAL_DATE    -> Blank
        RISK_CLASS         -> Risk Cat
        CREDIT_GROUP       -> Credit rep.group

    Registry -> Credit Segment mapping:

        KUNNR              -> CustomerNumber
        RUN_ID             -> Sequential
        CREDIT_SEGMENT     -> "1000"
        CREDIT_LIMIT       -> Credit Limit

    Data is written starting from row 9.
    """

    # ---------------------------------------------------------
    # 1. Read Registry
    # ---------------------------------------------------------

    df_raw = pd.read_excel(registry_file)

    # ---------------------------------------------------------
    # 2. Load Credit Data Load template
    # ---------------------------------------------------------

    wb = openpyxl.load_workbook(template_path)

    sheets_to_fill = [
        "Profile - Credit MD for Cust.",
        "Segment - Credit MD for Cust."
    ]

    # ---------------------------------------------------------
    # 3. Prepare mapped records
    # ---------------------------------------------------------

    processed_records = []

    run_id = 1

    for _, row in df_raw.iterrows():

        customer_number = clean_string(
            row.get("CustomerNumber")
        )

        # Skip rows where CustomerNumber is blank
        if not customer_number:
            continue

        record = {
            "customer_number": customer_number,
            "run_id": str(run_id),

            # Profile fields
            "risk_class": clean_string(
                row.get("Risk Cat")
            ),

            "credit_group": clean_string(
                row.get("Credit rep.group")
            ),

            # Segment fields
            "credit_limit": clean_float(
                row.get("Credit Limit")
            )
        }

        processed_records.append(record)

        run_id += 1

    # ---------------------------------------------------------
    # 4. Populate both sheets
    # ---------------------------------------------------------

    for sheet_name in sheets_to_fill:

        if sheet_name not in wb.sheetnames:
            print(
                f"Sheet {sheet_name} not found in template, skipping."
            )
            continue

        ws = wb[sheet_name]

        # -----------------------------------------------------
        # Technical field names are on Row 5
        # -----------------------------------------------------

        tech_cols = [
            clean_string(
                ws.cell(row=5, column=col).value
            )
            for col in range(1, ws.max_column + 1)
        ]

        # Build:
        # technical_field_name -> Excel column number
        col_to_idx = {
            name: idx + 1
            for idx, name in enumerate(tech_cols)
            if name
        }

        # -----------------------------------------------------
        # Data starts from Row 9
        # -----------------------------------------------------

        current_row = 9

        for rec in processed_records:

            mapped_values = {}

            # =================================================
            # PROFILE SHEET
            # =================================================

            if sheet_name == "Profile - Credit MD for Cust.":

                mapped_values["KUNNR"] = rec["customer_number"]

                mapped_values["RUN_ID"] = rec["run_id"]

                # No mapping provided for OWN_RATING
                mapped_values["OWN_RATING"] = ""

                # Hardcoded for now
                mapped_values["CHECK_RULE"] = "01"

                # Hardcoded
                mapped_values["LIMIT_RULE"] = "SAP_ALL"

                # Blank as specified
                mapped_values["RATING_VAL_DATE"] = ""

                # Risk Cat from Registry
                mapped_values["RISK_CLASS"] = rec["risk_class"]

                # Credit rep.group must remain STRING
                mapped_values["CREDIT_GROUP"] = rec["credit_group"]

            # =================================================
            # SEGMENT SHEET
            # =================================================

            elif sheet_name == "Segment - Credit MD for Cust.":

                mapped_values["KUNNR"] = rec["customer_number"]

                mapped_values["RUN_ID"] = rec["run_id"]

                # Hardcoded for now
                mapped_values["CREDIT_SEGMENT"] = "1000"

                mapped_values["CREDIT_LIMIT"] = rec["credit_limit"]

                # Other fields are intentionally left blank
                # because no mapping was provided.

            # -------------------------------------------------
            # Write mapped values
            # -------------------------------------------------

            for col_name, value in mapped_values.items():

                if col_name in col_to_idx:

                    c_idx = col_to_idx[col_name]

                    ws.cell(
                        row=current_row,
                        column=c_idx,
                        value=value
                    )

            current_row += 1

    # ---------------------------------------------------------
    # 5. Save workbook to BytesIO
    # ---------------------------------------------------------

    out_buf = io.BytesIO()

    wb.save(out_buf)

    out_buf.seek(0)

    return out_buf