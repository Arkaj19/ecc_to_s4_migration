from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
import json
import io
import os

from backend.config import TEMPLATES_DIR
from backend.fico.services.asset_processor import (
    process_asset_registry,
    RegistryMismatchError as AssetMismatchError,
)
from backend.fico.schemas.asset_schemas import (
    AssetCustomMappingsRequest,
    AssetFieldValidationResponse,
)

router = APIRouter(tags=["Asset"])

TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "assets_load_template.xlsx")


def _parse_custom_mappings(mappings_json: str):
    """
    Shared by /process-asset and /validate-asset so both endpoints apply
    the exact same custom mapping overrides.
    """
    if not mappings_json:
        return None
    try:
        parsed_raw = json.loads(mappings_json)
        # Validate shape against AssetCustomMappingsRequest first -- this
        # is what actually enforces the schema. Rows that fail validation
        # (wrong types, etc.) raise a 400 here instead of silently being
        # dropped further down. Reshaping into the tuple-keyed dicts the
        # processor expects still happens against the original dicts, so
        # unrecognized/extra keys on an item are simply ignored, same as
        # before.
        validated = AssetCustomMappingsRequest.parse_obj(parsed_raw)

        custom_maps = {}

        if validated.cocd is not None:
            custom_maps['cocd'] = {
                item.ecc_cocd: item.s4_cocd
                for item in validated.cocd
                if item.ecc_cocd is not None and item.s4_cocd is not None
            }

        if validated.plant_loc is not None:
            custom_maps['plant_loc'] = {}
            for item in validated.plant_loc:
                if None in (item.ecc_plant, item.ecc_location, item.s4_plant, item.s4_location):
                    continue
                try:
                    p_key = int(float(item.ecc_plant))
                except (ValueError, TypeError):
                    p_key = str(item.ecc_plant).strip()
                l_key = str(item.ecc_location).strip().upper()
                custom_maps['plant_loc'][(p_key, l_key)] = {
                    "s4_plant": item.s4_plant,
                    "s4_location": item.s4_location
                }

        if validated.cost_center is not None:
            custom_maps['cost_center'] = {}
            for item in validated.cost_center:
                if item.ecc_cost_center is None or item.s4_cost_center is None:
                    continue
                try:
                    cc_key = int(float(item.ecc_cost_center))
                except (ValueError, TypeError):
                    cc_key = str(item.ecc_cost_center).strip()
                custom_maps['cost_center'][cc_key] = item.s4_cost_center

        return custom_maps
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid custom mappings JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse custom mappings JSON: {str(e)}")


@router.post("/process-asset")
async def process_asset(
    file: UploadFile = File(...),
    mappings_json: str = Form(None)
):
    """
    POST endpoint that intakes the Registry excel file and returns the
    populated S/4 HANA assets_load_template file.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")

    custom_maps = _parse_custom_mappings(mappings_json)

    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        out_buf, validation_errors = process_asset_registry(
            reg_io,
            template_path=TEMPLATE_PATH,
            custom_mappings=custom_maps,
            sheet_names=['US01', 'US06', 'CA01']
        )

        return StreamingResponse(
            out_buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=assets_load_template_filled.xlsx",
                "X-Validation-Error-Count": str(len(validation_errors)),
                "Access-Control-Expose-Headers": "X-Validation-Error-Count",
            }
        )
    except AssetMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing asset registry: {str(e)}")


@router.post("/validate-asset", response_model=AssetFieldValidationResponse)
async def validate_asset(
    file: UploadFile = File(...),
    mappings_json: str = Form(None),
    sheet_names: str = Form("US01,US06,CA01")
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")

    custom_maps = _parse_custom_mappings(mappings_json)
    sheet_list = [s.strip() for s in sheet_names.split(",") if s.strip()]

    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        _out_buf, validation_errors = process_asset_registry(
            reg_io,
            template_path=TEMPLATE_PATH,
            custom_mappings=custom_maps,
            sheet_names=sheet_list
        )

        counts = {}
        for err in validation_errors:
            key = (err['sheet'], err['field_label'])
            counts[key] = counts.get(key, 0) + 1

        errors = [
            {
                "sheet": sheet,
                "column": column,
                "missing_rows": count,
                "message": (
                    f"Mandatory column {column} of sheet {sheet} has "
                    f"{count} missing row{'s' if count != 1 else ''}."
                ),
            }
            for (sheet, column), count in counts.items()
        ]

        return {"valid": len(errors) == 0, "errors": errors}

    except AssetMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error validating asset registry: {str(e)}")