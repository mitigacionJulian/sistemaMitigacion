# SG Mitigación de Accidentes de Tránsito

Sistema web para visualización y análisis de accidentalidad (caso de estudio: Medellín, datos Mede).

## Stack

- **Backend:** Django, Django REST Framework, PostgreSQL
- **Frontend:** React, Vite, Leaflet, Recharts
- **ETL:** scripts Python en la raíz del repositorio (`mede_*`)
- **Despliegue local:** Docker Compose (PostGIS + API)

## Variables de entorno

```bash
copy .env.example .env   # Windows
# Edite .env: DJANGO_SECRET_KEY y POSTGRES_PASSWORD (no se versiona en Git).
```

- **Sin Docker:** use en `.env` su `POSTGRES_HOST`, `POSTGRES_PORT` y base local.
- **Con Docker:** en `.env` ponga `POSTGRES_DB=mitigacion_accidentes` y la misma `POSTGRES_PASSWORD` que usará el contenedor `db`; `docker-compose.yml` fija `POSTGRES_HOST=db` solo para el servicio backend.

## Inicio rápido

```bash
# Base de datos + API
docker compose up --build

# Interfaz (otra terminal)
cd frontend
npm install
npm run dev
```

API: `http://127.0.0.1:8000` · Frontend: `http://127.0.0.1:5173` (según Vite).

## Estructura

| Carpeta / archivo | Rol |
|-------------------|-----|
| `backend/` | API REST, lógica de indicadores |
| `frontend/` | SPA (Inicio, Tablero, Predicciones) |
| `mede_pipeline_guiado.py`, `mede_limpieza.py` | Limpieza y carga de datos |
| `carga_mede_pgadmin.sql` | Carga idempotente a PostgreSQL |

La documentación detallada de desarrollo se mantiene **fuera del repositorio remoto** (carpeta `docs/` ignorada por git).

## Pruebas backend

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Licencia / uso académico

Proyecto de grado — Universidad Simón Bolívar (USB). Uso académico; no incluye datos abiertos Mede en el repositorio.
