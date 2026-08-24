# backend/asset_processor.py

import io
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import datetime
import mappings
from validation_utils import extract_mandatory_fields, is_blank

# def clean_string(val):
#     if pd.isna(val) or val is None:
#         return ""
#     return str(val).strip()

def clean_string(val):
    if pd.isna(val) or val is None:
        return ""

    if isinstance(val, float) and val.is_integer():
        return str(int(val))

    return str(val).strip()

def clean_int(val, default=""):
    if pd.isna(val) or val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return str(val).strip()

# def clean_float(val, default=None):
#     if pd.isna(val) or val is None:
#         return default
#     try:
#         return float(val)
#     except (ValueError, TypeError):
#         return val

def clean_float(val, default=None):
    """
    Convert a value to float, including SAP/Excel "accounting format"
    text such as "5,114.43-" or "(5,114.43)" for negative numbers.

    Registry exports commonly render negatives with a trailing minus sign
    and/or thousands separators rather than a leading minus. Python's
    float() can't parse either of those directly — float("5,114.43-")
    raises ValueError — so without this, such values silently fell
    through to the except branch and were returned completely unchanged:
    the literal text "5,114.43-" got written straight into the output
    cell instead of the number -5114.43, which is why the minus sign
    still showed up trailing in the generated file regardless of the
    template's own number format.
    """
    if pd.isna(val) or val is None:
        return default

    if isinstance(val, (int, float)):
        return float(val)

    text = str(val).strip()
    if not text:
        return default

    negative = False

    if text.endswith('-'):
        negative = True
        text = text[:-1].strip()
    elif text.startswith('(') and text.endswith(')'):
        negative = True
        text = text[1:-1].strip()

    text = text.replace(',', '')

    try:
        num = float(text)
        return -num if negative else num
    except (ValueError, TypeError):
        return val

class RegistryMismatchError(ValueError):
    """Raised when the uploaded file doesn't look like an Asset registry."""
    pass


# Minimum set of columns an Asset registry must have for this processor to
# produce meaningful output. If these aren't present, every row would
# silently fail is_active() / mapping lookups and the output would come
# back "successful" but empty.
REQUIRED_ASSET_COLUMNS = ['CoCd', 'Asset', 'Deact.Date', 'Plnt', 'Location']


def validate_asset_registry(df):
    missing = [c for c in REQUIRED_ASSET_COLUMNS if c not in df.columns]
    if missing:
        raise RegistryMismatchError(
            "This file doesn't look like an Asset registry. "
            f"Missing expected column(s): {', '.join(missing)}. "
            "Make sure you selected the right file for the Assets process."
        )


