from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, Response
import io
import os
import shutil
import tempfile
import uuid

from backend.config import TEMPLATES_DIR
from backend.fico.services import session_store
from backend.fico.services.credit_processor import (
    process_credit_registry,
    RegistryMismatchError as CreditMismatchError,
)
from backend.fico.services.credit_validator import validate_credit_files
from backend.fico.services.report_generator import generate_credit_validation_report
from backend.fico.schemas.credit_schemas import CreditFieldValidationResponse, CreditValidationResponse

router = APIRouter(tags=["Credit"])

CREDIT_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "Credit Data Load - SIT2.xlsx")
CREDIT_REPORT_FILENAME = "Credit_Validation_Report.pdf"


@router.post("/process-credit")
async def process_credit(
    file: UploadFile = File(...)
):
    """
    POST endpoint that takes the Credit Registry Excel file
    and returns the populated Credit Data Load template.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")

    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        out_buf, validation_errors = process_credit_registry(
            reg_io,
            template_path=CREDIT_TEMPLATE_PATH
        )

        return StreamingResponse(
            out_buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=credit_data_load_filled.xlsx",
                "X-Validation-Error-Count": str(len(validation_errors)),
                "Access-Control-Expose-Headers": "X-Validation-Error-Count",
            }
        )

    except CreditMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing credit registry: {str(e)}")


@router.post("/validate-credit", response_model=CreditFieldValidationResponse)
async def validate_credit(
    file: UploadFile = File(...)
):
    """
    POST endpoint that runs the exact same mapping logic as /process-credit
    but returns a JSON validation report instead of the file itself.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")

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
        raise HTTPException(status_code=500, detail=f"Error validating credit registry: {str(e)}")


@router.get("/download-credit-report/{download_id}")
async def download_credit_report(download_id: str):
    """The `download_id` comes from `report_download_id` in the /validate-credit-reconciliation response."""
    entry = session_store.get_download(download_id)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="No Credit validation report found for that download_id. It may have expired — re-run "
                   "/validate-credit-reconciliation and use the new download_id.",
        )

    return Response(
        content=entry["data"],
        media_type=entry["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{entry["filename"]}"'},
    )


@router.post("/validate-credit-reconciliation", response_model=CreditValidationResponse)
async def validate_credit_reconciliation(
    registry_file: UploadFile = File(...),
    filled_file: UploadFile = File(...)
):
    """
    Validate an ECC Credit registry against the previously generated
    S/4 Profile - Credit MD for Cust. file.

    Runs the two reconciliation checks defined in credit_validator.py:
      1. Credit Rep Group Distribution
      2. Company Code Distribution
    """
    if not registry_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="ECC registry must be an Excel file (.xlsx or .xls).")

    if not filled_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="S/4 filled file must be an Excel file (.xlsx or .xls).")

    try:
        registry_bytes = await registry_file.read()
        filled_bytes = await filled_file.read()

        registry_io = io.BytesIO(registry_bytes)
        filled_io = io.BytesIO(filled_bytes)

        result = validate_credit_files(
            registry_file=registry_io,
            filled_file=filled_io,
        )

        # Run-scoped temp dir instead of a fixed shared path — two
        # validations running at once can't clobber each other's PDF or
        # intermediate chart PNGs, and nothing is left on disk afterward.
        run_dir = tempfile.mkdtemp(prefix=f"credit_report_{uuid.uuid4().hex}_")
        try:
            report_path = os.path.join(run_dir, CREDIT_REPORT_FILENAME)
            generate_credit_validation_report(
                validation_payload=result,
                output_path=report_path,
                source_file_name=registry_file.filename,
                target_file_name=filled_file.filename,
            )
            with open(report_path, "rb") as f:
                report_bytes = f.read()
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

        report_download_id = session_store.put_download(report_bytes, CREDIT_REPORT_FILENAME, "application/pdf")

        result["report_available"] = True
        result["report_file"] = CREDIT_REPORT_FILENAME
        result["report_download_id"] = report_download_id

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error validating Credit files: {str(e)}")
