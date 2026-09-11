"""
Generic Excel/registry value-coercion helpers shared across every FICO
processor and validator (AP, AR, Asset, Credit).

These functions have NO SAP/FICO business meaning of their own — they
just turn messy Excel cell values (NaN, integer-like floats, SAP-style
accounting text, mixed date formats) into clean Python types. That's
what makes this `utils/`, not `repo/`: nothing here reads a reference
file or knows what a Business Partner or a Company Code is.

History: prior to this consolidation, clean_string/clean_int/clean_date/
normalize_series existed as identical copy-pasted definitions in up to
seven different files (every processor and every validator). This
module is the single source of truth for those now — see git history
on the individual processor/validator files if you need the old
per-file versions for reference.
"""

import datetime

import pandas as pd


# ============================================================
# clean_string — identical in all 7 prior copies, merged as-is
# ============================================================

def clean_string(value):
    """
    Convert a value to a clean string.

    Empty/NaN values become "". Numeric values such as 5304994.0 or
    1000.0 become "5304994" / "1000" (prevents integer-like floats
    from being written with a trailing ".0" when the Excel source
    stored them as floats).
    """
    if value is None or pd.isna(value):
        return ""

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value).strip()


# ============================================================
# clean_int — identical in both prior copies (ap_processor,
# asset_processor), merged as-is
# ============================================================

def clean_int(val, default=""):
    """
    Convert a value to an integer.

    Blank / NaN values return the supplied default. Values that can't
    be parsed as a number are returned as a stripped string rather
    than raising, so a genuinely non-numeric cell doesn't crash the
    whole conversion.
    """
    if pd.isna(val) or val is None:
        return default

    try:
        return int(float(val))
    except (ValueError, TypeError):
        return str(val).strip()


# ============================================================
# clean_date — identical in all 3 prior copies (ap_processor,
# ar_processor, asset_processor), merged as-is
# ============================================================

def clean_date(val):
    """
    Convert Excel/date values into Python date objects.

    Recognizes several ECC/S4 export date formats plus a handful of
    "blank date" sentinel strings ("00/00/0000", "00.00.0000", "NaT").
    Returns None for anything blank/unparseable rather than raising.
    """
    if pd.isna(val) or val is None:
        return None

    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.date() if isinstance(val, datetime.datetime) else val

    val_str = str(val).strip()

    if val_str in ("", "00/00/0000", "00.00.0000", "NaT"):
        return None

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%Y%m%d",
    ):
        try:
            return datetime.datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue

    return val


# ============================================================
# normalize_series — identical in both prior copies (ap_validator,
# ar_validator), merged as-is
# ============================================================

def normalize_series(series: pd.Series, upper: bool = True) -> pd.Series:
    """
    Apply clean_string element-wise, optionally upper-casing the
    result. Centralizes the `.apply(clean_string).str.upper()` pattern
    every reconciliation check needs before comparing ECC and S/4
    values, so each check just declares which columns it cares about.
    """
    cleaned = series.apply(clean_string)
    return cleaned.str.upper() if upper else cleaned


# ============================================================
# clean_float — NOT a straight merge. Two genuinely different prior
# implementations existed:
#   - ap_processor.py / asset_processor.py: parsed SAP/Excel
#     "accounting format" negatives, e.g. "5,114.43-" or "(5,114.43)"
#   - ar_processor.py / credit_processor.py: plain float(value) cast,
#     no accounting-format handling, AND disagreed with each other on
#     the failure fallback (default vs. the raw original value)
#
# Kept as two explicitly-named functions rather than silently picking
# one, since collapsing them could change AR/Credit's numeric output
# for any registry row using accounting-style negative notation.
# See the note in each processor's own comment for the decision to
# make before deleting one of these.
# ============================================================

def clean_float(val, default=None):
    """
    Convert a value to float with a plain cast — no accounting-format
    handling. Equivalent to the prior ar_processor.py behavior.

    Blank / NaN / unparseable values return the supplied default.
    """
    if pd.isna(val) or val is None:
        return default

    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def clean_float_accounting(val, default=None):
    """
    Convert a value to float, additionally handling SAP/Excel
    "accounting format" text such as "5,114.43-" or "(5,114.43)" for
    negative numbers. Equivalent to the prior ap_processor.py /
    asset_processor.py behavior.

    Registry exports commonly render negatives with a trailing minus
    sign and/or thousands separators rather than a leading minus.
    Python's float() can't parse either of those directly, so without
    this such values fall through unchanged as literal text (with the
    trailing minus baked in) instead of becoming the real negative
    number -5114.43.

    Blank / NaN / unparseable values return the supplied default.
    """
    if pd.isna(val) or val is None:
        return default

    if isinstance(val, (int, float)):
        return float(val)

    text = str(val).strip()
    if not text:
        return default

    negative = False

    if text.endswith("-"):
        negative = True
        text = text[:-1].strip()
    elif text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    text = text.replace(",", "")

    try:
        number = float(text)
    except (ValueError, TypeError):
        # Matches the original behavior exactly: an unparseable value
        # (after stripping accounting-style negative markers) returns
        # the original raw value, NOT `default` — different from
        # clean_float() above. Preserved deliberately; do not "fix"
        # this into `return default` without confirming with whoever
        # owns AP/Asset that nothing downstream depends on the
        # original text passing through unchanged here.
        return val

    return -number if negative else number
