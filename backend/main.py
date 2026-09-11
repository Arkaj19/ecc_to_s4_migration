from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.fico.api.ap_router import router as ap_router
from backend.fico.api.ar_router import router as ar_router
from backend.fico.api.credit_router import router as credit_router
from backend.fico.api.asset_router import router as asset_router
from backend.fico.repo import mappings

from backend.inventory.api.inventory_router import router as inventory_router

app = FastAPI(title="ECC to S/4 HANA fico Data Migrator Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ap_router)
app.include_router(ar_router)
app.include_router(credit_router)
app.include_router(asset_router)

app.include_router(inventory_router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ecc_to_s4_migrator_backend"}


@app.get("/default-mappings")
def get_default_mappings():
    """Returns the prebuilt mappings seeded in Python."""
    cocd_list = [
        {"ecc_cocd": k, "s4_cocd": v}
        for k, v in mappings.COMPANY_CODE_MAPPING.items()
    ]

    plant_loc_list = [
        {
            "ecc_plant": int(k[0]) if isinstance(k[0], (int, float)) else k[0],
            "ecc_location": k[1],
            "s4_plant": v["s4_plant"],
            "s4_location": v["s4_location"]
        }
        for k, v in mappings.PLANT_LOCATION_MAPPING.items()
    ]

    cost_center_list = [
        {"ecc_cost_center": int(k) if isinstance(k, (int, float)) else k, "s4_cost_center": v}
        for k, v in mappings.COST_CENTER_OVERRIDES.items()
    ]

    return {
        "cocd": cocd_list,
        "plant_loc": plant_loc_list,
        "cost_center": cost_center_list
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)