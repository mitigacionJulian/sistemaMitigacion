# ViaData — Medellín

Sistema web para visualización y análisis de accidentalidad vial (caso de estudio: Medellín, datos Mede).

## Stack (fijado para el trabajo de grado)

| Capa | Tecnologías |
|------|-------------|
| Backend | Django 5, **Django REST Framework**, **SimpleJWT**, **GeoDjango** |
| Base de datos | **PostgreSQL + PostGIS** |
| Cálculo en API | **NumPy** (OLS, Poisson, métricas), **statsmodels** (ARIMA/SARIMA) |
| ETL / análisis offline | **pandas**, openpyxl, matplotlib (`requirements-etl.txt`) |
| Frontend | **React 19**, **Vite**, **React Router** |
| Mapa | **Leaflet**, react-leaflet, markercluster, heat, area-selection, **topojson-client** |
| Gráficos | **Recharts**; zoom: **react-zoom-pan-pinch** |
| Reportes | Recharts + **html2canvas** (mapa) + CSS `@media print` (tablero, mapa, predicciones, **pruebas**) |
| IA | **Google Gemini API** (HTTP/`urllib`, function calling) |
| Pruebas | pytest, pytest-django |

No introducir otra pila (p. ej. otro framework backend o mapa) sin acuerdo con el director.

### Librerías por sección (sustentación)

Documentación detallada en **`docs/`** (versionada en Git; índice en **`docs/README.md`**):

- Qué librería usa cada pantalla (Tablero, Mapa, Predicciones, Reportes, Admin, Asistente).
- Qué modelos usan NumPy vs statsmodels vs SQL puro.
- FAQ oral: **`docs/GUIA_SUSTENTACION_LIBRERIAS.md`**.

Índice de `docs/`: **`docs/README.md`**.

## Variables de entorno

```bash
copy .env.example .env   # Windows
# Edite .env: DJANGO_SECRET_KEY y POSTGRES_PASSWORD (no se versiona en Git).
```

- **Sin Docker:** use en `.env` su `POSTGRES_HOST`, `POSTGRES_PORT` y base local (ej. pgAdmin en `5434`).
- **Con Docker:** `POSTGRES_DB=mitigacion_accidentes`, misma `POSTGRES_PASSWORD`; procedimiento en **`docs/MANUAL_INSTALACION_EJECUCION.md`** §8 (local) si tiene copia en `docs/`.
- **JWT / auth:** `JWT_ACCESS_MINUTES` (15), `JWT_REFRESH_DAYS`, `FRONTEND_URL`, `PASSWORD_RESET_TOKEN_HOURS` (ver `.env.example`).
- **Asistente IA:** `GEMINI_API_KEY` (obligatoria para `/agente`), `AGENT_MODEL_FLASH`, `AGENT_CACHE_TTL`, `AGENT_DAILY_LIMIT_PER_IP` (ver `.env.example`).
- **Panel admin — pruebas:** `DJANGO_DEBUG=1` habilita ejecución de pytest desde `/admin/pruebas`; `ALLOW_ADMIN_TEST_RUNNER=1` fuerza o desactiva ese botón de forma explícita (ver `.env.example`).

## Inicio rápido (desarrollo local habitual)

```powershell
# 1. Variables (raíz del repo)
copy .env.example .env
# Editar .env (POSTGRES_*, DJANGO_SECRET_KEY, GDAL si usa PostGIS en Windows)

# 2. Backend
cd backend
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py check_postgis   # si DJANGO_USE_POSTGIS=1
python manage.py migrate
.\run_dev.ps1                    # o: python manage.py runserver 127.0.0.1:8000

# 3. Frontend (otra terminal)
cd frontend
npm install
npm run dev
```

API: `http://127.0.0.1:8000` · Frontend: `http://127.0.0.1:5173` (proxy `/api` → backend).

## Acceso y roles

| Rol | Tablero / Mapa / Asistente | Predicciones / Reportes | Administración |
|-----|------------------------------|-------------------------|----------------|
| Sin login | Sí | No | No |
| Ciudadano | Sí | No | No |
| Analista | Sí | Sí | No |
| Administrador | Sí | Sí | Usuarios (`/admin/usuarios`) y pruebas (`/admin/pruebas`) |
| Autoridad | Sí (perfil reservado) | No* | No |

\*Rol definido en BD para extensión futura; hoy mismo alcance que ciudadano en la UI.

**Usuario administrador de demostración** (migración `0005_seed_admin_user`):

- Usuario: `admin`
- Contraseña: `AdminUSB2026!`

## Estructura del repositorio

| Carpeta / archivo | Rol |
|-------------------|-----|
| `backend/accounts/` | JWT, roles, admin API usuarios y **panel de pruebas** |
| `backend/dashboard/` | Indicadores, predicciones, mapa (SQL/NumPy/statsmodels) |
| `backend/agent/` | Asistente Gemini + herramientas |
| `backend/reports/` | Payload de reportes |
| `frontend/src/pages/` | Pantallas por ruta |
| `frontend/src/map/` | Leaflet, captura, TopoJSON |
| `evaluaciones/` | Evaluación modelos Predicciones; **`LEEME_PRUEBAS_SISTEMA.txt`** (panel admin pruebas) |
| `mede_pipeline_guiado.py`, `mede_limpieza.py`, … | ETL Mede (pandas) |

