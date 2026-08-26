# # backend/mappings.py

# import pandas as pd

# # Company Code Mappings (ECC -> S/4)
# COMPANY_CODE_MAPPING = {
#     "US01": "1000",
#     "US06": "1001",
#     "CA01": "1200"
# }

# # Plant and Location Mappings (ECC Plant, ECC Location) -> (S/4 Plant, S/4 Location)
# PLANT_LOCATION_MAPPING = {
#     (1000, "DAPLB"): {"s4_plant": "US26", "s4_location": "DapLab"},
#     (1000, "DAPHQ"): {"s4_plant": "US26", "s4_location": "DapHQ"},
#     (1021, "BALTPL"): {"s4_plant": "US27", "s4_location": "BaltPlt"},
#     (1021, "KELSO"): {"s4_plant": "US28", "s4_location": "KelsoDC"},
#     (1025, "TIPPCY"): {"s4_plant": "US29", "s4_location": "TippCyPlt"},
#     (1028, "DALLPL"): {"s4_plant": "US30", "s4_location": "DallPlt"},
#     (1028, "GARLND"): {"s4_plant": "US31", "s4_location": "GarlndDC"},
#     (1029, "CANADA"): {"s4_plant": "CA02", "s4_location": "TorontoDC"},
#     (1030, "STLPLT"): {"s4_plant": "US32", "s4_location": "StlPlt"},
#     (1030, "STLRD"): {"s4_plant": "US33", "s4_location": "StlLab"},
#     (1030, "STLDC"): {"s4_plant": "US33", "s4_location": "StlDC"},
#     (1030, "STLHQ"): {"s4_plant": "US33", "s4_location": "StlOffice"},
# }

# # Specific Cost Center Mapping overrides
# # Specific Cost Center Mapping overrides
# COST_CENTER_OVERRIDES = {
#     # Baltimore
#     1021240: "US27AM10",
#     1021241: "US27AM15",
#     1021253: "US27CB10",
#     1021260: "US27H110",
#     1021351: "US30X100",

#     # Tipp City
#     1025240: "US29AM10",
#     1025241: "US29AM15",
#     1025242: "US29AM17",
#     1025253: "US29CB10",
#     1025260: "US29H110",

#     # R&D
#     1027261: "10008100",

#     # Dallas
#     1028240: "US28AM10",
#     1028241: "US28AM15",
#     1028253: "US28CB10",
#     1028260: "US28H110",
#     1028351: "US31X100",

#     # St. Louis / Pacific
#     1030240: "US32AM10",
#     1030241: "US32AM15",
#     1030242: "US32AM17",
#     1030253: "US32CB10",
#     1030260: "US32H110",

#     # Manufacturing Depreciation (CoCd 1001)
#     7021100: "US27CB20",
#     7025100: "US29CB20",
#     7028100: "US28CB20",
#     7030100: "US32CB20",

#     # Canada
#     2029351: "CA02X100",

#     # Additional
#     1021100: "US27CB10",
#     1000650: "10009970",
# }
# def get_s4_company_code(ecc_cocd: str) -> str:
#     """Look up S/4 Company Code from ECC Company Code."""
#     if not ecc_cocd:
#         return ""
#     # Normalize string
#     cocd_str = str(ecc_cocd).strip().upper()
#     return COMPANY_CODE_MAPPING.get(cocd_str, cocd_str)

# def get_s4_plant_and_location(ecc_plant, ecc_location) -> dict:
#     """Look up S/4 Plant and Location based on ECC Plant and Location."""
#     # A blank source cell comes in as float NaN (not None) via pandas.
#     # str(NaN) is the literal text 'nan', which — left unguarded — was
#     # leaking into the output as fallback values like "USnan" for plant
#     # and "NAN" for location. Normalize NaN to None up front so the
#     # existing None-checks below actually catch it.
#     if pd.isna(ecc_plant):
#         ecc_plant = None
#     if pd.isna(ecc_location):
#         ecc_location = None

#     try:
#         plant_val = int(float(ecc_plant)) if ecc_plant is not None else None
#     except (ValueError, TypeError):
#         plant_val = str(ecc_plant).strip() if ecc_plant is not None else None

#     loc_str = str(ecc_location).strip().upper() if ecc_location is not None else None

#     # Try exact match with tuple key
#     match = PLANT_LOCATION_MAPPING.get((plant_val, loc_str))
#     if match:
#         return match

#     # Fallback to single column lookups if full key not matched
#     # Find any plant match or location match
#     fallback_plant = ""
#     fallback_loc = ""
#     for (p, l), mapping in PLANT_LOCATION_MAPPING.items():
#         if p == plant_val:
#             fallback_plant = mapping["s4_plant"]
#         if l == loc_str:
#             fallback_loc = mapping["s4_location"]

#     return {
#         "s4_plant": fallback_plant or (f"US{plant_val}" if plant_val else ""),
#         "s4_location": fallback_loc or (loc_str or "")
#     }

# def get_s4_cost_center(ecc_cost_center, ecc_plant=None, ecc_location=None) -> str:
#     """Look up S/4 Cost Center with overrides and standard pattern fallback."""
#     if ecc_cost_center is None:
#         return ""
    
#     try:
#         cc_val = int(float(ecc_cost_center))
#     except (ValueError, TypeError):
#         cc_val = str(ecc_cost_center).strip()

#     return COST_CENTER_OVERRIDES.get(cc_val, "")

