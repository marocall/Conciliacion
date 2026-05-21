"""Tests for FastAPI endpoints in main.py."""
import sys
import os
import io
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_returns_ok():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /api/reconcile
# ---------------------------------------------------------------------------

class TestReconcileEndpoint:
    def test_rejects_missing_files(self):
        res = client.post("/api/reconcile")
        assert res.status_code == 422

    def test_rejects_non_excel_naos(self, exact_bytes):
        res = client.post(
            "/api/reconcile",
            files={
                "naos_file": ("naos.txt", b"not an xlsx", "text/plain"),
                "exact_file": ("exact.xlsx", exact_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            },
        )
        assert res.status_code == 400
        assert "NAOS" in res.json()["detail"]

    def test_rejects_non_excel_exact(self, naos_bytes):
        res = client.post(
            "/api/reconcile",
            files={
                "naos_file": ("naos.xlsx", naos_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "exact_file": ("exact.csv", b"a,b,c", "text/csv"),
            },
        )
        assert res.status_code == 400
        assert "EXACT" in res.json()["detail"]

    def test_returns_expected_json_fields(self, naos_bytes, exact_bytes):
        res = client.post(
            "/api/reconcile",
            files={
                "naos_file": ("naos.xlsx", naos_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "exact_file": ("exact.xlsx", exact_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            },
        )
        assert res.status_code == 200
        body = res.json()
        for key in ("summary", "totalDates", "matchedDates", "diffDates", "totalDiff", "download_token"):
            assert key in body, f"Missing key: {key}"

    def test_download_token_is_string(self, naos_bytes, exact_bytes):
        res = client.post(
            "/api/reconcile",
            files={
                "naos_file": ("naos.xlsx", naos_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "exact_file": ("exact.xlsx", exact_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            },
        )
        assert isinstance(res.json()["download_token"], str)
        assert len(res.json()["download_token"]) > 0

    def test_total_dates_matches_summary_length(self, naos_bytes, exact_bytes):
        res = client.post(
            "/api/reconcile",
            files={
                "naos_file": ("naos.xlsx", naos_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "exact_file": ("exact.xlsx", exact_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            },
        )
        body = res.json()
        assert body["totalDates"] == len(body["summary"])


# ---------------------------------------------------------------------------
# /api/download/{token}
# ---------------------------------------------------------------------------

class TestDownloadEndpoint:
    def test_download_returns_xlsx(self, naos_bytes, exact_bytes):
        rec = client.post(
            "/api/reconcile",
            files={
                "naos_file": ("naos.xlsx", naos_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "exact_file": ("exact.xlsx", exact_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            },
        )
        token = rec.json()["download_token"]
        dl = client.get(f"/api/download/{token}")
        assert dl.status_code == 200
        assert "spreadsheetml" in dl.headers["content-type"]
        assert dl.content[:4] == b"PK\x03\x04"

    def test_download_invalid_token_returns_404(self):
        res = client.get("/api/download/nonexistent-token-xyz")
        assert res.status_code == 404

    def test_download_filename_header(self, naos_bytes, exact_bytes):
        rec = client.post(
            "/api/reconcile",
            files={
                "naos_file": ("naos.xlsx", naos_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "exact_file": ("exact.xlsx", exact_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            },
        )
        token = rec.json()["download_token"]
        dl = client.get(f"/api/download/{token}")
        assert "reconciliacion_resultado.xlsx" in dl.headers.get("content-disposition", "")
