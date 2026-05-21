import io
import re
import uuid
from collections import defaultdict
from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import (
    Alignment, Border, Font, PatternFill, Side
)
from openpyxl.utils import get_column_letter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_str(s):
    if not isinstance(s, str):
        try:
            s = str(s)
        except Exception:
            return ""
    return s.replace("_x0000_", "").replace("\x00", "").strip()


def norm_ref(r: str) -> str:
    r = _clean_str(r).strip()
    if re.match(r'^[LRF]\d+$', r):
        return r[1:]
    return r


def norm_desc(s: str) -> str:
    s = _clean_str(s)
    s = re.sub(r'[-/\s\(\)]', '', s).upper().strip()
    return s[:25]


def _thin_border():
    side = Side(style='thin', color='FFBFBFBF')
    return Border(left=side, right=side, top=side, bottom=side)


def _cell_fill(hex_color: str):
    return PatternFill(fill_type='solid', fgColor=hex_color)


# ---------------------------------------------------------------------------
# Load NAOS
# ---------------------------------------------------------------------------

def load_naos(data: bytes, ext: str) -> pd.DataFrame:
    engine = 'xlrd' if ext == '.xls' else 'openpyxl'
    df = pd.read_excel(io.BytesIO(data), engine=engine, dtype=str)

    # Clean all string columns
    df.columns = [_clean_str(c) for c in df.columns]
    for col in df.columns:
        df[col] = df[col].apply(_clean_str)

    # Normalize expected column names (lowercase)
    df.columns = [c.lower().strip() for c in df.columns]

    # Map common aliases
    aliases = {
        'ampliacion': ['ampliacion', 'ampliación', 'descripcion', 'descripción'],
        'referencia': ['referencia', 'ref'],
        'signo_co': ['signo_co', 'signo'],
        'asiento': ['asiento'],
        'cuenta_co': ['cuenta_co', 'cuenta'],
        'concepto_co': ['concepto_co', 'concepto'],
        'diario_co': ['diario_co', 'diario'],
        'fecha_apunte': ['fecha_apunte', 'fecha apunte', 'fecha'],
        'importe_eu': ['importe_eu', 'importe eu', 'importe_eur', 'importe eur', 'importe'],
        'periodo': ['periodo', 'período'],
        'orden': ['orden'],
    }
    rename_map = {}
    for canonical, options in aliases.items():
        if canonical not in df.columns:
            for opt in options:
                if opt in df.columns:
                    rename_map[opt] = canonical
                    break
    df.rename(columns=rename_map, inplace=True)

    df['importe_eu'] = pd.to_numeric(df.get('importe_eu', 0), errors='coerce').fillna(0)

    signo = df.get('signo_co', pd.Series(['D'] * len(df)))
    df['DEBE'] = df['importe_eu'].where(signo == 'D', 0)
    df['HABER'] = df['importe_eu'].where(signo == 'H', 0)
    df['SALDO'] = df['DEBE'] - df['HABER']

    # Normalize fecha
    fecha_col = 'fecha_apunte'
    if fecha_col in df.columns:
        df[fecha_col] = pd.to_datetime(df[fecha_col], dayfirst=True, errors='coerce')
    else:
        df[fecha_col] = pd.NaT

    df['ref_norm'] = df.get('referencia', pd.Series(['']*len(df))).apply(norm_ref)
    df['fecha_str'] = df[fecha_col].dt.strftime('%Y-%m-%d').fillna('')

    return df


# ---------------------------------------------------------------------------
# Load EXACT
# ---------------------------------------------------------------------------

