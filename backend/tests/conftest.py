"""Shared fixtures for backend tests."""
import io
import pytest
from openpyxl import Workbook


def _make_naos_xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append([
        "fecha_apunte", "referencia", "signo_co", "importe_eu",
        "cuenta_co", "concepto_co", "ampliacion", "diario_co",
        "asiento", "periodo", "orden",
    ])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_exact_xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for _ in range(13):
        ws.append([])
    ws.append(["Día de informe", "Descripción", "Debe EUR", "Haber EUR"])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def naos_bytes():
    return _make_naos_xlsx([
        ["15/01/2024", "L12345", "D", 1000.00, "400001", "ARRENDAMIENTO", "LOCAL A",    "01", "AS001", "202401", "1"],
        ["15/01/2024", "R67890", "H",  500.00, "400002", "DEVOLUCION",    "DEV ENERO",  "01", "AS002", "202401", "2"],
        ["16/01/2024", "L11111", "D",  250.00, "400001", "ARRENDAMIENTO", "LOCAL B",    "01", "AS003", "202401", "3"],
    ])


@pytest.fixture
def exact_bytes():
    return _make_exact_xlsx([
        ["15/01/2024", "ARRENDAMIENTO LOCAL A REF:L12345 - AS:AS001", 1000.00, 0],
        ["15/01/2024", "DEVOLUCION REF:R67890 - AS:AS002",            0,       500.00],
        ["16/01/2024", "ARRENDAMIENTO LOCAL B REF:L11111 - AS:AS003",  300.00, 0],
    ])


@pytest.fixture
def naos_bytes_balanced():
    """NAOS + EXACT that should reconcile perfectly (zero diff)."""
    return _make_naos_xlsx([
        ["15/01/2024", "L12345", "D", 1000.00, "400001", "ARREND", "LOCAL A", "01", "AS001", "202401", "1"],
    ])


@pytest.fixture
def exact_bytes_balanced():
    return _make_exact_xlsx([
        ["15/01/2024", "ARREND LOCAL A REF:L12345 - AS:AS001", 1000.00, 0],
    ])
