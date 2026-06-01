-- F1.5 — Columnas geometry en comuna y barrio + indices GIST
-- Ejecutar despues de 003_punto_critico_ubicacion.sql

ALTER TABLE public.comuna
    ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 4326);

ALTER TABLE public.barrio
    ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 4326);

COMMENT ON COLUMN public.comuna.geom IS
    'Limite territorial WGS84 (EPSG:4326). Fuente: shapefile Datos Abiertos Medellin.';

COMMENT ON COLUMN public.barrio.geom IS
    'Limite de barrio WGS84. Corregimientos rurales pueden quedar sin geometria (veredas en shapefile).';

CREATE INDEX IF NOT EXISTS idx_comuna_geom
    ON public.comuna USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_barrio_geom
    ON public.barrio USING GIST (geom);

SELECT
    (SELECT count(*) FROM comuna) AS comunas,
    (SELECT count(*) FROM comuna WHERE geom IS NOT NULL) AS comunas_con_geom,
    (SELECT count(*) FROM barrio) AS barrios,
    (SELECT count(*) FROM barrio WHERE geom IS NOT NULL) AS barrios_con_geom;
