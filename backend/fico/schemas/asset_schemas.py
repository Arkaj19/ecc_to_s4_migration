"""
Schemas for fico/api/asset_router.py.

`/process-asset` and `/validate-asset` both accept an optional
`mappings_json` form field: a JSON-encoded string with up to three
override tables (company code, plant/location, cost center) that take
priority over the prebuilt mappings in mappings.py. `_parse_custom_mappings`
in asset_router.py decodes and reshapes that JSON by hand today; these
schemas give that payload a validated shape (see
`AssetCustomMappingsRequest.parse_raw_json`) while `_parse_custom_mappings`
keeps doing the reshaping into the plain/tuple-keyed dicts the processor
expects.

`/process-asset` streams a file, so it isn't wired up as a
`response_model`. `/validate-asset` returns JSON and reuses the shared
"quick" validation shape from common_schemas.py.
"""

from typing import List, Optional, Union

from pydantic import BaseModel

from .common_schemas import FieldValidationResponse


# ============================================================
# `mappings_json` form field (POST /process-asset, POST /validate-asset)
# ============================================================

class CocdMappingItem(BaseModel):
    """
    `ecc_cocd`/`s4_cocd` are optional here (rather than required) so an
    incomplete row fails validation gracefully instead of a 400 -- the
    router drops rows missing either key, matching the original
    dict-based parsing behavior.
    """
    ecc_cocd: Optional[str] = None
    s4_cocd: Optional[str] = None


class PlantLocMappingItem(BaseModel):
    ecc_plant: Optional[Union[str, int, float]] = None
    ecc_location: Optional[str] = None
    s4_plant: Optional[Union[str, int, float]] = None
    s4_location: Optional[str] = None


class CostCenterMappingItem(BaseModel):
    ecc_cost_center: Optional[Union[str, int, float]] = None
    s4_cost_center: Optional[Union[str, int, float]] = None


class AssetCustomMappingsRequest(BaseModel):
    """
    Decoded shape of the `mappings_json` form field. All three tables
    are optional -- any combination (or none) may be supplied, and any
    entry missing a required key is dropped by `_parse_custom_mappings`
    rather than rejected outright.
    """
    cocd: Optional[List[CocdMappingItem]] = None
    plant_loc: Optional[List[PlantLocMappingItem]] = None
    cost_center: Optional[List[CostCenterMappingItem]] = None


# ============================================================
# POST /process-asset
# ============================================================

class ProcessAssetRequest(BaseModel):
    """
    Documents the multipart form fields accepted by `/process-asset`.
    Not used as a FastAPI dependency directly -- the route takes
    `UploadFile`/`Form` params so it can stream the upload.
    """
    file: str  # Excel (.xlsx/.xls) upload, field name "file"
    mappings_json: Optional[str] = None  # see AssetCustomMappingsRequest


# ============================================================
# POST /validate-asset
# ============================================================

class ValidateAssetRequest(BaseModel):
    """Documents the multipart form fields accepted by `/validate-asset`."""
    file: str  # Excel (.xlsx/.xls) upload, field name "file"
    mappings_json: Optional[str] = None
    sheet_names: str = "US01,US06,CA01"


class AssetFieldValidationResponse(FieldValidationResponse):
    """Response body for `/validate-asset`."""
    pass
