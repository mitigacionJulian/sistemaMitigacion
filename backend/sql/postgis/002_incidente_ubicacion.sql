-- F1.1–F1.3 — Columna geometry en incidente, backfill, índice GIST y trigger lat/lon → ubicacion
-- Ejecutar en pgAdmin sobre la base del proyecto (ej. reviNuwBD), después de 001_postgis_extension.sql

-- Columna (idempotente)
ALTER TABLE public.incidente
    ADD COLUMN IF NOT EXISTS ubicacion geometry(Point, 4326);

COMMENT ON COLUMN public.incidente.ubicacion IS
    'Punto WGS84 (EPSG:4326). Se rellena desde latitud/longitud con trigger o backfill.';

-- Mismos rangos que backend/dashboard/incidentes_mapa.py (Medellín aprox.)
UPDATE public.incidente i
SET ubicacion = ST_SetSRID(
        ST_MakePoint(
            CAST(i.longitud AS double precision),
            CAST(i.latitud AS double precision)
        ),
        4326
    )
WHERE i.latitud IS NOT NULL
  AND i.longitud IS NOT NULL
  AND CAST(i.latitud AS double precision) BETWEEN 1 AND 11
  AND CAST(i.longitud AS double precision) BETWEEN -79 AND -74
  AND (
        i.ubicacion IS NULL
        OR NOT ST_Equals(
            i.ubicacion,
            ST_SetSRID(
                ST_MakePoint(
                    CAST(i.longitud AS double precision),
                    CAST(i.latitud AS double precision)
                ),
                4326
            )
        )
      );

-- Índice espacial
CREATE INDEX IF NOT EXISTS idx_incidente_ubicacion
    ON public.incidente USING GIST (ubicacion);

-- Trigger: nuevas filas / actualización de lat/lon mantienen ubicacion
CREATE OR REPLACE FUNCTION public.incidente_sync_ubicacion_from_latlon()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.latitud IS NOT NULL
       AND NEW.longitud IS NOT NULL
       AND CAST(NEW.latitud AS double precision) BETWEEN 1 AND 11
       AND CAST(NEW.longitud AS double precision) BETWEEN -79 AND -74
    THEN
        NEW.ubicacion := ST_SetSRID(
            ST_MakePoint(
                CAST(NEW.longitud AS double precision),
                CAST(NEW.latitud AS double precision)
            ),
            4326
        );
    ELSE
        NEW.ubicacion := NULL;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_incidente_sync_ubicacion ON public.incidente;

CREATE TRIGGER trg_incidente_sync_ubicacion
    BEFORE INSERT OR UPDATE OF latitud, longitud
    ON public.incidente
    FOR EACH ROW
    EXECUTE FUNCTION public.incidente_sync_ubicacion_from_latlon();

-- Resumen (para validar en pgAdmin)
SELECT
    count(*) AS total_incidentes,
    count(*) FILTER (
        WHERE latitud IS NOT NULL AND longitud IS NOT NULL
    ) AS con_latlon,
    count(*) FILTER (
        WHERE ubicacion IS NOT NULL
    ) AS con_ubicacion,
    count(*) FILTER (
        WHERE latitud IS NOT NULL
          AND longitud IS NOT NULL
          AND CAST(latitud AS double precision) BETWEEN 1 AND 11
          AND CAST(longitud AS double precision) BETWEEN -79 AND -74
          AND ubicacion IS NULL
    ) AS validos_sin_ubicacion
FROM public.incidente;
