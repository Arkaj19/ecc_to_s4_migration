import random
import pandas as pd
from .plant_store_loc_mapping import compute_plant, compute_storage_location

ECC_MATNR, ECC_WERKS, ECC_LGORT = "MATNR", "WERKS", "LGORT"
S4_MATERIAL, S4_PLANT, S4_STORLOC = "Material", "Plant", "Storage_Location"

def _norm_ecc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in (ECC_MATNR, ECC_WERKS, ECC_LGORT):
        df[c] = df[c].astype(str).str.strip()
    return df

def _norm_s4(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in (S4_MATERIAL, S4_PLANT, S4_STORLOC):
        df[c] = df[c].astype(str).str.strip()
    return df

def run_match(ecc_raw: pd.DataFrame, s4_raw: pd.DataFrame,
              sample_size: int = 50, seed: int | None = 42):
    """Returns (ecc_out, s4_out, summary_dict) or raises ValueError."""
    

    if seed is not None:
        random.seed(seed)

    ecc = _norm_ecc(ecc_raw)
    s4  = _norm_s4(s4_raw)

    ecc["_Plant_calc"] = ecc.apply(
        lambda r: compute_plant(r[ECC_WERKS], r[ECC_LGORT]), axis=1)
    ecc["_StorLoc_calc"] = ecc.apply(
        lambda r: compute_storage_location(r[ECC_WERKS], r[ECC_LGORT],
                                           r["_Plant_calc"]), axis=1)

    ecc["_key"] = ecc[ECC_MATNR] + "|" + ecc["_Plant_calc"] + "|" + ecc["_StorLoc_calc"]
    s4["_key"]  = s4[S4_MATERIAL] + "|" + s4[S4_PLANT] + "|" + s4[S4_STORLOC]

    ecc_keys, s4_keys = set(ecc["_key"]), set(s4["_key"])
    common = ecc_keys & s4_keys

    summary = {
        "ecc_rows": int(len(ecc)),
        "s4_rows": int(len(s4)),
        "ecc_unique_keys": int(len(ecc_keys)),
        "s4_unique_keys": int(len(s4_keys)),
        "common_keys": int(len(common)),
        "sample_size": int(min(sample_size, len(common))),
    }

    if not common:
        raise ValueError(
            "No common composite keys found. Check column names, "
            "conversion rules, or leading-zero formatting."
        )

    n = min(sample_size, len(common))
    sampled = random.sample(sorted(common), n)

    ecc_first = ecc.drop_duplicates("_key", keep="first").set_index("_key")
    s4_first  = s4.drop_duplicates("_key", keep="first").set_index("_key")

    ecc_out = (ecc_first.loc[sampled].reset_index()
               .drop(columns=["_Plant_calc", "_StorLoc_calc"])
               .rename(columns={"_key": "Composite_Key"}))
    s4_out  = (s4_first.loc[sampled].reset_index()
               .rename(columns={"_key": "Composite_Key"}))

    for df in (ecc_out, s4_out):
        cols = ["Composite_Key"] + [c for c in df.columns if c != "Composite_Key"]
        df[:] = df[cols]  # reorder in place

    return ecc_out, s4_out, summary


def build_excel_bytes(ecc_df: pd.DataFrame, s4_df: pd.DataFrame) -> bytes:
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        ecc_df.to_excel(w, sheet_name="50 ecc", index=False)
        s4_df.to_excel(w, sheet_name="50 s4", index=False)
    return buf.getvalue()


def df_to_records(df: pd.DataFrame):
    """NaN-safe JSON-friendly records."""
    return df.where(pd.notnull(df), None).to_dict(orient="records")