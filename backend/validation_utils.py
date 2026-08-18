"""
Shared helpers for detecting mandatory-field gaps across the Asset, Credit,
and AP load-sheet templates.

Every one of these templates follows the same layout convention:
    Row 5 = technical SAP field name (matches what the processor writes)
    Row 8 = human-readable field description, with a trailing '*' on the
            first line when the field is mandatory, e.g.
            "Company Code*\n\nThe company code is..."

Reading mandatory-ness straight from the template (rather than hardcoding
a list per sheet) means it always matches whatever template file is
actually loaded, even if the template is updated later.
"""

import pandas as pd


def extract_mandatory_fields(ws, col_to_idx):
    """
    Returns {technical_field_name: human_readable_label} for every column
    on this sheet whose Row 8 description ends its first line with '*'.
    """
    mandatory = {}
    for tech_name, col_idx in col_to_idx.items():
        desc = ws.cell(row=8, column=col_idx).value
        if not desc:
            continue
        first_line = str(desc).split('\n', 1)[0].strip()
        if first_line.endswith('*'):
            mandatory[tech_name] = first_line[:-1].strip()
    return mandatory


def is_blank(value):
    """True if a mapped cell value would land in Excel as empty."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        if isinstance(value, float) and pd.isna(value):
            return True
    except Exception:
        pass
    return False
