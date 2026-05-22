import logging
import os
import threading
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from reconciler import run_reconciliation

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reconciliación Contable API")

origins = os.getenv("CORS_ORIGINS", "http://localhost").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_static_dir = Path(__file__).parent / "static"
_index_html = _static_dir / "index.html"

# In-memory store with TTL and size limit
_download_store: Dict[str, Tuple[bytes, float]] = {}
_store_lock = threading.Lock()
_MAX_ENTRIES = 50
_TTL_SECONDS = 300  # 5 minutes
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _validate_excel_magic(data: bytes, ext: str) -> bool:
    if ext == ".xlsx":
        return data[:4] == b"PK\x03\x04"
    elif ext == ".xls":
        return data[:8] == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
    return False


def _store_put(token: str, data: bytes):
    with _store_lock:
        now = time.monotonic()
        expired = [k for k, (_, ts) in _download_store.items() if now - ts > _TTL_SECONDS]
        for k in expired:
            del _download_store[k]
        if len(_download_store) >= _MAX_ENTRIES:
            raise HTTPException(503, "Servidor ocupado, intente en unos minutos")
        _download_store[token] = (data, now)


def _store_pop(token: str) -> bytes | None:
    with _store_lock:
        entry = _download_store.pop(token, None)
        if entry is None:
            return None
        data, ts = entry
        if time.monotonic() - ts > _TTL_SECONDS:
            return None
        return data


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

    if naos_ext not in (".xls", ".xlsx"):
        raise HTTPException(status_code=400, detail="Archivo NAOS debe ser .xls o .xlsx")
    if exact_ext not in (".xls", ".xlsx"):
        raise HTTPException(status_code=400, detail="Archivo EXACT debe ser .xls o .xlsx")

    if len(naos_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Archivo NAOS supera el límite de 10 MB")
    if len(exact_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Archivo EXACT supera el límite de 10 MB")

    if not _validate_excel_magic(naos_bytes, naos_ext):
        raise HTTPException(status_code=400, detail="El contenido del archivo NAOS no es un Excel válido")
    if not _validate_excel_magic(exact_bytes, exact_ext):
        raise HTTPException(status_code=400, detail="El contenido del archivo EXACT no es un Excel válido")

    try:
        excel_io, date_summary = run_reconciliation(naos_bytes, exact_bytes, naos_ext, exact_ext)
    except Exception:
        logger.exception("Error en reconciliación")
        raise HTTPException(
            status_code=500,
            detail="Error procesando los archivos. Verifique que los archivos sean válidos y tengan el formato esperado.",
        )

    token = str(uuid.uuid4())
    _store_put(token, excel_io.getvalue())

    total_dates = len(date_summary)
    matched_dates = sum(1 for d in date_summary if d["cuadra"])
    diff_dates = total_dates - matched_dates
    total_diff = round(sum(d["diferencia"] for d in date_summary), 2)

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
    data = _store_pop(token)
    if data is None:
        raise HTTPException(status_code=404, detail="Token no encontrado o expirado")

    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reconciliacion_resultado.xlsx"},
    )
