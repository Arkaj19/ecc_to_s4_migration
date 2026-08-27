from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import io
from asset_processor import process_asset_registry, RegistryMismatchError as AssetMismatchError
from credit_processor import process_credit_registry, RegistryMismatchError as CreditMismatchError
from ap_processor import process_ap_registry, RegistryMismatchError as APMismatchError
from ar_processor import process_ar_registry, RegistryMismatchError as ARMismatchError
import mappings
import os
 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
 
TEMPLATE_PATH = os.path.join(
    BASE_DIR,
    "templates",
    "assets_load_template.xlsx"
)

CREDIT_TEMPLATE_PATH = os.path.join(
    BASE_DIR,
    "templates",
    "Credit Data Load - SIT2.xlsx"
)

AP_TEMPLATE_PATH = os.path.join(
    BASE_DIR,
    "templates",
    "AP Data Load Sheet - SIT2.xlsx"
)

# NEW: AR template path
AR_TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "AR_TEMPLATE.xlsx")

# Reference data (not templates) used for Supplier/Customer -> Business
# Partner lookups (BUT sheet) and Customer -> Credit Rep Group lookups
# (DAP Clerk Codes), shared by the Credit and AP processors.
BUT_REFERENCE_PATH = os.path.join(
    BASE_DIR,
    "reference_data",
    "but0id_qs4_500.xlsx"
)

CLERK_CODES_PATH = os.path.join(
    BASE_DIR,
    "reference_data",
    "DAP_CODE.xlsx"
)
 
app = FastAPI(title="ECC to S/4 HANA FICO Data Migrator Backend")
 
# Allow the Vite dev server (and any frontend) to call this API. Without
# this, the browser blocks every request before it reaches an endpoint —
# uvicorn shows nothing at all in its logs for the failed request, which is
# the telltale sign it's a CORS problem rather than the server being down.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your deployed frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ecc_to_s4_migrator_backend"}
 
@app.get("/default-mappings")
def get_default_mappings():
    """Returns the prebuilt mappings seeded in Python."""
    # Convert company code mappings to list format for easier frontend editing
    cocd_list = [
        {"ecc_cocd": k, "s4_cocd": v}
        for k, v in mappings.COMPANY_CODE_MAPPING.items()
    ]
   
    # Convert plant & location mappings to list
    plant_loc_list = [
        {
            "ecc_plant": int(k[0]) if isinstance(k[0], (int, float)) else k[0],
            "ecc_location": k[1],
            "s4_plant": v["s4_plant"],
            "s4_location": v["s4_location"]
        }
        for k, v in mappings.PLANT_LOCATION_MAPPING.items()
    ]
   
    # Convert cost center overrides to list
    cost_center_list = [
        {"ecc_cost_center": int(k) if isinstance(k, (int, float)) else k, "s4_cost_center": v}
        for k, v in mappings.COST_CENTER_OVERRIDES.items()
    ]
   
    return {
        "cocd": cocd_list,
        "plant_loc": plant_loc_list,
        "cost_center": cost_center_list
    }
 
def parse_custom_mappings(mappings_json: str):
    """
    Shared by /process-asset and /validate-asset so both endpoints apply
    the exact same custom mapping overrides.
    """
    if not mappings_json:
        return None
    try:
        parsed = json.loads(mappings_json)
        custom_maps = {}

        # Reconstruct cocd map
        if 'cocd' in parsed:
            custom_maps['cocd'] = {
                item['ecc_cocd']: item['s4_cocd']
                for item in parsed['cocd']
                if 'ecc_cocd' in item and 's4_cocd' in item
            }

        # Reconstruct plant_loc map
        if 'plant_loc' in parsed:
            custom_maps['plant_loc'] = {}
            for item in parsed['plant_loc']:
                if all(k in item for k in ('ecc_plant', 'ecc_location', 's4_plant', 's4_location')):
                    try:
                        # Normalize plant keys (as ints where possible)
                        p_key = int(float(item['ecc_plant']))
                    except (ValueError, TypeError):
                        p_key = str(item['ecc_plant']).strip()
                    l_key = str(item['ecc_location']).strip().upper()
                    custom_maps['plant_loc'][(p_key, l_key)] = {
                        "s4_plant": item['s4_plant'],
                        "s4_location": item['s4_location']
                    }

        # Reconstruct cost center map
        if 'cost_center' in parsed:
            custom_maps['cost_center'] = {}
            for item in parsed['cost_center']:
                if 'ecc_cost_center' in item and 's4_cost_center' in item:
                    try:
                        cc_key = int(float(item['ecc_cost_center']))
                    except (ValueError, TypeError):
                        cc_key = str(item['ecc_cost_center']).strip()
                    custom_maps['cost_center'][cc_key] = item['s4_cost_center']

        return custom_maps
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse custom mappings JSON: {str(e)}")


@app.post("/process-asset")
async def process_asset(
    file: UploadFile = File(...),
    mappings_json: str = Form(None)
):
    """
    POST endpoint that intakes the Registry excel file and returns the
    populated S/4 HANA assets_load_template file.
    """
    # Verify file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")

    custom_maps = parse_custom_mappings(mappings_json)

    try:
        # Read uploaded file into memory
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)
       
        # Process the registry
        out_buf, validation_errors = process_asset_registry(
            reg_io,
            template_path=TEMPLATE_PATH,
            custom_mappings=custom_maps
        )
       
        # Return populated template. The file is fully written regardless
        # of validation issues — X-Validation-Error-Count lets the frontend
        # know at a glance whether it should also call /validate-asset for
        # the details, without a second round trip just to find out.
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
        # Wrong file for this process (e.g. a Credit or AP registry was
        # uploaded while "Assets" was selected) — a 400, not a 500, since
        # it's a bad request rather than a server-side failure.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing asset registry: {str(e)}")


