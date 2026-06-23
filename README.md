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
| Reportes | Recharts + **html2canvas** (mapa) + CSS `@media print` |
| IA | **Google Gemini API** (HTTP/`urllib`, function calling) |
| Pruebas | pytest, pytest-django |

No introducir otra pila (p. ej. otro framework backend o mapa) sin acuerdo con el director.

### Librerías por sección (sustentación)

Documentación detallada en **`docs/LIBRERIAS_Y_SECCIONES.md`** (carpeta local, no en Git remoto):

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

| Rol | Tablero / Mapa / Asistente | Predicciones / Reportes | Gestión usuarios |
|-----|------------------------------|-------------------------|------------------|
| Sin login | Sí | No | No |
| Ciudadano | Sí | No | No |
| Analista | Sí | Sí | No |
| Administrador | Sí | Sí | Sí (`/admin/usuarios`) |
| Autoridad | Sí (perfil reservado) | No* | No |

\*Rol definido en BD para extensión futura; hoy mismo alcance que ciudadano en la UI.

**Usuario administrador de demostración** (migración `0005_seed_admin_user`):

- Usuario: `admin`
- Contraseña: `AdminUSB2026!`

## Estructura del repositorio

| Carpeta / archivo | Rol |
|-------------------|-----|
| `backend/accounts/` | JWT, roles, admin API usuarios |
| `backend/dashboard/` | Indicadores, predicciones, mapa (SQL/NumPy/statsmodels) |
| `backend/agent/` | Asistente Gemini + herramientas |
| `backend/reports/` | Payload de reportes |
| `frontend/src/pages/` | Pantallas por ruta |
| `frontend/src/map/` | Leaflet, captura, TopoJSON |
| `evaluaciones/` | `EVALUACION_MODULO_PREDICCIONES.md` + CSV de evaluación de modelos |
| `mede_pipeline_guiado.py`, `mede_limpieza.py`, … | ETL Mede (pandas) |

## Documentación local (`docs/`)

La carpeta **`docs/`** está en `.gitignore` (memoria de grado). Mantenga copia en su máquina/USB:

| Documento | Contenido |
|-----------|-----------|
| `docs/LIBRERIAS_Y_SECCIONES.md` | **Librerías y funciones por sección** |
| `docs/DOCUMENTO_TECNICO_SISTEMA.md` | Arquitectura y APIs |
| `docs/GUIA_SUSTENTACION_COMPLETA.md` | Demo, fórmulas y FAQ integral (sustentación) |
| `docs/GUIA_SUSTENTACION_LIBRERIAS.md` | Respuestas cortas para el jurado |
| `docs/CIERRE_PROYECTO.md` | Alcance final y checklist de cierre |
| `docs/VIADATA_DOCUMENTACION_INTEGRAL.md` | **Documento maestro** para exportar a la tesis |
| `docs/MANUAL_INSTALACION_EJECUCION.md` | Instalación |
| `docs/MANUAL_CARGA_DATOS_BD.md` | Carga PostGIS |
| `evaluaciones/EVALUACION_MODULO_PREDICCIONES.md` | Evaluación modelos Predicciones (§1–§5) |

## Pruebas backend

```powershell
cd backend
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
```

Esperado: suite en verde (SQLite en tests; PostGIS con `check_postgis` en BD real).

### Reporte Allure (visual)

Requiere `allure-pytest` (en `requirements.txt`), **Node.js** (`npx`) y **Java 8+** (Allure CLI).

```powershell
cd backend
.\run_pytest_allure.ps1 -Serve      # ejecuta tests y abre reporte en el navegador
.\run_pytest_allure.ps1 -Static      # genera backend/allure-report/index.html
```

Salida cruda: `backend/allure-results/` (ignorada en Git).

El reporte agrupa automáticamente por **Epic** (módulo), **Feature** (archivo de prueba), **Story** (caso), **Severidad** y etiquetas: `categoria`, `tipo_prueba`, `capa`, `indicador` (P05, P07, etc.). Configuración en `backend/allure_reporting.py`.

## Frontend — dependencias npm (referencia)

```json
"react", "react-dom", "react-router-dom", "recharts", "leaflet", "react-leaflet",
"leaflet.heat", "leaflet.markercluster", "@bopen/leaflet-area-selection",
"topojson-client", "html2canvas", "react-zoom-pan-pinch"
```

Versiones exactas en `frontend/package.json`.

## Licencia / uso académico

Proyecto de grado — Universidad San Buenaventura (USB). Uso académico.
