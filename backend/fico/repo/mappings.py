# backend/mappings.py

import pandas as pd

# Company Code Mappings (ECC -> S/4)
COMPANY_CODE_MAPPING = {
    "US01": "1000",
    "US06": "1001",
    "CA01": "1200",
    # US09 has no S/4 translation -- it carries the same code on both
    # sides. Discovered via ap_validator.py's BSIK_AP_Registry.xlsx /
    # AP_Data_Load_SIT2 crosstab; kept here as an explicit self-mapping
    # so validate_company_code_counts() (which does a plain dict.get
    # with no passthrough) resolves it instead of flagging MAPPING_ERROR.
    "US09": "US09",
}

# ============================================================
# AP Payment Terms Mapping
# ECC -> S/4
# ============================================================

AP_PAYMENT_TERMS_MAPPING = {
    "O": "NT30",
    "A": "NT00",
    "B": "NT10",
    "H": "NT15",
    "T": "NT60",
    "C": "Z130",
    "L": "NT20",
    "YY": "NT90",
    "R": "NT45",
    "S": "NT50",
    "NF5": "Z514",
    "D": "Z221",
    "ZZ": "N100",
    "I": "Z229",
    "N120": "N120",
    "M": "Z120",
    "EE": "Z167",
    "BB": "Z103",
    "G": "Z162",
    "NF7": "NT07",
    "HI": "Z101",
    "U": "Z053",
    "N110": "N110",
    "TT": "NT75",
    "Y": "NT55",
    "V": "Z233",
    "Q": "NT40",
    "X": "Z247",
    "WX": "Z163",
    "N115": "N115",
    "Z": "Z132",
    "J": "P215",
    "E10": "P210",
    "E": "P010",
    "FF": "Z145",
    "N125": "N125",
    "N65": "NT65",
    "T70": "NT70",
    "NF4": "Z333",
    "N135": "N135",
    "AA": "Z261",
    "CC": "Z147",
    "W": "Z263",
    "DD": "Z100",
    "F": "P231",
    "XX": "Z190",
    "N": "Z223",
    "OO": "NT38",
}

# ============================================================
# AR Payment Terms Mapping
# ECC -> S/4
#
# Distinct from AP_PAYMENT_TERMS_MAPPING above: AR uses numeric ECC
# codes (e.g. "001", "033") rather than AP's letter codes, and the two
# processes map some of the same-looking codes to different S/4 terms.
# Keep these as two separate tables rather than merging them.
# ============================================================

AR_PAYMENT_TERMS_MAPPING = {
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

def get_s4_ar_company_code(ecc_company_code) -> str:
    """
    Look up S/4 Company Code from ECC Company Code (AR).

    Uses the same COMPANY_CODE_MAPPING table as get_s4_company_code
    above, but AR returns "" for an unmapped code instead of passing
    the ECC code through unchanged -- matching ar_processor.py's
    original local get_s4_company_code().
    """
    if ecc_company_code is None or pd.isna(ecc_company_code):
        cocd_str = ""
    elif isinstance(ecc_company_code, float) and ecc_company_code.is_integer():
        cocd_str = str(int(ecc_company_code))
    else:
        cocd_str = str(ecc_company_code).strip()

    return COMPANY_CODE_MAPPING.get(cocd_str.upper(), "")

def get_s4_ap_payment_terms(ecc_payment_term):
    """
    Look up S/4 Payment Terms from ECC Payment Terms (AP).
    """

    if not ecc_payment_term or pd.isna(ecc_payment_term):
        return ""

    payment_term = str(ecc_payment_term).strip().upper()

    return AP_PAYMENT_TERMS_MAPPING.get(
        payment_term,
        payment_term
    )

def get_s4_ar_payment_terms(ecc_payment_term):
    """
    Look up S/4 Payment Terms from ECC Payment Terms (AR).

    Leading zeroes are ignored, so values such as 033 and 33
    are treated as the same ECC payment-term code. This mirrors
    AR's own numeric-code table (AR_PAYMENT_TERMS_MAPPING), which is
    keyed and normalized differently from AP's letter-code table.
    """

    if ecc_payment_term is None or pd.isna(ecc_payment_term):
        return "No payment terms in ECC"

    payment_term = str(ecc_payment_term).strip().upper()

    # Excel/Pandas may read numeric codes as 33.0.
    if payment_term.endswith(".0") and payment_term[:-2].isdigit():
        payment_term = payment_term[:-2]

    normalized_term = payment_term.lstrip("0") or "0"

    for ecc_code, s4_term in AR_PAYMENT_TERMS_MAPPING.items():
        normalized_code = ecc_code.lstrip("0") or "0"
        if normalized_code == normalized_term:
            return s4_term

    return payment_term

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