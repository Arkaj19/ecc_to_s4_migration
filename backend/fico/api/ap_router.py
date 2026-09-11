from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, Response
import io
import os
import shutil
import tempfile
import uuid

from backend.config import TEMPLATES_DIR
from backend.fico.services import session_store
from backend.fico.services.ap_processor import (
    process_ap_registry,
    RegistryMismatchError as APMismatchError,
    CurrencyReviewRequiredError as APCurrencyReviewRequiredError,
)
from backend.fico.services.ap_validator import validate_ap_files
from backend.fico.services.report_generator import generate_ap_validation_report
from backend.fico.schemas.ap_schemas import APCurrencyReviewResponse, APValidationResponse

router = APIRouter(tags=["Accounts Payable"])  # no prefix — keeps your existing URLs unchanged

AP_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "AP Data Load Sheet - SIT2.xlsx")
AP_CURRENCY_DUMP_FILENAME = "AP_Currency_Mismatch_Deleted.xlsx"
AP_REPORT_FILENAME = "AP_Validation_Report.pdf"
AP_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/process-ap")
async def process_ap(file: UploadFile = File(...), currency_action: str = Form(None)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")
    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)
        out_buf, validation_errors = process_ap_registry(
            reg_io, template_path=AP_TEMPLATE_PATH, currency_action=currency_action,
        )
        currency_review = getattr(out_buf, "currency_review", None)
        response_headers = {
            "Content-Disposition": "attachment; filename=AP_Data_Load_SIT2_filled.xlsx",
            "X-Validation-Error-Count": str(len(validation_errors)),
        }
        if currency_review:
            dump_buffer = currency_review.get("dump_buffer")
            if dump_buffer is not None:
                # Fresh download_id per run instead of a fixed shared
                # path, so concurrent runs can't clobber each other's
                # dump file.
                dump_download_id = session_store.put_download(
                    dump_buffer.getvalue(), AP_CURRENCY_DUMP_FILENAME, AP_XLSX_MEDIA_TYPE,
                )
                response_headers["X-Currency-Dump-Download-Id"] = dump_download_id
            response_headers.update({
                "X-Currency-Review-Status": currency_review["status"],
                "X-Currency-Action": str(currency_review["action"] or ""),
                "X-Currency-Mismatch-Count": str(currency_review["mismatch_count"]),
                "X-Currency-Dump-Rows": str(currency_review["dump_rows"]),
                "X-Currency-Retained-Rows": str(currency_review["retained_rows"]),
                "X-Currency-Dump-Available": str(currency_review.get("dump_buffer") is not None),
            })
        response_headers["Access-Control-Expose-Headers"] = ", ".join(response_headers.keys())
        return StreamingResponse(out_buf, media_type=AP_XLSX_MEDIA_TYPE, headers=response_headers)
    except APCurrencyReviewRequiredError as e:
        return APCurrencyReviewResponse(**e.review_payload)
    except APMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing AP registry: {str(e)}")


@router.get("/download-ap-currency-dump/{download_id}")
async def download_ap_currency_dump(download_id: str):
    """
    The `download_id` comes from that run's `X-Currency-Dump-Download-Id`
    response header (only produced when /process-ap was called with
    currency_action="delete").
    """
    entry = session_store.get_download(download_id)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="No deleted-records file found for that download_id. It may have expired — re-run "
                   "/process-ap with currency_action=\"DELETE\" and use the new download_id.",
        )
    return Response(
        content=entry["data"],
        media_type=entry["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{entry["filename"]}"'},
    )


@router.get("/download-ap-report/{download_id}")
async def download_ap_report(download_id: str):
    """The `download_id` comes from `report_download_id` in the /validate-ap-reconciliation response."""
    entry = session_store.get_download(download_id)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="No AP validation report found for that download_id. It may have expired — re-run "
                   "/validate-ap-reconciliation and use the new download_id.",
        )
    return Response(
        content=entry["data"],
        media_type=entry["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{entry["filename"]}"'},
    )


@router.post("/validate-ap-reconciliation", response_model=APValidationResponse)
async def validate_ap_reconciliation(registry_file: UploadFile = File(...), filled_file: UploadFile = File(...)):
    if not registry_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="ECC registry must be an Excel file (.xlsx or .xls).")
    if not filled_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="S/4 filled file must be an Excel file (.xlsx or .xls).")
    try:
        registry_io = io.BytesIO(await registry_file.read())
        filled_io = io.BytesIO(await filled_file.read())
        result = validate_ap_files(registry_file=registry_io, filled_file=filled_io)

        # Run-scoped temp dir instead of a fixed shared path — two
        # validations running at once can't clobber each other's PDF or
        # intermediate chart PNGs, and nothing is left on disk afterward.
        run_dir = tempfile.mkdtemp(prefix=f"ap_report_{uuid.uuid4().hex}_")
        try:
            report_path = os.path.join(run_dir, AP_REPORT_FILENAME)
            generate_ap_validation_report(
                validation_payload=result, output_path=report_path,
                source_file_name=registry_file.filename, target_file_name=filled_file.filename,
            )
            with open(report_path, "rb") as f:
                report_bytes = f.read()
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

        report_download_id = session_store.put_download(report_bytes, AP_REPORT_FILENAME, "application/pdf")

        result["report_available"] = True
        result["report_file"] = AP_REPORT_FILENAME
        result["report_download_id"] = report_download_id
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error validating AP files: {str(e)}")
