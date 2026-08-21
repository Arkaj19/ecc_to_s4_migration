"""
Shared reference-data lookups used by ap_processor.py and
credit_processor.py:

1. BUT (Business Partner Identification Number) mapping — resolves a
   supplier/customer number from the registry to its S/4 Business
   Partner number.
2. DAP Clerk Codes mapping — resolves a customer number to its
   Credit Rep Group / Clerk Code.
"""

import pandas as pd


def normalize_id_key(value):
    """
    Normalize a supplier/customer/identification number into a
    consistent string key, so '12738', 12738.0, and ' 12738 ' all match
    the same entry regardless of which file or column they came from.
    """
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


# ============================================================
# BUT: Identification Number -> Business Partner
# ============================================================

def load_but_mapping(but_path, id_type, sheet_name="Data"):
    """
    Build {identification_number: business_partner} from the BUT
    reference export, restricted to a single Identification Type.

    IMPORTANT: the same Identification Number can appear multiple times
    in this sheet under different Identification Types, mapped to a
    DIFFERENT Business Partner each time — e.g. '163933' resolves to
    '800064' under 'DAPVEN' (vendor) but '4010088' under 'DAP'
    (customer). Around 240 numbers in this reference file collide this
    way, so every lookup MUST be scoped to one id_type
    ('DAPVEN' for AP suppliers, 'DAP' for Credit customers) or it will
    silently resolve to whichever row pandas happened to read last.
    """
    df = pd.read_excel(but_path, sheet_name=sheet_name)

    required = ["Identification Type", "Identification Number", "Business Partner"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "BUT reference file is missing expected column(s): "
            f"{', '.join(missing)}."
        )

    df = df[df["Identification Type"].astype(str).str.strip() == id_type]

    mapping = {}
    for _, row in df.iterrows():
        key = normalize_id_key(row.get("Identification Number"))
        bp = normalize_id_key(row.get("Business Partner"))
        if key and bp:
            mapping[key] = bp

    return mapping


def map_business_partner(mapping, source_value):
    """
    Look up source_value (a supplier or customer number from the
    registry) in a BUT mapping. Falls back to the original (normalized)
    value if there's no match, so a missing reference-data row degrades
    to "keep what we had" rather than blanking the field outright.
    """
    key = normalize_id_key(source_value)
    return mapping.get(key, key)


# ============================================================
# DAP Clerk Codes: Customer Number -> Credit Rep Group
# ============================================================

def load_credit_rep_group_mapping(clerk_codes_path, sheet_name="DAP Clerk Codes"):
    """
    Build {customer_number: credit_rep_group} from the DAP Clerk Codes
    reference file.

    Keyed by the registry's raw Customer Number (the same key space as
    the BUT sheet's 'DAP' Identification Numbers) — NOT the mapped
    Business Partner value — since that's what this reference file
    itself uses.
    """
    df = pd.read_excel(clerk_codes_path, sheet_name=sheet_name)

    required = ["Customer Number", "Credit rep.group/Clerk code"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "DAP Clerk Codes file is missing expected column(s): "
            f"{', '.join(missing)}."
        )

    mapping = {}
    for _, row in df.iterrows():
        key = normalize_id_key(row.get("Customer Number"))
        raw_code = row.get("Credit rep.group/Clerk code")

        if not key:
            continue
        try:
            if pd.isna(raw_code):
                continue
        except (TypeError, ValueError):
            pass

        # The visible values in this file are 2-digit codes with a
        # leading zero ('01', '02', ...), but pandas reads the
        # underlying cell as a plain integer (1, 2, ...) — restore the
        # zero-padded form so it matches what the template expects.
        try:
            code = str(int(float(raw_code))).zfill(2)
        except (TypeError, ValueError):
            code = str(raw_code).strip()

        mapping[key] = code

    return mapping


def get_credit_rep_group(mapping, customer_number, default=""):
    """
    Look up customer_number in a Clerk Codes mapping. Falls back to an
    empty string (NOT the registry's own Credit Rep Group value) when
    there's no match, per the requirement to stop using the registry's
    value for this field entirely.
    """
    key = normalize_id_key(customer_number)
    return mapping.get(key, default)