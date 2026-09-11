from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response

from ..schemas.inventory_schemas import UploadResponse, ValidateResponse
from ..services import session_store
from ..services.file_loader import load_from_bytes
from ..services.matching import run_match, build_excel_bytes, df_to_records

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.post("/upload", response_model=UploadResponse)
async def upload(ecc_file: UploadFile = File(...),
                 s4_file: UploadFile = File(...)):
    ecc_bytes = await ecc_file.read()
    s4_bytes  = await s4_file.read()
    if not ecc_bytes or not s4_bytes:
        raise HTTPException(400, "One or both files are empty.")

    sid = session_store.create_session(
        ecc_bytes, ecc_file.filename or "ecc",
        s4_bytes,  s4_file.filename or "s4",
    )
    return UploadResponse(
        session_id=sid,
        ecc_filename=ecc_file.filename or "ecc",
        s4_filename=s4_file.filename or "s4",
        message="Files uploaded. Ready to validate.",
    )


@router.post("/validate/{session_id}", response_model=ValidateResponse)
async def validate(session_id: str, sample_size: int = 50):
    sess = session_store.get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found or expired. Re-upload files.")

    try:
        ecc_df = load_from_bytes(sess["ecc"], sess["ecc_name"])
        s4_df  = load_from_bytes(sess["s4"],  sess["s4_name"])
    except Exception as e:
        raise HTTPException(400, f"Failed to parse files: {e}")

    try:
        ecc_out, s4_out, summary = run_match(ecc_df, s4_df, sample_size=sample_size)
    except KeyError as e:
        raise HTTPException(400, f"Missing expected column: {e}")
    except ValueError as e:
        raise HTTPException(422, str(e))

    xlsx = build_excel_bytes(ecc_out, s4_out)
    download_id = session_store.put_download(xlsx)

    return ValidateResponse(
        download_id=download_id,
        summary=summary,
        ecc_rows=df_to_records(ecc_out),
        s4_rows=df_to_records(s4_out),
        columns_ecc=list(ecc_out.columns),
        columns_s4=list(s4_out.columns),
    )


@router.get("/download/{download_id}")
async def download(download_id: str):
    data = session_store.get_download(download_id)
    if not data:
        raise HTTPException(404, "Download not found or expired.")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":
                 'attachment; filename="ecc_s4_50_sample.xlsx"'},
    )