# backend/mappings.py

import pandas as pd

# Company Code Mappings (ECC -> S/4)
COMPANY_CODE_MAPPING = {
    "US01": "1000",
    "US06": "1001",
    "CA01": "1200"
}

# Plant and Location Mappings (ECC Plant, ECC Location) -> (S/4 Plant, S/4 Location)
PLANT_LOCATION_MAPPING = {
    (1000, "DAPLB"): {"s4_plant": "US26", "s4_location": "DapLab"},
    (1000, "DAPHQ"): {"s4_plant": "US26", "s4_location": "DapHQ"},
    (1021, "BALTPL"): {"s4_plant": "US27", "s4_location": "BaltPlt"},
    (1021, "KELSO"): {"s4_plant": "US28", "s4_location": "KelsoDC"},
    (1025, "TIPPCY"): {"s4_plant": "US29", "s4_location": "TippCyPlt"},
    (1028, "DALLPL"): {"s4_plant": "US30", "s4_location": "DallPlt"},
    (1028, "GARLND"): {"s4_plant": "US31", "s4_location": "GarlndDC"},
    (1029, "CANADA"): {"s4_plant": "CA02", "s4_location": "TorontoDC"},
    (1030, "STLPLT"): {"s4_plant": "US32", "s4_location": "StlPlt"},
    (1030, "STLRD"): {"s4_plant": "US33", "s4_location": "StlLab"},
    (1030, "STLDC"): {"s4_plant": "US33", "s4_location": "StlDC"},
    (1030, "STLHQ"): {"s4_plant": "US33", "s4_location": "StlOffice"},
}

# Specific Cost Center Mapping overrides
# Specific Cost Center Mapping overrides
COST_CENTER_OVERRIDES = {
    # Baltimore
    1021240: "US27AM10",
    1021241: "US27AM15",
    1021253: "US27CB10",
    1021260: "US27H110",
    1021351: "US30X100",

    # Tipp City
    1025240: "US29AM10",
    1025241: "US29AM15",
    1025242: "US29AM17",
    1025253: "US29CB10",
    1025260: "US29H110",

    # R&D
    1027261: "10008100",

    # Dallas
    1028240: "US28AM10",
    1028241: "US28AM15",
    1028253: "US28CB10",
    1028260: "US28H110",
    1028351: "US31X100",

    # St. Louis / Pacific
    1030240: "US32AM10",
    1030241: "US32AM15",
    1030242: "US32AM17",
    1030253: "US32CB10",
    1030260: "US32H110",

    # Manufacturing Depreciation (CoCd 1001)
    7021100: "US27CB20",
    7025100: "US29CB20",
    7028100: "US28CB20",
    7030100: "US32CB20",

    # Canada
    2029351: "CA02X100",

    # Additional
    1021100: "US27CB10",
    1000650: "10009970",
}
def get_s4_company_code(ecc_cocd: str) -> str:
    """Look up S/4 Company Code from ECC Company Code."""
    # NaN is truthy in Python, so `if not ecc_cocd` alone doesn't catch a
    # blank source cell — it falls through, str(NaN) becomes the literal
    # text 'nan', and that ends up written straight into the output.
    if pd.isna(ecc_cocd) or not ecc_cocd:
        return ""
    # Normalize string
    cocd_str = str(ecc_cocd).strip().upper()
    if not cocd_str:
        return ""
    return COMPANY_CODE_MAPPING.get(cocd_str, cocd_str)

def get_s4_plant_and_location(ecc_plant, ecc_location) -> dict:
    """Look up S/4 Plant and Location based on ECC Plant and Location."""
    # A blank source cell comes in as float NaN (not None) via pandas.
    # str(NaN) is the literal text 'nan', which — left unguarded — was
    # leaking into the output as fallback values like "USnan" for plant
    # and "NAN" for location. Normalize NaN to None up front so the
    # existing None-checks below actually catch it.
    if pd.isna(ecc_plant):
        ecc_plant = None
    if pd.isna(ecc_location):
        ecc_location = None

    try:
        plant_val = int(float(ecc_plant)) if ecc_plant is not None else None
    except (ValueError, TypeError):
        plant_val = str(ecc_plant).strip() if ecc_plant is not None else None

    loc_str = str(ecc_location).strip().upper() if ecc_location is not None else None

    # Try exact match with tuple key
    match = PLANT_LOCATION_MAPPING.get((plant_val, loc_str))
    if match:
        return match

    # Fallback to single column lookups if full key not matched
    # Find any plant match or location match
    fallback_plant = ""
    fallback_loc = ""
    for (p, l), mapping in PLANT_LOCATION_MAPPING.items():
        if p == plant_val:
            fallback_plant = mapping["s4_plant"]
        if l == loc_str:
            fallback_loc = mapping["s4_location"]

    return {
        "s4_plant": fallback_plant or (f"US{plant_val}" if plant_val else ""),
        "s4_location": fallback_loc or (loc_str or "")
    }

def get_s4_cost_center(ecc_cost_center, ecc_plant=None, ecc_location=None) -> str:
    """Look up S/4 Cost Center with overrides and standard pattern fallback."""
    if ecc_cost_center is None:
        return ""
    
    try:
        cc_val = int(float(ecc_cost_center))
    except (ValueError, TypeError):
        cc_val = str(ecc_cost_center).strip()

    return COST_CENTER_OVERRIDES.get(cc_val, "")