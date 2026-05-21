"""Generate minimal xlsx fixtures for Playwright E2E tests."""
import os
from openpyxl import Workbook

out = os.path.dirname(os.path.abspath(__file__))

# --- NAOS sample ---
wb = Workbook()
ws = wb.active
ws.title = "Hoja1"
ws.append([
    "fecha_apunte", "referencia", "signo_co", "importe_eu",
    "cuenta_co", "concepto_co", "ampliacion", "diario_co",
    "asiento", "periodo", "orden",
])
ws.append(["15/01/2024", "L12345", "D", 1000.00, "400001", "ARRENDAMIENTO", "LOCAL A - ENERO", "01", "AS001", "202401", "1"])
ws.append(["15/01/2024", "R67890", "H",  500.00, "400002", "DEVOLUCION",    "DEV ENERO",      "01", "AS002", "202401", "2"])
ws.append(["16/01/2024", "L11111", "D",  250.00, "400001", "ARRENDAMIENTO", "LOCAL B - ENERO", "01", "AS003", "202401", "3"])
wb.save(os.path.join(out, "naos-sample.xlsx"))
print("Created naos-sample.xlsx")

# --- EXACT sample ---
wb2 = Workbook()
ws2 = wb2.active
ws2.title = "Sheet1"
# EXACT format: 13 metadata rows before the real header
for _ in range(13):
    ws2.append([])
ws2.append(["Día de informe", "Descripción", "Debe EUR", "Haber EUR"])
ws2.append(["15/01/2024", "ARRENDAMIENTO LOCAL A REF:L12345 - AS:AS001", 1000.00, 0])
ws2.append(["15/01/2024", "DEVOLUCION REF:R67890 - AS:AS002",            0,       500.00])
ws2.append(["16/01/2024", "ARRENDAMIENTO LOCAL B REF:L11111 - AS:AS003", 300.00,  0])
wb2.save(os.path.join(out, "exact-sample.xlsx"))
print("Created exact-sample.xlsx")