## Documentación (`docs/`)

La carpeta **`docs/`** está **versionada en Git** (Markdown y SQL). Índice: **`docs/README.md`**.

| Documento | Contenido |
|-----------|-----------|
| `docs/LIBRERIAS_Y_SECCIONES.md` | **Librerías y funciones por sección** |
| `docs/DOCUMENTO_TECNICO_SISTEMA.md` | Arquitectura y APIs |
| `docs/GUIA_SUSTENTACION_COMPLETA.md` | Demo, fórmulas y FAQ integral (sustentación) |
| `docs/GUIA_SUSTENTACION_LIBRERIAS.md` | Respuestas cortas para el jurado |
| `docs/DOCUMENTACION_PRUEBAS_SOFTWARE.md` | Casos de prueba pytest documentados |
| `docs/CIERRE_PROYECTO.md` | Alcance final y checklist de cierre |
| `docs/VIADATA_DOCUMENTACION_INTEGRAL.md` | **Documento maestro** para exportar a la tesis |
| `docs/MANUAL_INSTALACION_EJECUCION.md` | Instalación |
| `docs/MANUAL_CARGA_DATOS_BD.md` | Carga PostGIS |
| `evaluaciones/LEEME_PRUEBAS_SISTEMA.txt` | Panel admin — pruebas y reporte PDF |
| `evaluaciones/EVALUACION_MODULO_PREDICCIONES.md` | Evaluación modelos Predicciones (§1–§5) |

## Pruebas backend

### Ejecución en consola

```powershell
cd backend
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
```

Esperado: suite en verde (SQLite en tests; PostGIS con `check_postgis` en BD real).

Con salida estructurada para el panel admin (JSON Allure):

```powershell
python -m pytest --alluredir=allure-results --clean-alluredir -q
```

Los archivos quedan en `backend/allure-results/` (ignorados en Git). **No requiere Node.js ni Java.**

### Panel administrador — `/admin/pruebas`

Solo rol **administrador**. Flujo con **dos botones**:

| Botón | Acción |
|-------|--------|
| **Ejecutar suite** | Lanza `pytest` con `--alluredir`, guarda JSON en `allure-results/` y muestra resultados en la UI |
| **Generar reporte** | Igual que tablero/mapa/predicciones: vista previa → **Imprimir / Guardar PDF** |

**Qué muestra la UI tras ejecutar:** KPIs (total, pasaron, fallaron…), resumen por módulo, fallos y detalle de cada caso (con filtro por estado).

**Variables de entorno** (archivo `.env` en la raíz del repo; reinicie el backend tras cambiarlas):

| Variable | Efecto |
|----------|--------|
| `DJANGO_DEBUG=1` | Modo desarrollo; por defecto habilita «Ejecutar suite» |
| `ALLOW_ADMIN_TEST_RUNNER=1` | Fuerza habilitar el botón (útil si quiere control explícito) |
| `ALLOW_ADMIN_TEST_RUNNER=0` | Deshabilita ejecutar desde la UI aunque `DEBUG=1` |

**Campos del reporte imprimible:**

| Campo | Significado |
|-------|-------------|
| **Estado** | `done` = pytest terminó con código 0; `error` = fallos, timeout o error del runner |
| **Código salida pytest** | `0` = todas las pruebas pasaron; `1` = hubo fallos; `-1` = timeout o no se pudo ejecutar |

**API (administrador, JWT):**

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/admin/pruebas/` | Estado de la última ejecución + resumen parseado |
| POST | `/api/admin/pruebas/ejecutar/` | Inicia la suite en segundo plano |
| POST | `/api/admin/pruebas/reporte/` | Payload para `/reporte/vista` (imprimible) |

Código: `backend/accounts/pruebas_runner.py`, `pruebas_reporte.py`, `admin_pruebas_views.py` · UI: `frontend/src/pages/AdminPruebas.jsx`.

Guía extendida: **`evaluaciones/LEEME_PRUEBAS_SISTEMA.txt`**.

### Allure — etiquetado y reporte opcional en consola

La suite usa **`allure-pytest`** para etiquetar cada caso (Epic, Feature, categoría, indicador P05/P07, etc.). Configuración en `backend/allure_reporting.py` y `backend/conftest.py`.

El **panel admin no necesita** el reporte HTML oficial de Allure: los JSON alimentan la UI y el reporte imprimible.

**Opcional** (solo consola, requiere Node.js + Java 8+ y `allure-pytest` en `requirements.txt`):

```powershell
cd backend
.\run_pytest_allure.ps1 -Serve      # ejecuta tests y abre Allure en el navegador
.\run_pytest_allure.ps1 -Static      # genera backend/allure-report/index.html
```

No es necesario para el uso habitual del sistema vía `/admin/pruebas`.

## Frontend — dependencias npm (referencia)

```json
"react", "react-dom", "react-router-dom", "recharts", "leaflet", "react-leaflet",
"leaflet.heat", "leaflet.markercluster", "@bopen/leaflet-area-selection",
"topojson-client", "html2canvas", "react-zoom-pan-pinch"
```

Versiones exactas en `frontend/package.json`.

## Licencia / uso académico

Proyecto de grado — Universidad San Buenaventura (USB). Uso académico.
