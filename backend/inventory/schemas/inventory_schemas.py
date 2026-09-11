from pydantic import BaseModel
from typing import Any, List, Optional

class UploadResponse(BaseModel):
    session_id: str
    ecc_filename: str
    s4_filename: str
    message: str

class ValidationSummary(BaseModel):
    ecc_rows: int
    s4_rows: int
    ecc_unique_keys: int
    s4_unique_keys: int
    common_keys: int
    sample_size: int

class ValidateResponse(BaseModel):
    download_id: str
    summary: ValidationSummary
    ecc_rows: List[dict[str, Any]]
    s4_rows: List[dict[str, Any]]
    columns_ecc: List[str]
    columns_s4: List[str]