def load_exact(data: bytes, ext: str) -> pd.DataFrame:
    engine = 'xlrd' if ext == '.xls' else 'openpyxl'

    # Detect header row containing 'Día de informe'
    raw = pd.read_excel(io.BytesIO(data), engine=engine, header=None, dtype=str)
    header_row = None
    for i, row in raw.iterrows():
        for cell in row:
            if isinstance(cell, str) and 'Día de informe' in cell:
                header_row = i
                break
        if header_row is not None:
            break

    if header_row is None:
        # Fallback: try row 13 (0-indexed)
        header_row = 13

    df = pd.read_excel(io.BytesIO(data), engine=engine, header=header_row, dtype=str)
    df.columns = [_clean_str(c) for c in df.columns]

    # Drop rows where 'Día de informe' is null/empty
    date_col = 'Día de informe'
    if date_col not in df.columns:
        # Try case-insensitive match
        for c in df.columns:
            if 'informe' in c.lower():
                df.rename(columns={c: date_col}, inplace=True)
                break

    df = df[df[date_col].notna() & (df[date_col].astype(str).str.strip() != '')].copy()
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    df = df[df[date_col].notna()].copy()

    df['Debe EUR'] = pd.to_numeric(df.get('Debe EUR', 0), errors='coerce').fillna(0)
    df['Haber EUR'] = pd.to_numeric(df.get('Haber EUR', 0), errors='coerce').fillna(0)
    df['SALDO'] = df['Debe EUR'] - df['Haber EUR']

    desc_col = 'Descripción' if 'Descripción' in df.columns else (
        'Descripcion' if 'Descripcion' in df.columns else None
    )
    if desc_col is None:
        for c in df.columns:
            if 'descri' in c.lower():
                desc_col = c
                break
    df['desc_raw'] = df[desc_col].apply(_clean_str) if desc_col else ''

    def extract_ref(desc):
        m = re.search(r'REF:([A-Z]\d+)', desc)
        if m:
            return m.group(1)
        m = re.search(r'\b([RL]\d{5,6})\b', desc)
        if m:
            return m.group(1)
        return ''

    def extract_desc_base(desc):
        idx = desc.find(' - AS:')
        return desc[:idx] if idx != -1 else desc

    df['ref_ext'] = df['desc_raw'].apply(extract_ref)
    df['desc_base'] = df['desc_raw'].apply(extract_desc_base)
    df['ref_norm'] = df['ref_ext'].apply(norm_ref)
    df['fecha_str'] = df[date_col].dt.strftime('%Y-%m-%d').fillna('')

    return df


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def run_matching(naos: pd.DataFrame, exact: pd.DataFrame):
    # Pasada A: fecha + abs(importe) + ref_norm
    exact['keyA'] = (
        exact['fecha_str'] + '|' +
        (exact['Debe EUR'] + exact['Haber EUR']).round(2).astype(str) + '|' +
        exact['ref_norm']
    )
    naos['keyA'] = (
        naos['fecha_str'] + '|' +
        naos['importe_eu'].abs().round(2).astype(str) + '|' +
        naos['ref_norm']
    )

    set_exact_A = set(exact.loc[exact['ref_norm'] != '', 'keyA'])
    set_naos_A = set(naos.loc[naos['ref_norm'] != '', 'keyA'])

    naos['MA'] = naos['keyA'].isin(set_exact_A) & (naos['ref_norm'] != '')
    exact['MA'] = exact['keyA'].isin(set_naos_A) & (exact['ref_norm'] != '')

    # Pasada C: fecha + abs(importe) + norm_desc
    exact['keyC'] = (
        exact['fecha_str'] + '|' +
        (exact['Debe EUR'] + exact['Haber EUR']).round(2).astype(str) + '|' +
        exact['desc_base'].apply(norm_desc)
    )
    naos['keyC'] = (
        naos['fecha_str'] + '|' +
        naos['importe_eu'].abs().round(2).astype(str) + '|' +
        naos.get('ampliacion', pd.Series(['']*len(naos))).apply(norm_desc)
    )

    set_exact_C = set(exact.loc[~exact['MA'], 'keyC'])
    set_naos_C = set(naos.loc[~naos['MA'], 'keyC'])

    naos['MC'] = (~naos['MA']) & naos['keyC'].isin(set_exact_C)
    exact['MC'] = (~exact['MA']) & exact['keyC'].isin(set_naos_C)

    # Pasada B: one-to-one fecha + Debe EUR (Exact sin REF)
    exact_B_mask = (exact['ref_ext'] == '') & (~exact['MA']) & (~exact['MC'])
    naos_B_mask = (
        (naos.get('signo_co', 'D') == 'D') &
        (naos['importe_eu'] > 0) &
        (~naos['MA']) &
        (~naos['MC'])
    )

    pool = defaultdict(list)
    for idx, row in exact.loc[exact_B_mask].iterrows():
        key = row['fecha_str'] + '|' + str(round(row['Debe EUR'], 2))
        pool[key].append(idx)

    naos['MB'] = False
    exact['MB'] = False

    for idx, row in naos.loc[naos_B_mask].iterrows():
        key = row['fecha_str'] + '|' + str(round(row['importe_eu'], 2))
        if pool[key]:
            exact_idx = pool[key].pop(0)
            naos.at[idx, 'MB'] = True
            exact.at[exact_idx, 'MB'] = True

    naos['MATCHED'] = naos['MA'] | naos['MC'] | naos['MB']
    exact['MATCHED'] = exact['MA'] | exact['MC'] | exact['MB']

    return naos, exact


