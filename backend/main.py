# # backend/main.py

# from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# from fastapi.responses import StreamingResponse
# import json
# import io
# from processor import process_asset_registry
# import mappings
# import os

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# TEMPLATE_PATH = os.path.join(
#     BASE_DIR,
#     "templates",
#     "assets_load_template.xlsx"
# )


# app = FastAPI(title="ECC to S/4 HANA FICO Data Migrator Backend")

# @app.get("/health")
# def health_check():
#     return {"status": "healthy", "service": "ecc_to_s4_migrator_backend"}

# @app.get("/default-mappings")
# def get_default_mappings():
#     """Returns the prebuilt mappings seeded in Python."""
#     # Convert company code mappings to list format for easier frontend editing
#     cocd_list = [
#         {"ecc_cocd": k, "s4_cocd": v}
#         for k, v in mappings.COMPANY_CODE_MAPPING.items()
#     ]
    
#     # Convert plant & location mappings to list
#     plant_loc_list = [
#         {
#             "ecc_plant": int(k[0]) if isinstance(k[0], (int, float)) else k[0],
#             "ecc_location": k[1],
#             "s4_plant": v["s4_plant"],
#             "s4_location": v["s4_location"]
#         }
#         for k, v in mappings.PLANT_LOCATION_MAPPING.items()
#     ]
    
#     # Convert cost center overrides to list
#     cost_center_list = [
#         {"ecc_cost_center": int(k) if isinstance(k, (int, float)) else k, "s4_cost_center": v}
#         for k, v in mappings.COST_CENTER_OVERRIDES.items()
#     ]
    
#     return {
#         "cocd": cocd_list,
#         "plant_loc": plant_loc_list,
#         "cost_center": cost_center_list
#     }

# @app.post("/process-asset")
# async def process_asset(
#     file: UploadFile = File(...),
#     mappings_json: str = Form(None)
# ):
#     """
#     POST endpoint that intakes the Registry excel file and returns the 
#     populated S/4 HANA assets_load_template file.
#     """
#     # Verify file type
#     if not file.filename.endswith(('.xlsx', '.xls')):
#         raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")
    
#     # Parse custom mappings if provided
#     custom_maps = None
#     if mappings_json:
#         try:
#             parsed = json.loads(mappings_json)
#             custom_maps = {}
            
#             # Reconstruct cocd map
#             if 'cocd' in parsed:
#                 custom_maps['cocd'] = {
#                     item['ecc_cocd']: item['s4_cocd'] 
#                     for item in parsed['cocd'] 
#                     if 'ecc_cocd' in item and 's4_cocd' in item
#                 }
                
#             # Reconstruct plant_loc map
#             if 'plant_loc' in parsed:
#                 custom_maps['plant_loc'] = {}
#                 for item in parsed['plant_loc']:
#                     if all(k in item for k in ('ecc_plant', 'ecc_location', 's4_plant', 's4_location')):
#                         try:
#                             # Normalize plant keys (as ints where possible)
#                             p_key = int(float(item['ecc_plant']))
#                         except (ValueError, TypeError):
#                             p_key = str(item['ecc_plant']).strip()
#                         l_key = str(item['ecc_location']).strip().upper()
#                         custom_maps['plant_loc'][(p_key, l_key)] = {
#                             "s4_plant": item['s4_plant'],
#                             "s4_location": item['s4_location']
#                         }
                        
#             # Reconstruct cost center map
#             if 'cost_center' in parsed:
#                 custom_maps['cost_center'] = {}
#                 for item in parsed['cost_center']:
#                     if 'ecc_cost_center' in item and 's4_cost_center' in item:
#                         try:
#                             cc_key = int(float(item['ecc_cost_center']))
#                         except (ValueError, TypeError):
#                             cc_key = str(item['ecc_cost_center']).strip()
#                         custom_maps['cost_center'][cc_key] = item['s4_cost_center']
                        
#         except Exception as e:
#             raise HTTPException(status_code=400, detail=f"Failed to parse custom mappings JSON: {str(e)}")

#     try:
#         # Read uploaded file into memory
#         file_bytes = await file.read()
#         reg_io = io.BytesIO(file_bytes)
        
#         # Process the registry
#         out_buf = process_asset_registry(
#             reg_io,
#             template_path=TEMPLATE_PATH,
#             custom_mappings=custom_maps
#         )
        
#         # Return populated template
#         return StreamingResponse(
#             out_buf,
#             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             headers={"Content-Disposition": f"attachment; filename=assets_load_template_filled.xlsx"}
#         )
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Error processing asset registry: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000)

# backend/main.py
 
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import io
from asset_processor import process_asset_registry
from credit_processor import process_credit_registry
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
   
    # Parse custom mappings if provided
    custom_maps = None
    if mappings_json:
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
                       
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse custom mappings JSON: {str(e)}")
 
    try:
        # Read uploaded file into memory
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)
       
        # Process the registry
        out_buf = process_asset_registry(
            reg_io,
            template_path=TEMPLATE_PATH,
            custom_mappings=custom_maps
        )
       
        # Return populated template
        return StreamingResponse(
            out_buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=assets_load_template_filled.xlsx"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing asset registry: {str(e)}")

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
        out_buf = process_credit_registry(
            reg_io,
            template_path=CREDIT_TEMPLATE_PATH
        )

        # Return populated Credit Data Load template
        return StreamingResponse(
            out_buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                    "attachment; filename=credit_data_load_filled.xlsx"
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error processing credit registry: {str(e)}"
        )
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
 