@app.post("/validate-asset")
async def validate_asset(
    file: UploadFile = File(...),
    mappings_json: str = Form(None)
):
    """
    POST endpoint that runs the exact same mapping logic as /process-asset
    but returns a JSON validation report instead of the file itself: one
    entry per (sheet, mandatory column) that has at least one missing row,
    with a ready-to-display message so the frontend doesn't have to build
    its own copy.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")

    custom_maps = parse_custom_mappings(mappings_json)

    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        _out_buf, validation_errors = process_asset_registry(
            reg_io,
            template_path=TEMPLATE_PATH,
            custom_mappings=custom_maps
        )

        # Collapse row-level errors down to one count per (sheet, column) —
        # that's all the frontend needs to show per your spec.
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

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
    except AssetMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error validating asset registry: {str(e)}")

@app.post("/process-credit")
async def process_credit(
    file: UploadFile = File(...)
):
    """
    POST endpoint that takes the Credit Registry Excel file
    and returns the populated Credit Data Load template.
    """

    # Verify file type
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx, .xls) are accepted."
        )

    try:
        # Read uploaded registry file into memory
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        # Process Credit Registry
        out_buf, validation_errors = process_credit_registry(
            reg_io,
            template_path=CREDIT_TEMPLATE_PATH
        )

        # Return populated Credit Data Load template. The file is written
        # regardless of validation issues — X-Validation-Error-Count lets
        # the frontend know at a glance whether to also call
        # /validate-credit for the details.
        return StreamingResponse(
            out_buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                    "attachment; filename=credit_data_load_filled.xlsx",
                "X-Validation-Error-Count": str(len(validation_errors)),
                "Access-Control-Expose-Headers": "X-Validation-Error-Count",
            }
        )

    except CreditMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error processing credit registry: {str(e)}"
        )


@app.post("/validate-credit")
async def validate_credit(
    file: UploadFile = File(...)
):
    """
    POST endpoint that runs the exact same mapping logic as /process-credit
    but returns a JSON validation report instead of the file itself: one
    entry per (sheet, mandatory column) that has at least one missing row.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx, .xls) are accepted."
        )

    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        _out_buf, validation_errors = process_credit_registry(
            reg_io,
            template_path=CREDIT_TEMPLATE_PATH
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

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    except CreditMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error validating credit registry: {str(e)}"
        )

@app.post("/process-ap")
async def process_ap(
    file: UploadFile = File(...)
):
    """
    POST endpoint that takes the AP Registry Excel file
    and returns the populated AP Data Load template.
    """

    # Verify file type
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx, .xls) are accepted."
        )

    try:
        # Read uploaded AP Registry into memory
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        # Process AP Registry
        out_buf, validation_errors = process_ap_registry(
            reg_io,
            template_path=AP_TEMPLATE_PATH
        )

        # Return populated AP Data Load template. The file is written
        # regardless of validation issues — X-Validation-Error-Count lets
        # the frontend know at a glance whether to also call /validate-ap
        # for the details.
        return StreamingResponse(
            out_buf,
            media_type=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition":
                    "attachment; "
                    "filename=AP_Data_Load_SIT2_filled.xlsx",
                "X-Validation-Error-Count": str(len(validation_errors)),
                "Access-Control-Expose-Headers": "X-Validation-Error-Count",
            }
        )

    except APMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error processing AP registry: {str(e)}"
        )


@app.post("/validate-ap")
async def validate_ap(
    file: UploadFile = File(...)
):
    """
    POST endpoint that runs the exact same mapping logic as /process-ap
    but returns a JSON validation report instead of the file itself: one
    entry per (sheet, mandatory column) that has at least one missing row.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx, .xls) are accepted."
        )

    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        _out_buf, validation_errors = process_ap_registry(
            reg_io,
            template_path=AP_TEMPLATE_PATH
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

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    except APMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error validating AP registry: {str(e)}"
        )

@app.post("/process-ar")
async def process_ar(
    file: UploadFile = File(...)
):
    """
    POST endpoint that takes the AR Registry Excel file
    and returns the populated AR Data Load template.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx, .xls) are accepted."
        )

    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        out_buf, validation_errors = process_ar_registry(
            reg_io,
            template_path=AR_TEMPLATE_PATH
        )

        return StreamingResponse(
            out_buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=AR_Data_Load_filled.xlsx",
                "X-Validation-Error-Count": str(len(validation_errors)),
                "Access-Control-Expose-Headers": "X-Validation-Error-Count",
            }
        )

    except ARMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing AR registry: {str(e)}"
        )


# NEW: validate-ar endpoint
@app.post("/validate-ar")
async def validate_ar(
    file: UploadFile = File(...)
):
    """
    POST endpoint that runs the same mapping logic as /process-ar
    but returns a JSON validation report instead of the file.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx, .xls) are accepted."
        )

    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        _out_buf, validation_errors = process_ar_registry(
            reg_io,
            template_path=AR_TEMPLATE_PATH
        )

        # Collapse errors per sheet and field_label (like the other validators)
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

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    except ARMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error validating AR registry: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) 