# ---------------------------------------------------------------------------
# Excel generation
# ---------------------------------------------------------------------------

HEADER_FILL = _cell_fill('FF4472C4')
HEADER_FONT = Font(name='Arial', size=10, bold=True, color='FFFFFFFF')
BODY_FONT = Font(name='Arial', size=9)
NAOS_FILL = _cell_fill('FFFFFF00')
EXACT_FILL = _cell_fill('FFD9EAD3')
SUBTOTAL_FILL = _cell_fill('FFFFC7CE')
SUBTOTAL_FONT = Font(name='Arial', size=9, bold=True, color='FF9C0006')
NUM_FMT = '#,##0.00'
DATE_FMT = 'DD/MM/YYYY'


def _apply_body(cell, fill=None):
    cell.font = BODY_FONT
    cell.border = _thin_border()
    if fill:
        cell.fill = fill


def _apply_header(cell):
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.border = _thin_border()
    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)


def build_excel(naos: pd.DataFrame, exact: pd.DataFrame) -> BytesIO:
    wb = Workbook()

    # -----------------------------------------------------------------------
    # Pestaña 1: DIFERENCIAS
    # -----------------------------------------------------------------------
    ws1 = wb.active
    ws1.title = 'DIFERENCIAS'

    diff_headers = [
        'Fecha', 'Periodo', 'Orden', 'Cuenta', 'Concepto',
        'Ampliación / Descripción', 'Referencia', 'Importe EUR',
        'Signo', 'DEBE', 'HABER', 'SALDO', 'Diario', 'Asiento', 'Origen'
    ]

    for col_idx, h in enumerate(diff_headers, 1):
        cell = ws1.cell(row=1, column=col_idx, value=h)
        _apply_header(cell)

    # Leyenda en columna P
    legend_col = 16
    ws1.cell(row=1, column=legend_col, value='Leyenda:').font = Font(name='Arial', size=9, bold=True)
    ws1.cell(row=2, column=legend_col, value='🟡 Amarillo = apunte de NAOS que FALTA en Exact').font = BODY_FONT
    ws1.cell(row=3, column=legend_col, value='🟢 Verde = apunte de Exact que NO está en NAOS').font = BODY_FONT
    ws1.cell(row=4, column=legend_col, value='🔴 Rojo = subtotal con diferencia neta del día').font = BODY_FONT

    # Calculate per-date saldos
    naos_by_date = naos.groupby('fecha_str')['SALDO'].sum()
    exact_by_date = exact.groupby('fecha_str')['SALDO'].sum()
    all_dates = sorted(set(naos['fecha_str'].unique()) | set(exact['fecha_str'].unique()))

    # Filter to dates with differences only
    diff_dates = []
    date_summary = []
    for d in all_dates:
        if not d:  # skip rows with no valid date
            continue
        sn = float(round(naos_by_date.get(d, 0), 2))
        se = float(round(exact_by_date.get(d, 0), 2))
        diff = float(round(sn - se, 2))
        cuadra = bool(abs(diff) < 0.02)
        date_summary.append({'fecha': d, 'saldo_naos': sn, 'saldo_exact': se, 'diferencia': diff, 'cuadra': cuadra})
        if not cuadra:
            diff_dates.append(d)

    current_row = 2

    for fecha_str in diff_dates:
        naos_unmatched = naos[(naos['fecha_str'] == fecha_str) & (~naos['MATCHED'])]
        exact_unmatched = exact[(exact['fecha_str'] == fecha_str) & (~exact['MATCHED'])]

        # NAOS rows
        for _, row in naos_unmatched.iterrows():
            fecha_val = row.get('fecha_apunte', None)
            if pd.isna(fecha_val):
                fecha_val = None
            vals = [
                fecha_val,
                row.get('periodo', ''),
                row.get('orden', ''),
                row.get('cuenta_co', ''),
                row.get('concepto_co', ''),
                row.get('ampliacion', ''),
                row.get('referencia', ''),
                row.get('importe_eu', 0),
                row.get('signo_co', ''),
                row.get('DEBE', 0),
                row.get('HABER', 0),
                row.get('SALDO', 0),
                row.get('diario_co', ''),
                row.get('asiento', ''),
                'NAOS – falta en Exact',
            ]
            for c, v in enumerate(vals, 1):
                cell = ws1.cell(row=current_row, column=c, value=v)
                _apply_body(cell, NAOS_FILL)
                if c == 1 and v is not None:
                    cell.number_format = DATE_FMT
                elif c in (8, 10, 11, 12):
                    cell.number_format = NUM_FMT
            current_row += 1

        # EXACT rows
        for _, row in exact_unmatched.iterrows():
            fecha_val = row.get('Día de informe', None)
            if pd.isna(fecha_val):
                fecha_val = None
            debe = row.get('Debe EUR', 0)
            haber = row.get('Haber EUR', 0)
            saldo = debe - haber
            vals = [
                fecha_val, '', '', '', '',
                row.get('desc_base', ''),
                row.get('ref_ext', ''),
                debe + haber,
                '',
                debe,
                haber,
                saldo,
                '', '',
                'EXACT – no está en NAOS',
            ]
            for c, v in enumerate(vals, 1):
                cell = ws1.cell(row=current_row, column=c, value=v)
                _apply_body(cell, EXACT_FILL)
                if c == 1 and v is not None:
                    cell.number_format = DATE_FMT
                elif c in (8, 10, 11, 12):
                    cell.number_format = NUM_FMT
            current_row += 1

        # Subtotal row
        sn = round(naos_by_date.get(fecha_str, 0), 2)
        se = round(exact_by_date.get(fecha_str, 0), 2)
        diff = round(sn - se, 2)
        try:
            fecha_dt = pd.Timestamp(fecha_str)
            fecha_display = fecha_dt.strftime('%d/%m/%Y')
        except Exception:
            fecha_display = fecha_str

        debe_sum = round(naos_unmatched['DEBE'].sum(), 2)
        haber_sum = round(naos_unmatched['HABER'].sum(), 2)

        subtotal_fill = _cell_fill('FFFFC7CE')
        for c in range(1, 16):
            cell = ws1.cell(row=current_row, column=c, value='')
            cell.fill = subtotal_fill
            cell.font = SUBTOTAL_FONT
            cell.border = _thin_border()

        ws1.cell(row=current_row, column=1, value=fecha_display).font = SUBTOTAL_FONT
        ws1.cell(row=current_row, column=1).fill = subtotal_fill
        ws1.cell(row=current_row, column=1).border = _thin_border()
        ws1.cell(row=current_row, column=2, value=f'SUBTOTAL {fecha_display} — Diferencia de saldo: {diff:,.2f} €').font = SUBTOTAL_FONT
        ws1.cell(row=current_row, column=2).fill = subtotal_fill
        ws1.cell(row=current_row, column=2).border = _thin_border()
        ws1.cell(row=current_row, column=10, value=debe_sum).number_format = NUM_FMT
        ws1.cell(row=current_row, column=10).fill = subtotal_fill
        ws1.cell(row=current_row, column=10).font = SUBTOTAL_FONT
        ws1.cell(row=current_row, column=10).border = _thin_border()
        ws1.cell(row=current_row, column=11, value=haber_sum).number_format = NUM_FMT
        ws1.cell(row=current_row, column=11).fill = subtotal_fill
        ws1.cell(row=current_row, column=11).font = SUBTOTAL_FONT
        ws1.cell(row=current_row, column=11).border = _thin_border()
        ws1.cell(row=current_row, column=12, value=diff).number_format = NUM_FMT
        ws1.cell(row=current_row, column=12).fill = subtotal_fill
        ws1.cell(row=current_row, column=12).font = SUBTOTAL_FONT
        ws1.cell(row=current_row, column=12).border = _thin_border()
        ws1.cell(row=current_row, column=15, value=f'Dif. neta={diff:,.2f}').font = SUBTOTAL_FONT
        ws1.cell(row=current_row, column=15).fill = subtotal_fill
        ws1.cell(row=current_row, column=15).border = _thin_border()
        current_row += 1

        # Separator
        current_row += 1

    # Column widths
    col_widths = [12, 10, 10, 12, 20, 35, 14, 14, 8, 14, 14, 14, 10, 12, 28, 45]
    for i, w in enumerate(col_widths, 1):
        ws1.column_dimensions[get_column_letter(i)].width = w

    # -----------------------------------------------------------------------
    # Pestaña 2: RESUMEN_POR_FECHA
    # -----------------------------------------------------------------------
    ws2 = wb.create_sheet('RESUMEN_POR_FECHA')

    # Title
    ws2.merge_cells('A1:E1')
    title_cell = ws2['A1']
    title_cell.value = 'RECONCILIACIÓN POR FECHA – NAOS vs EXACT'
    title_cell.font = Font(name='Arial', size=12, bold=True, color='FFFFFFFF')
    title_cell.fill = _cell_fill('FF4472C4')
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    ws2.row_dimensions[1].height = 22

    # Header row 3
    sum_headers = ['Fecha', 'SALDO NAOS', 'SALDO EXACT', 'DIFERENCIA', '¿Cuadra?']
    for c, h in enumerate(sum_headers, 1):
        cell = ws2.cell(row=3, column=c, value=h)
        _apply_header(cell)

    ws2.freeze_panes = 'A4'

    green_fill = _cell_fill('FFE2EFDA')
    red_fill = _cell_fill('FFFFC7CE')

    total_naos = 0.0
    total_exact = 0.0
    total_diff = 0.0

    data_row = 4
    for item in date_summary:
        try:
            fecha_dt = pd.Timestamp(item['fecha'])
            fecha_val = fecha_dt.to_pydatetime()
        except Exception:
            fecha_val = item['fecha']

        row_fill = green_fill if item['cuadra'] else red_fill

        cell_f = ws2.cell(row=data_row, column=1, value=fecha_val)
        cell_f.number_format = DATE_FMT
        _apply_body(cell_f)

        for c, key in enumerate(['saldo_naos', 'saldo_exact', 'diferencia'], 2):
            cell = ws2.cell(row=data_row, column=c, value=item[key])
            cell.number_format = NUM_FMT
            _apply_body(cell, row_fill if c >= 4 else None)

        cell_ok = ws2.cell(row=data_row, column=5, value='✓' if item['cuadra'] else '✗')
        _apply_body(cell_ok, row_fill)
        cell_ok.alignment = Alignment(horizontal='center')

        total_naos += item['saldo_naos']
        total_exact += item['saldo_exact']
        total_diff += item['diferencia']
        data_row += 1

    # Total row
    blue_fill = _cell_fill('FF4472C4')
    total_font = Font(name='Arial', size=10, bold=True, color='FFFFFFFF')
    totals = ['TOTAL', round(total_naos, 2), round(total_exact, 2), round(total_diff, 2), '']
    for c, v in enumerate(totals, 1):
        cell = ws2.cell(row=data_row, column=c, value=v)
        cell.fill = blue_fill
        cell.font = total_font
        cell.border = _thin_border()
        if c in (2, 3, 4):
            cell.number_format = NUM_FMT

    col_widths2 = [14, 16, 16, 16, 12]
    for i, w in enumerate(col_widths2, 1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output, date_summary


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_reconciliation(naos_bytes: bytes, exact_bytes: bytes, naos_ext: str, exact_ext: str):
    naos = load_naos(naos_bytes, naos_ext)
    exact = load_exact(exact_bytes, exact_ext)
    naos, exact = run_matching(naos, exact)
    excel_io, date_summary = build_excel(naos, exact)
    return excel_io, date_summary
