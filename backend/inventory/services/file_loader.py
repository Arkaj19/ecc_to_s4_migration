import io
import pandas as pd

def load_from_bytes(content: bytes, filename: str) -> pd.DataFrame:
    """Auto-detect CSV vs Excel from filename, reading from bytes."""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content), dtype=str)

    # CSV: try encodings, mirroring your original logic
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(content), dtype=str, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(content), dtype=str,
                       encoding="utf-8", encoding_errors="replace")