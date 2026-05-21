import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from reconciler import run_reconciliation

load_dotenv()

app = FastAPI(title="Reconciliación Contable API")

origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_static_dir = Path(__file__).parent / "static"
_index_html = _static_dir / "index.html"

# In-memory store for download tokens
_download_store: Dict[str, bytes] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(str(_index_html))


@app.post("/api/reconcile")
async def reconcile(
    naos_file: UploadFile = File(...),
    exact_file: UploadFile = File(...),
):
    naos_bytes = await naos_file.read()
    exact_bytes = await exact_file.read()

    naos_name = naos_file.filename or "naos.xlsx"
    exact_name = exact_file.filename or "exact.xlsx"

    naos_ext = os.path.splitext(naos_name)[1].lower()
    exact_ext = os.path.splitext(exact_name)[1].lower()

    if naos_ext not in ('.xls', '.xlsx'):
        raise HTTPException(status_code=400, detail="Archivo NAOS debe ser .xls o .xlsx")
    if exact_ext not in ('.xls', '.xlsx'):
        raise HTTPException(status_code=400, detail="Archivo EXACT debe ser .xls o .xlsx")

    try:
        excel_io, date_summary = run_reconciliation(naos_bytes, exact_bytes, naos_ext, exact_ext)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en reconciliación: {str(exc)}")

    token = str(uuid.uuid4())
    _download_store[token] = excel_io.getvalue()

    total_dates = len(date_summary)
    matched_dates = sum(1 for d in date_summary if d['cuadra'])
    diff_dates = total_dates - matched_dates
    total_diff = round(sum(d['diferencia'] for d in date_summary), 2)

    return JSONResponse({
        "summary": date_summary,
        "totalDates": total_dates,
        "matchedDates": matched_dates,
        "diffDates": diff_dates,
        "totalDiff": total_diff,
        "download_token": token,
    })


@app.get("/api/download/{token}")
def download(token: str):
    data = _download_store.get(token)
    if data is None:
        raise HTTPException(status_code=404, detail="Token no encontrado o expirado")

    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reconciliacion_resultado.xlsx"},
    )
