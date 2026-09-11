from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, Response
import io
import os
import shutil
import tempfile
import uuid

from backend.config import TEMPLATES_DIR
from backend.fico.services import session_store
from backend.fico.services.ar_processor import (
    process_ar_registry,
    RegistryMismatchError as ARMismatchError,
    CurrencyReviewRequiredError,
)
from backend.fico.services.ar_validator import validate_ar_files
from backend.fico.services.report_generator import generate_ar_validation_report
from backend.fico.schemas.ar_schemas import ARCurrencyReviewResponse, ARValidationResponse

router = APIRouter(tags=["Accounts Receivable"])

AR_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "AR_TEMPLATE.xlsx")
AR_CURRENCY_DUMP_FILENAME = "AR_Currency_Mismatch_Deleted.xlsx"
AR_REPORT_FILENAME = "AR_Validation_Report.pdf"
AR_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/process-ar")
async def process_ar(
    file: UploadFile = File(...),
    currency_action: str = Form(None),
):
    """
    POST endpoint that takes the AR Registry Excel file and returns the
    populated AR Data Load template.

    If the registry contains company-code / currency mismatches and no
    `currency_action` was supplied, no file is generated — a JSON review
    payload is returned instead so the frontend can prompt the user to
    choose "keep" (highlight mismatches red) or "delete" (drop the rows,
    available via /download-ar-currency-dump/{download_id}, using the
    `X-Currency-Dump-Download-Id` header returned here). Re-call with the
    chosen `currency_action` to proceed.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted.")

    try:
        file_bytes = await file.read()
        reg_io = io.BytesIO(file_bytes)

        out_buf, validation_errors = process_ar_registry(
            reg_io,
            template_path=AR_TEMPLATE_PATH,
            currency_action=currency_action,
        )

        currency_review = getattr(out_buf, "currency_review", None)
        response_headers = {
            "Content-Disposition": "attachment; filename=AR_Data_Load_filled.xlsx",
            "X-Validation-Error-Count": str(len(validation_errors)),
        }

        if currency_review:
            dump_buffer = currency_review.get("dump_buffer")
            if dump_buffer is not None:
                # Keyed by a fresh download_id per run instead of a fixed
                # shared path, so concurrent runs can't clobber each
                # other's dump file.
                dump_download_id = session_store.put_download(
                    dump_buffer.getvalue(), AR_CURRENCY_DUMP_FILENAME, AR_XLSX_MEDIA_TYPE,
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

        return StreamingResponse(
            out_buf,
            media_type=AR_XLSX_MEDIA_TYPE,
            headers=response_headers,
        )

    except CurrencyReviewRequiredError as e:
        return ARCurrencyReviewResponse(**e.review_payload)
    except ARMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing AR registry: {str(e)}")


@router.get("/download-ar-currency-dump/{download_id}")
async def download_ar_currency_dump(download_id: str):
    """
    Downloads the Excel file of rows removed from a specific AR
    migration run because of a company code / currency mismatch (only
    produced when /process-ar was called with currency_action="delete").
    The `download_id` comes from that run's `X-Currency-Dump-Download-Id`
    response header.
    """
    entry = session_store.get_download(download_id)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="No deleted-records file found for that download_id. It may have expired — re-run "
                   "/process-ar with currency_action=\"delete\" and use the new download_id.",
        )

    return Response(
        content=entry["data"],
        media_type=entry["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{entry["filename"]}"'},
    )


@router.post("/validate-ar", response_model=ARValidationResponse)
async def validate_ar(
    registry_file: UploadFile = File(...),
    filled_file: UploadFile = File(...)
):
    """
    Validate an ECC AR registry against the previously generated
    S/4 Customer Open Items file.
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

        result = validate_ar_files(
            registry_file=registry_io,
            filled_file=filled_io,
        )

        # Render the PDF into a run-scoped temp dir (not a fixed shared
        # path) so two validations running at once can't clobber each
        # other's report or intermediate chart PNGs, then move the
        # finished bytes into the session_store and throw the temp dir
        # away — nothing generated by this run is left on disk.
        run_dir = tempfile.mkdtemp(prefix=f"ar_report_{uuid.uuid4().hex}_")
        try:
            report_path = os.path.join(run_dir, AR_REPORT_FILENAME)
            generate_ar_validation_report(
                validation_payload=result,
                output_path=report_path,
                source_file_name=registry_file.filename,
                target_file_name=filled_file.filename,
            )
            with open(report_path, "rb") as f:
                report_bytes = f.read()
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

        report_download_id = session_store.put_download(
            report_bytes, AR_REPORT_FILENAME, "application/pdf",
        )

        result["report_available"] = True
        result["report_file"] = AR_REPORT_FILENAME
        result["report_download_id"] = report_download_id

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error validating AR files: {str(e)}")


@router.get("/download-ar-report/{download_id}")
async def download_ar_report(download_id: str):
    """
    Downloads a specific AR validation report. The `download_id` comes
    from that run's `report_download_id` field in the /validate-ar
    response.
    """
    entry = session_store.get_download(download_id)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="No AR validation report found for that download_id. It may have expired — re-run "
                   "/validate-ar and use the new download_id.",
        )

    return Response(
        content=entry["data"],
        media_type=entry["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{entry["filename"]}"'},
    )
