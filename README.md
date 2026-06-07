# SG Mitigación de Accidentes de Tránsito

Sistema web para visualización y análisis de accidentalidad (caso de estudio: Medellín, datos Mede).

## Stack (fijado para el trabajo de grado)

| Capa | Tecnologías |
|------|-------------|
| Backend | Django, Django REST Framework, **GeoDjango** |
| Base de datos | **PostgreSQL + PostGIS** |
| ETL / análisis | Python (pandas, NumPy; GeoPandas cuando aplique) |
| Frontend | React, Vite, **Leaflet** (mapa), **Recharts** (gráficos) |
| Pruebas | pytest, pytest-django |
| Local | Docker Compose (opcional) o Postgres + backend en el PC |

No introducir otra pila (p. ej. otro framework backend o mapa) sin acuerdo con el director y registro en la documentación local.

## Variables de entorno

```bash
copy .env.example .env   # Windows
# Edite .env: DJANGO_SECRET_KEY y POSTGRES_PASSWORD (no se versiona en Git).
```

- **Sin Docker:** use en `.env` su `POSTGRES_HOST`, `POSTGRES_PORT` y base local (ej. pgAdmin en `5434`).
- **Con Docker:** `POSTGRES_DB=mitigacion_accidentes`, misma `POSTGRES_PASSWORD`; procedimiento en **`docs/MANUAL_INSTALACION_EJECUCION.md`** §8 (local). Compose fija `POSTGRES_HOST=db` solo en el contenedor backend.
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

**Acceso:** Inicio, Tablero, Mapa y **Asistente** (`/agente`) son públicos. **Predicciones** requiere iniciar sesión con rol **analista** (JWT). En el asistente, las consultas predictivas también requieren sesión de analista (el JWT se envía automáticamente si hay login).

**Docker (alternativa):** `docker compose up --build` desde la raíz; ver `docs/MANUAL_INSTALACION_EJECUCION.md` §8. No ejecutar otro `runserver` en el puerto 8000 a la vez.

**BD creada con SQL manual (pgAdmin):** ver `docs/MANUAL_INSTALACION_EJECUCION.md` §9 y `docs/MANUAL_CARGA_DATOS_BD.md`.

## Estructura

Resumen breve; **árbol completo** en `docs/MANUAL_INSTALACION_EJECUCION.md` §2.

| Carpeta / archivo | Rol |
|-------------------|-----|
| `backend/` | API REST, lógica de indicadores |
| `frontend/` | SPA (Inicio, Tablero, Mapa, Asistente, Predicciones) |
| `backend/agent/` | Asistente IA (Gemini + herramientas sobre APIs del dashboard) |
| `mede_pipeline_guiado.py`, `mede_limpieza.py`, `mede_eda_export.py` | ETL y EDA |
| `carga_mede_pgadmin.sql`, `requirements-etl.txt` | Carga idempotente a PostgreSQL |
| `scripts/cargar_poligonos_medellin.py` | Wrapper carga shapefile (ver manual carga §6) |

## Documentación (carpeta `docs/`, local)

Cinco documentos oficiales del proyecto (no versionados en Git público si `docs/` está en `.gitignore`). Copie la carpeta `docs/` completa al trasladar el proyecto a otro PC (ver `MANUAL_INSTALACION` §13).

| Documento | Contenido |
|-----------|-----------|
| `docs/DOCUMENTO_TECNICO_SISTEMA.md` | Arquitectura, datos, APIs, mapa, asistente IA, modelos predictivos |
| `docs/MANUAL_INSTALACION_EJECUCION.md` | Clonar, `.env`, PostGIS, Docker, migraciones, inventario portabilidad |
| `docs/MANUAL_CARGA_DATOS_BD.md` | ETL Mede, PostGIS 001–006, polígonos, carga SQL |
| `docs/GUIA_SUSTENTACION_COMPLETA.md` | Demo oral, FAQ jurado, fórmulas |
| `docs/CIERRE_PROYECTO.md` | Alcance final, checklist, limpieza del repo |

Además en `docs/`: `esquema_base_datos.sql` y `shp/` (shapefile límites comunales).




## Pruebas backend

Desde la carpeta `backend`, con el entorno virtual activado (mismo flujo que [Inicio rápido](#inicio-rápido-desarrollo-local-habitual)):

```powershell
cd backend
.\.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

Esperado: **99 passed, 3 skipped** (SQLite en memoria vía `config.settings_test`; ver `backend/pytest.ini`).

Los tests de predicciones usan JWT de rol **analista** (`backend/conftest.py`). PostGIS en PostgreSQL real se valida aparte con `python manage.py check_postgis` (no sustituye la suite pytest).


## Licencia / uso académico

Proyecto de grado — Universidad San buenaventura (USB). Uso académico
