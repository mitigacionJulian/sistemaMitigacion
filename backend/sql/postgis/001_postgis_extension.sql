-- F0.1 — Activar PostGIS en la base de datos del proyecto
-- Ejecutar en pgAdmin o psql conectado a POSTGRES_DB (ej. reviNuwBD o mitigacion_accidentes)

CREATE EXTENSION IF NOT EXISTS postgis;

-- Verificación (debe devolver una versión, no error)
SELECT postgis_full_version();