def clean_date(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.date() if isinstance(val, datetime.datetime) else val
    val_str = str(val).strip()
    if val_str == "00/00/0000" or val_str == "00.00.0000" or val_str == "" or val_str == "NaT":
        return None
    
    # Try parsing different date formats
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%d.%m.%Y', '%Y%m%d'):
        try:
            return datetime.datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    return val





def process_asset_registry(registry_file, template_path="templates/assets_load_template.xlsx", custom_mappings=None) -> io.BytesIO:
    """
    Processes the ECC asset registry spreadsheet, filters active records, 
    maps fields to S/4 HANA, and writes them to the prebuilt Excel template sheets starting at Row 8.
    
    custom_mappings: dict containing:
        - 'cocd': dict
        - 'plant_loc': dict with key: (plant_val, location_str) and value: {"s4_plant": str, "s4_location": str}
        - 'cost_center': dict
    """
    if custom_mappings is None:
        custom_mappings = {}
        
    cocd_map = custom_mappings.get('cocd', {})
    plant_loc_map = custom_mappings.get('plant_loc', {})
    cost_center_map = custom_mappings.get('cost_center', {})
    
    # Helper translation functions
    def map_cocd(ecc_cocd):
        ecc_str = clean_string(ecc_cocd)
        if ecc_str in cocd_map:
            return cocd_map[ecc_str]
        return mappings.get_s4_company_code(ecc_cocd)
        
    def map_plant_loc(ecc_plant, ecc_loc):
        p_val = clean_int(ecc_plant)
        l_str = clean_string(ecc_loc).upper()
        if (p_val, l_str) in plant_loc_map:
            return plant_loc_map[(p_val, l_str)]
        return mappings.get_s4_plant_and_location(ecc_plant, ecc_loc)
        
    def map_cost_center(ecc_cc, ecc_plant, ecc_loc):
        cc_val = clean_int(ecc_cc)
        if cc_val in cost_center_map:
            return cost_center_map[cc_val]
        # Fallback to function
        return mappings.get_s4_cost_center(ecc_cc, ecc_plant, ecc_loc)

    # 1. Read registry file (excel)
    # Using openpyxl engine
    df_raw = pd.read_excel(registry_file)

    # Fail loudly if this isn't actually an Asset registry, instead of
    # silently filtering every row out and returning an empty "success".
    validate_asset_registry(df_raw)
    
    # 2. Filter records where Deact.Date is '00/00/0000' or empty or None
    # Let's inspect the active condition. Active records are those NOT deactivated.
    # So Deact.Date should be '00/00/0000', or nan, or empty.
    def is_active(row):
        deact_val = str(row.get('Deact.Date', '')).strip()
        # Pick only records whose Deact.Date is '00/00/0000' or '00.00.0000'
        return deact_val in ('00/00/0000', '00.00.0000')
        
    df_active = df_raw[df_raw.apply(is_active, axis=1)].copy()
    
    # 3. Load seeded assets_load_template
    wb = openpyxl.load_workbook(template_path)
    
    # List of sheets we need to fill
    sheets_to_fill = {
        'Master Details': 'S_KEY',
        'Allocations': 'S_ALLOCATIONS',
        'Origin': 'S_ORIGIN',
        'Depreciation Areas': 'S_DEPR',
        'Cumulative Values': 'S_CUM_VAL',
        'Posted Values': 'S_POST_VAL',
        'Posting Information': 'S_POSTINGINFORMATION',
        'Time-Dependent Data': 'S_TIMEDEPENDENTDATA',
        'Acct. Assignmt. for Investment': 'S_INVESTACCTASSIGNMN'
    }

    # Pre-generate mapped datasets for performance and simplicity
    processed_records = []
    
    for idx, row in df_active.iterrows():
        # Get basic properties
        ecc_cocd = row.get('CoCd')
        s4_cocd = map_cocd(ecc_cocd)
        
        ecc_asset = clean_string(row.get('Asset'))
        # print(ecc_asset)
        # Standard subnumber is 0
        s4_subnumber = "0"
        
        # Plant & Location
        ecc_plant = row.get('Plnt')
        ecc_location = row.get('Location')
        pl_mapped = map_plant_loc(ecc_plant, ecc_location)
        s4_plant = pl_mapped['s4_plant']
        s4_location = pl_mapped['s4_location']
        
        # Cost Center
        ecc_cc = row.get('Cost Ctr')
        s4_cost_center = map_cost_center(ecc_cc, ecc_plant, ecc_location)
        
        record = {
            'ecc_row': row,
            # +2: pandas index is 0-based and the registry's Row 1 is the
            # header, so the first data row (index 0) is Excel Row 2.
            'source_row': idx + 2,
            's4_cocd': s4_cocd,
            's4_asset': ecc_asset,
            's4_subnumber': s4_subnumber,
            's4_plant': s4_plant,
            's4_location': s4_location,
            's4_cost_center': s4_cost_center
        }
        processed_records.append(record)

    # 4. Map columns for each sheet and write
    validation_errors = []

    for sheet_name, tech_id in sheets_to_fill.items():
        if sheet_name not in wb.sheetnames:
            print(f"Sheet {sheet_name} not found in template, skipping.")
            continue
            
        ws = wb[sheet_name]
        
        # Find column technical identifiers on Row 5 (index 4 in openpyxl)
        # Note: openpyxl rows are 1-indexed. Let's read Row 5.
        tech_cols = [clean_string(ws.cell(row=5, column=col).value) for col in range(1, ws.max_column + 1)]
        
        # Build mapping index
        col_to_idx = {name: idx + 1 for idx, name in enumerate(tech_cols) if name}

        # Which technical fields this sheet marks mandatory (Row 8, '*').
        mandatory_fields = extract_mandatory_fields(ws, col_to_idx)
        
        # Write rows starting from row 9 (openpyxl Row 9 is index 9)
        current_row = 9
        
        for rec in processed_records:
            row_data = rec['ecc_row']
            
            # Map based on sheet name
            mapped_values = {}
            
            # Common fields
            mapped_values['BUKRS'] = rec['s4_cocd']
            
            if sheet_name in ['Master Details', 'Allocations', 'Origin', 'Depreciation Areas', 
                             'Cumulative Values', 'Posted Values', 'Posting Information', 
                             'Time-Dependent Data', 'Acct. Assignmt. for Investment']:
                mapped_values['ANLN1'] = rec['s4_asset']
                mapped_values['ANLN2'] = rec['s4_subnumber']
                
            if sheet_name == 'Master Details':
                mapped_values['ANLKL'] = clean_string(row_data.get('S4 asset class '))
                mapped_values['TXT50'] = clean_string(row_data.get('Description'))
                mapped_values['TXA50_MORE'] = clean_string(row_data.get('Description'))
                mapped_values['SERNR'] = clean_string(row_data.get('Serial no.'))
                mapped_values['INVNR'] = clean_string(row_data.get('Inventory number'))
                mapped_values['MAIN_DESCRIPT'] = clean_string(row_data.get('Description'))
                
            elif sheet_name == 'Allocations':
                # Map Insurable indicator to Evaluation Group 1
                ins_repl = clean_string(row_data.get('Insurable for replacement Value (Yes or No)'))
                mapped_values['EVALGROUP1'] = ins_repl
                
            elif sheet_name == 'Origin':
                mapped_values['ORIG_VALUE'] = clean_float(row_data.get('Acquisition Value'))
                
            elif sheet_name == 'Depreciation Areas':
                mapped_values['AFABE'] = "01" # Hardcoded depreciation area
                # mapped_values['AFASL'] = clean_string(row_data.get('DepKy'))
                mapped_values['AFASL'] = "LINS"
                mapped_values['NDJAR'] = clean_int(row_data.get('Use'), default=None)
                mapped_values['NDPER'] = clean_int(row_data.get('Per'), default=None)
                mapped_values['NDABJ'] = clean_int(row_data.get('EUL'), default=None)
                mapped_values['NDABP'] = clean_int(row_data.get('ELP'), default=None)
                mapped_values['AFABG'] = clean_date(row_data.get('ODep.Start'))
                mapped_values['INBDA'] = clean_date(row_data.get('Cap.date'))
                
                
            elif sheet_name == 'Cumulative Values':
                mapped_values['AFABE'] = "01"
                mapped_values['GJAHR'] = clean_int(row_data.get('Year'))
                mapped_values['KANSW'] = clean_float(row_data.get('Acquisition Value'))
                mapped_values['KNAFA'] = clean_float(row_data.get('Prior_Year_Accum_Dep'))
                mapped_values['KAAFA'] = clean_float(row_data.get('Pstd.unpl.dep.'))
                mapped_values['KMAFA'] = clean_float(row_data.get('Transf.Acq.Value'))
                mapped_values['KAUFN'] = clean_float(row_data.get('Transf.Accu.Dep'))
                
            elif sheet_name == 'Posted Values':
                mapped_values['AFABE'] = "01"
                mapped_values['GJAHR'] = clean_int(row_data.get('Year'))
                mapped_values['NAFAG'] = clean_float(row_data.get('Posted.Dep.CY'))
                mapped_values['AAFAG'] = clean_float(row_data.get('Pstd.unpl.dep.'))
                mapped_values['MAFAG'] = clean_float(row_data.get('Transf.Acq.Value'))
                mapped_values['AUFNG'] = clean_float(row_data.get('Transf.Accu.Dep'))
                mapped_values['LAST_POSTED_DEPR_PERIOD'] = clean_int(row_data.get('Last Dep Per'))
                
            elif sheet_name == 'Posting Information':
                mapped_values['AKTIV'] = clean_date(row_data.get('Cap.date'))
                # Deactivation date is empty/None for active records
                mapped_values['DEAKT'] = clean_date(row_data.get('Deact.Date'))
                
            elif sheet_name == 'Time-Dependent Data':
                mapped_values['GSBER'] = clean_string(row_data.get('BusA'))
                mapped_values['KOSTL'] = rec['s4_cost_center']
                mapped_values['WERKS'] = rec['s4_plant']
                mapped_values['STORT'] = rec['s4_location']
                
            elif sheet_name == 'Acct. Assignmt. for Investment':
                mapped_values['INVEST_ORD'] = clean_string(row_data.get('Inv. order'))

            # Flag any mandatory field that's blank in the final mapped
            # value — this catches both missing source data AND failed
            # lookups (e.g. a cost center with no override). The sheet
            # still gets written either way; this only records the issue.
            for field_tech, field_label in mandatory_fields.items():
                if is_blank(mapped_values.get(field_tech)):
                    validation_errors.append({
                        'sheet': sheet_name,
                        'field': field_tech,
                        'field_label': field_label,
                        'source_row': rec['source_row'],
                        'asset': rec['s4_asset'],
                        'subnumber': rec['s4_subnumber'],
                        'company_code': rec['s4_cocd'],
                    })
                
            # Write populated cells for this row
            for col_name, value in mapped_values.items():
                if col_name in col_to_idx:
                    c_idx = col_to_idx[col_name]
                    ws.cell(row=current_row, column=c_idx, value=value)
                    
            current_row += 1

    # Save to a bytes buffer
    out_buf = io.BytesIO()
    wb.save(out_buf)
    out_buf.seek(0)
    return out_buf, validation_errors