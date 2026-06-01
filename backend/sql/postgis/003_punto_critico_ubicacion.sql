-- F1.4 — Geometría en punto_critico + índice GIST
-- Ejecutar después de 002_incidente_ubicacion.sql

ALTER TABLE public.punto_critico
    ADD COLUMN IF NOT EXISTS ubicacion geometry(Point, 4326);

COMMENT ON COLUMN public.punto_critico.ubicacion IS
    'Punto WGS84 del punto crítico; radio_metros se usa en ST_DWithin.';

UPDATE public.punto_critico p
SET ubicacion = ST_SetSRID(
        ST_MakePoint(
            CAST(p.longitud AS double precision),
            CAST(p.latitud AS double precision)
        ),
        4326
    )
WHERE p.latitud IS NOT NULL
  AND p.longitud IS NOT NULL
  AND p.ubicacion IS NULL;

CREATE INDEX IF NOT EXISTS idx_punto_critico_ubicacion
    ON public.punto_critico USING GIST (ubicacion);

CREATE OR REPLACE FUNCTION public.punto_critico_sync_ubicacion_from_latlon()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.latitud IS NOT NULL AND NEW.longitud IS NOT NULL THEN
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

DROP TRIGGER IF EXISTS trg_punto_critico_sync_ubicacion ON public.punto_critico;

CREATE TRIGGER trg_punto_critico_sync_ubicacion
    BEFORE INSERT OR UPDATE OF latitud, longitud
    ON public.punto_critico
    FOR EACH ROW
    EXECUTE FUNCTION public.punto_critico_sync_ubicacion_from_latlon();

SELECT
    count(*) AS total_puntos,
    count(*) FILTER (WHERE ubicacion IS NOT NULL) AS con_ubicacion
FROM public.punto_critico;
