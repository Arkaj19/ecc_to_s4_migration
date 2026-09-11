"""
ECC -> S4 Field Mapping Rules
=============================

Pure, side-effect-free functions that translate ECC plant/storage-location
codes into their S4 equivalents, based on the business rules provided.

Used by:
    services/matching.py  ->  builds composite keys for ECC <-> S4 matching

Contents
--------
- compute_plant(werks, lgort)
    ECC (WERKS, LGORT)  ->  S4 Plant

- STORAGE_LOCATION_RULES
    Priority-ordered mapping table used by compute_storage_location.

- compute_storage_location(werks, lgort, plant)
    ECC (WERKS, LGORT) or computed S4 Plant  ->  S4 Storage_Location
"""


# -----------------------------------------------------------------------
# CONVERSION RULES: ECC (WERKS, LGORT) -> S4 Plant
# -----------------------------------------------------------------------
def compute_plant(werks, lgort):
    werks = (werks or "").strip()
    lgort = (lgort or "").strip().upper()

    if werks == "1021":
        if lgort in {"DWHS", "DRTN", "KWHS"}:
            return "US30"
        if lgort == "PWHS":
            return ""
        return "US27"

    if werks == "1028":
        if lgort in {"DWHS", "DRTN", "AWHS"}:
            return "US31"
        if lgort == "PWHS":
            return ""
        return "US28"

    if werks == "1030":
        if lgort == "DWHS":
            return ""
        if lgort == "DRTN":
            return "US33"
        return "US32"

    if werks == "1025":
        if lgort == "PWHS":
            return ""
        return "US29"

    if werks == "1029":
        return "CA02"

    # Other -> original WERKS unchanged
    return werks


# -----------------------------------------------------------------------
# CONVERSION RULES: (WERKS or computed Plant, LGORT) -> S4 Storage_Location
# Checked in priority order; first match wins. Falls back to original LGORT.
# -----------------------------------------------------------------------
STORAGE_LOCATION_RULES = [
    ("1021", {"CSA", "MRS", "PL01", "PL02", "TRL"}, "PRWK"),
    ("1028", {"PL02", "PL01", "THD", "DR01", "MRS", "PWHS"}, "PPKG"),
    ("1030", {"PL02", "PRTN", "PL01", "0021", "0020", "0045", "DWHS"}, "INSW"),
    ("1025", {"PL02", "TRL", "PWHS"}, "PPKG"),
    ("US30", {"DRTN", "KWHS"}, "DWHS"),
    ("CA02", {"TRMC"}, "DWHS"),
]


def compute_storage_location(werks, lgort, plant):
    werks = (werks or "").strip()
    lgort = (lgort or "").strip().upper()
    plant = (plant or "").strip()

    for key_code, lgort_set, storloc in STORAGE_LOCATION_RULES:
        if (werks == key_code or plant == key_code) and lgort in lgort_set:
            return storloc

    # Other -> original LGORT unchanged
    return lgort