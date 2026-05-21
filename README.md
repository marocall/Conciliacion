# RECON — Reconciliación Contable NAOS ↔ EXACT

Aplicación web fullstack para reconciliación contable entre los ERPs **NAOS** y **EXACT**.
El usuario carga dos archivos Excel, el backend los cruza aplicando reglas de negocio específicas y devuelve un Excel descargable con las diferencias y el resumen por fecha.

---

## Índice

1. [Stack tecnológico](#stack-tecnológico)
2. [Estructura del proyecto](#estructura-del-proyecto)
3. [Cómo ejecutar en local (sin Docker)](#cómo-ejecutar-en-local-sin-docker)
4. [Cómo ejecutar con Docker](#cómo-ejecutar-con-docker)
5. [API — Endpoints](#api--endpoints)
6. [Lógica de negocio — Reconciliación](#lógica-de-negocio--reconciliación)
7. [Formato del Excel resultado](#formato-del-excel-resultado)
8. [Frontend — Interfaz](#frontend--interfaz)
9. [Variables de entorno](#variables-de-entorno)
10. [Decisiones de diseño y advertencias](#decisiones-de-diseño-y-advertencias)
11. [Historial de cambios relevantes](#historial-de-cambios-relevantes)

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+ · FastAPI · uvicorn |
| Procesamiento Excel | pandas · openpyxl · xlrd |
| Frontend | HTML + Vanilla JS + Tailwind CSS (CDN) · sin Node.js |
| Containerización | Docker · docker-compose |
| Repositorio | https://github.com/marocall/Conciliacion.git |

> **Nota:** El frontend es un único `index.html` servido directamente por FastAPI.
> No requiere Node.js ni npm para ejecutarse. Tailwind CSS y las fuentes se cargan desde CDN.

---

## Estructura del proyecto

```
reconciliacion-app/
│
├── backend/
│   ├── main.py              # Servidor FastAPI: endpoints, CORS, token store
│   ├── reconciler.py        # Toda la lógica de cruce y generación del Excel
│   ├── requirements.txt     # Dependencias Python
│   ├── .env.example         # Plantilla de variables de entorno
│   └── static/
│       └── index.html       # Frontend completo (HTML + JS + Tailwind CDN)
│
├── frontend/                # Versión React/Vite (requiere Node.js)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── UploadZone.tsx
│   │   │   ├── ResultsPanel.tsx
│   │   │   └── SummaryTable.tsx
│   │   └── hooks/
│   │       └── useReconciliation.ts
│   ├── package.json
│   ├── vite.config.ts       # Proxy /api → http://localhost:8000
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── nginx.conf           # Proxy /api → backend en Docker
│
├── docker-compose.yml       # Orquesta backend + frontend (nginx)
├── .gitignore
└── README.md
```

### Qué hace cada archivo clave

| Archivo | Responsabilidad |
|---------|----------------|
| `backend/main.py` | Define los 3 endpoints REST, gestiona CORS, almacena tokens de descarga en memoria |
| `backend/reconciler.py` | Carga NAOS, carga EXACT, ejecuta las 3 pasadas de matching, calcula saldos por fecha, genera el Excel con openpyxl |
| `backend/static/index.html` | UI completa: drag & drop, llamada a la API, tabla de resultados, botón de descarga. Sin dependencias de build |
| `frontend/` | Versión alternativa React + TypeScript para entornos con Node.js disponible |
| `docker-compose.yml` | Backend en puerto 8000, frontend/nginx en puerto 80 con proxy a backend |

---

## Cómo ejecutar en local (sin Docker)

### Requisitos
- **Python 3.11+** instalado (verificar con `py --version` en Windows o `python3 --version` en Linux/Mac)
- Conexión a internet para cargar Tailwind CSS y Google Fonts desde CDN

### 1. Clonar el repositorio

```bash
git clone https://github.com/marocall/Conciliacion.git
cd Conciliacion
```

### 2. Instalar dependencias Python

```bash
cd backend
pip install -r requirements.txt
# En Windows si 'pip' no está en PATH:
py -3 -m pip install -r requirements.txt
```

### 3. Arrancar el servidor

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
# En Windows:
py -3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Abrir en el navegador

```
http://localhost:8000
```

El propio backend sirve el frontend en la ruta raíz `/`. No hay que arrancar nada más.

---

## Cómo ejecutar con Docker

### Requisitos
- Docker Desktop instalado y en ejecución

### Un solo comando

```bash
docker compose up --build
```

Abre **http://localhost** (puerto 80). El nginx del frontend hace de proxy hacia el backend en el puerto 8000.

### Parar

```bash
docker compose down
```

---

## API — Endpoints

### `GET /health`
Verificación de estado del servicio.

**Response:**
```json
{ "status": "ok" }
```

---

### `POST /api/reconcile`
Ejecuta la reconciliación entre los dos archivos Excel.

**Request:** `multipart/form-data`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `naos_file` | File (.xls / .xlsx) | Exportación del ERP NAOS |
| `exact_file` | File (.xls / .xlsx) | Exportación del ERP EXACT |

**Response JSON:**
```json
{
  "summary": [
    {
      "fecha": "2025-10-12",
      "saldo_naos": -19954.55,
      "saldo_exact": -19954.55,
      "diferencia": 0.0,
      "cuadra": true
    }
  ],
  "totalDates": 3,
  "matchedDates": 3,
  "diffDates": 0,
  "totalDiff": 0.0,
  "download_token": "uuid-v4-string"
}
```

> El Excel no se devuelve directamente en esta respuesta. Se almacena en memoria del servidor
> asociado a un `download_token` UUID. El frontend usa ese token para descargarlo.

---

### `GET /api/download/{token}`
Descarga el Excel generado por una reconciliación previa.

**Response:** Archivo `.xlsx` con `Content-Disposition: attachment`.

> Los tokens se guardan en un `dict` en memoria del proceso. Si el servidor se reinicia,
> los tokens se pierden. Para MVP esto es suficiente; en producción usar Redis o almacenamiento en disco.

---

## Lógica de negocio — Reconciliación

Todo el motor está en `backend/reconciler.py`. El flujo es:

```
load_naos() → load_exact() → run_matching() → build_excel()
```

### Carga NAOS (`load_naos`)

- Acepta `.xls` (engine `xlrd`) y `.xlsx` (engine `openpyxl`)
- **Limpieza de strings:** elimina sufijos `_x0000_` y caracteres nulos `\x00` que aparecen en algunos exports de NAOS
- Normaliza nombres de columna a minúsculas con aliases comunes (ej: `importe_eur` → `importe_eu`)
- Columnas clave utilizadas:

| Columna NAOS | Descripción |
|-------------|-------------|
| `fecha_apunte` | Fecha del apunte contable |
| `referencia` | Referencia del expediente (ej: `R076237`, `L064006`) |
| `signo_co` | `D` = Debe, `H` = Haber |
| `importe_eu` | Importe en euros (puede ser negativo con signo `H` o `D`) |
| `ampliacion` | Descripción ampliada del apunte |
| `cuenta_co`, `concepto_co`, `diario_co`, `asiento` | Datos contables para el Excel |

- Calcula:
  - `DEBE = importe_eu` si `signo_co == 'D'`, sino `0`
  - `HABER = importe_eu` si `signo_co == 'H'`, sino `0`
  - `SALDO = DEBE - HABER`

> **Importante:** Los importes negativos con signo `D` o `H` son válidos y se respetan.
> No se aplica `abs()` al calcular DEBE/HABER. Solo se usa `abs()` en las claves de matching.

---

### Carga EXACT (`load_exact`)

- Acepta `.xls` y `.xlsx`
- **Detección dinámica de cabecera:** busca la fila que contenga el texto `'Día de informe'` (puede estar en fila 13 o 14 según el export). Si no lo encuentra, usa fila 13 como fallback.
- Columnas clave:

| Columna EXACT | Descripción |
|--------------|-------------|
| `Día de informe` | Fecha de la operación |
| `Descripción` | Texto libre de la operación |
| `Debe EUR` | Importe en el Debe |
| `Haber EUR` | Importe en el Haber |

- Extrae `ref_ext` de la columna Descripción con dos patrones regex:
  1. Patrón explícito: `REF:([A-Z]\d+)`
  2. Patrón implícito: `\b([RL]\d{5,6})\b`
- Extrae `desc_base`: texto antes de ` - AS:` (elimina sufijo de asiento)

---

### Normalización de referencias (`norm_ref`)

```
L064006 → 064006
R076237 → 076237
F057571 → 057571
```

Si la referencia empieza por `L`, `R` o `F` seguido de dígitos, se elimina el primer carácter.
Esto permite cruzar referencias entre NAOS (que incluye el prefijo) y EXACT (que a veces no lo incluye).

---

### Normalización de descripción (`norm_desc`)

```
"OP A EQUIPOS RECUPERADOS" → "OPAEQUISRECUPERA" (25 chars, sin espacios/guiones/paréntesis)
```

Elimina `[-/\s\(\)]`, convierte a mayúsculas, toma los primeros 25 caracteres.

---

### Motor de matching — 3 pasadas

Se ejecutan en orden de fiabilidad decreciente. Una fila matcheada en pasada A no participa en B ni C.

#### Pasada A — Referencia + importe + fecha *(más fuerte)*

```python
keyA = fecha + '|' + abs(importe).round(2) + '|' + ref_norm
```

Solo actúa en filas con referencia no vacía. Es la pasada más confiable: exige los tres criterios a la vez.

#### Pasada C — Descripción + importe + fecha

```python
keyC = fecha + '|' + abs(importe).round(2) + '|' + norm_desc(descripcion)
```

Para filas sin referencia (frecuente en EXACT). Usa los primeros 25 chars de la descripción normalizada.

#### Pasada B — One-to-one por fecha + Debe EUR *(fallback)*

Solo para filas EXACT **sin referencia** y que no matchearon en A ni C.
Solo para filas NAOS con `signo_co == 'D'`, `importe > 0`, no matcheadas.

Usa un `defaultdict(list)` como pool: agrupa las filas EXACT sin ref por `(fecha, Debe EUR)`.
Para cada NAOS elegible, busca en el pool y hace `pop(0)` (FIFO) para garantizar matching 1-a-1 sin dobles.

```python
pool[fecha + '|' + str(round(Debe_EUR, 2))].append(idx_exact)
# → para cada NAOS: pool[key].pop(0) si hay disponible
```

> **No simplificar esta lógica.** El `pop(0)` es esencial para evitar que un importe repetido
> matchee dos veces contra el mismo registro EXACT.

---

### Cálculo de diferencias por fecha

```python
naos_by_date  = naos.groupby('fecha_apunte')['SALDO'].sum()
exact_by_date = exact.groupby('Día de informe')['SALDO'].sum()
DIFERENCIA = SALDO_NAOS - SALDO_EXACT   # round(2)
CUADRA = abs(DIFERENCIA) < 0.02         # tolerancia 2 céntimos
```

Las fechas sin valor en uno de los dos sistemas se tratan como `0` (outer join).
Las filas de NAOS **sin fecha** se excluyen del cálculo de saldos (no tienen contrapartida temporal en EXACT).

---

## Formato del Excel resultado

El Excel tiene **dos pestañas**:

### Pestaña 1: `DIFERENCIAS`

Solo contiene datos para **fechas donde `CUADRA == False`**.

**Columnas (A–O):**
`Fecha | Periodo | Orden | Cuenta | Concepto | Ampliación/Descripción | Referencia | Importe EUR | Signo | DEBE | HABER | SALDO | Diario | Asiento | Origen`

**Código de colores:**
| Color | Significado |
|-------|-------------|
| 🟡 Amarillo `FFFF00` | Apunte de NAOS que **falta** en EXACT |
| 🟢 Verde claro `FFD9EAD3` | Apunte de EXACT que **no está** en NAOS |
| 🔴 Rojo `FFFFC7CE` | Fila de subtotal con diferencia neta del día |

**Columna P (leyenda):** Filas 1–4 con descripción del código de colores.

**Fila subtotal (roja) por cada fecha con diferencia:**
- Col 1: fecha en formato `DD/MM/YYYY`
- Col 2: texto `SUBTOTAL DD/MM/YYYY — Diferencia de saldo: X,XXX.XX €`
- Col 10: suma DEBE de filas NAOS no matcheadas
- Col 11: suma HABER de filas NAOS no matcheadas
- Col 12: diferencia neta del día
- Col 15: `Dif. neta=X,XXX.XX`

### Pestaña 2: `RESUMEN_POR_FECHA`

Muestra **todas las fechas** (no solo las que difieren).

- Fila 1: título fusionado A1:E1 (fondo azul `FF4472C4`, texto blanco)
- Fila 3: cabecera `Fecha | SALDO NAOS | SALDO EXACT | DIFERENCIA | ¿Cuadra?`
- Freeze panes en `A4`
- Filas de datos: verde `FFE2EFDA` si cuadra, rojo `FFFFC7CE` si no
- Fila TOTAL al final (fondo azul)

**Estilos generales:**
- Fuente Arial 9pt (cuerpo), 10pt (resumen)
- Bordes finos en todas las celdas
- Números: formato `#,##0.00`
- Fechas: formato `DD/MM/YYYY`
- Headers: fondo `FF4472C4`, texto blanco, negrita

---

## Frontend — Interfaz

El frontend es `backend/static/index.html` — un único archivo HTML con:

- **Tailwind CSS** cargado desde CDN (`cdn.tailwindcss.com`)
- **Google Fonts:** Playfair Display (títulos), JetBrains Mono (números), DM Sans (cuerpo)
- **React** no usado en esta versión — es Vanilla JS puro

### Estética
Dark theme ejecutivo. Paleta:
```
bg-primary:   #0a0a0f
bg-card:      #12121a
accent-gold:  #f59e0b   (NAOS)
accent-blue:  #3b82f6   (EXACT)
success:      #10b981
error:        #ef4444
```

### Flujo de usuario
1. Drag & drop (o clic) para cargar archivo NAOS → zona dorada
2. Drag & drop (o clic) para cargar archivo EXACT → zona azul
3. Botón **⚡ Reconciliar** → `POST /api/reconcile`
4. Spinner con mensajes rotativos durante el procesamiento
5. Panel de resultados con 4 métricas animadas
6. Botón dorado **Descargar Informe Excel** → `GET /api/download/{token}`
7. Tabla resumen por fecha con colores verde/rojo

### Estados de la interfaz
| Estado | Descripción |
|--------|-------------|
| `idle` | Instrucciones iniciales, botón deshabilitado |
| `processing` | Spinner + barra de progreso + mensajes rotativos |
| `done` | Métricas animadas + botón de descarga + tabla |
| `error` | Mensaje de error con detalle del servidor |

---

## Variables de entorno

El backend lee `.env` en el directorio `backend/`. Copiar `.env.example` como `.env`:

```bash
cp backend/.env.example backend/.env
```

| Variable | Default | Descripción |
|----------|---------|-------------|
| `CORS_ORIGINS` | `*` | Orígenes permitidos para CORS (separados por coma) |

En producción con Docker, el CORS no es necesario porque nginx hace de proxy y las peticiones llegan al backend como `localhost`.

---

## Decisiones de diseño y advertencias

### Limpieza de strings en NAOS
Algunos exports del ERP NAOS contienen el sufijo `_x0000_` o caracteres nulos `\x00` en columnas de texto. La función `_clean_str()` los elimina antes de cualquier procesamiento.

### Detección de cabecera en EXACT
La fila de cabecera del fichero EXACT puede variar entre exportaciones (fila 13 o 14). El código busca dinámicamente la fila que contenga `'Día de informe'`. Si no la encuentra, usa fila 13 (índice 0-based) como fallback.

### Encoding en EXACT
Los archivos EXACT exportados desde Windows pueden tener columnas con encoding cp1252 que pandas lee como caracteres garbled (`D\xa2a de informe`). El código detecta la columna de fecha por contener la palabra `'informe'` en minúsculas, lo que funciona independientemente del encoding.

### Tipos numpy en JSON
pandas devuelve `np.float64` y `np.bool_` en operaciones de agrupación. Python's `json` no serializa estos tipos. El `date_summary` convierte explícitamente todos los valores a `float()` y `bool()` nativos antes de devolverlos en `JSONResponse`.

### Token store en memoria
Los Excel generados se guardan en un `dict` Python en memoria del proceso (`_download_store`). Si el servidor se reinicia entre el `POST /api/reconcile` y el `GET /api/download/{token}`, el token no existirá (HTTP 404). Para MVP es aceptable. En producción: persistir en Redis o disco.

### Filas NAOS sin fecha
NAOS puede contener asientos internos (impagados, anulaciones, cierres y aperturas) sin `fecha_apunte`. Estas filas se excluyen del cálculo de saldos por fecha y no aparecen en el Excel de diferencias, ya que no tienen contrapartida temporal en EXACT.

### Signos negativos en NAOS
Un importe con `signo_co == 'H'` puede ser negativo (ej: abono con importe `-13.848,72`). Esto es válido contablemente. El código respeta el signo original y solo aplica `abs()` para construir las claves de matching (no en DEBE/HABER).

---

## Historial de cambios relevantes

| Commit | Cambio |
|--------|--------|
| `b00330e` | Implementación inicial: backend FastAPI + frontend React/Vite + docker-compose |
| `14a1245` | Frontend convertido a HTML único servido por FastAPI (sin Node.js requerido) |
| `9c8983c` | Fix: tipos numpy no serializables en JSONResponse (causa del "error desconocido") |
| `84fe47c` | Fix: separador de miles en números 4 dígitos y formato 2 decimales en diferencia cero |
