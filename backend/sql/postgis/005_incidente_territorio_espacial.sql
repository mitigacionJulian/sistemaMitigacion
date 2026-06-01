-- F2.3-F2.4 — Territorio espacial derivado de poligonos + vistas QA
-- Requiere: 004_comuna_barrio_geom.sql y barrios/comunas con geom cargados
-- Ejecutar: python manage.py run_postgis_sql --only 005_incidente_territorio_espacial.sql
-- Backfill: python manage.py actualizar_territorio_espacial

ALTER TABLE public.incidente
    ADD COLUMN IF NOT EXISTS comuna_id_espacial integer REFERENCES public.comuna(id),
    ADD COLUMN IF NOT EXISTS barrio_id_espacial integer REFERENCES public.barrio(id);

COMMENT ON COLUMN public.incidente.comuna_id_espacial IS
    'Comuna segun ST_Contains(comuna.geom, ubicacion). Puede diferir de comuna_id (texto Mede).';

COMMENT ON COLUMN public.incidente.barrio_id_espacial IS
    'Barrio segun ST_Contains(barrio.geom, ubicacion). Puede diferir de barrio_id (texto Mede).';

CREATE INDEX IF NOT EXISTS idx_incidente_comuna_id_espacial
    ON public.incidente (comuna_id_espacial);

CREATE INDEX IF NOT EXISTS idx_incidente_barrio_id_espacial
    ON public.incidente (barrio_id_espacial);

-- Resuelve comuna/barrio espacial para un punto (barrio = poligono mas pequeno que contiene)
CREATE OR REPLACE FUNCTION public.incidente_resolver_territorio_espacial(p_ubicacion geometry)
RETURNS TABLE(comuna_id integer, barrio_id integer)
LANGUAGE sql
STABLE
AS $$
    SELECT
        (
            SELECT c.id
            FROM public.comuna c
            WHERE c.geom IS NOT NULL
              AND p_ubicacion IS NOT NULL
              AND ST_Contains(c.geom, p_ubicacion)
            ORDER BY ST_Area(c.geom::geography) ASC
            LIMIT 1
        ) AS comuna_id,
        (
            SELECT b.id
            FROM public.barrio b
            WHERE b.geom IS NOT NULL
              AND p_ubicacion IS NOT NULL
              AND ST_Contains(b.geom, p_ubicacion)
            ORDER BY ST_Area(b.geom::geography) ASC
            LIMIT 1
        ) AS barrio_id;
$$;

CREATE OR REPLACE FUNCTION public.incidente_sync_territorio_espacial()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    r record;
BEGIN
    IF NEW.ubicacion IS NULL THEN
        NEW.comuna_id_espacial := NULL;
        NEW.barrio_id_espacial := NULL;
        RETURN NEW;
    END IF;

    SELECT * INTO r FROM public.incidente_resolver_territorio_espacial(NEW.ubicacion);
    NEW.comuna_id_espacial := r.comuna_id;
    NEW.barrio_id_espacial := r.barrio_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_incidente_sync_territorio_espacial ON public.incidente;

CREATE TRIGGER trg_incidente_sync_territorio_espacial
    BEFORE INSERT OR UPDATE OF ubicacion
    ON public.incidente
    FOR EACH ROW
    EXECUTE FUNCTION public.incidente_sync_territorio_espacial();

-- Vista enriquecida (F2.3)
CREATE OR REPLACE VIEW public.v_incidente_territorio_espacial AS
SELECT
    i.id,
    i.radicado,
    i.fecha_incidente,
    i.ubicacion,
    i.comuna_id,
    i.barrio_id,
    i.comuna_id_espacial,
    i.barrio_id_espacial,
    co_reg.codigo AS comuna_codigo_registro,
    co_reg.nombre AS comuna_nombre_registro,
    co_esp.codigo AS comuna_codigo_espacial,
    co_esp.nombre AS comuna_nombre_espacial,
    b_reg.codigo AS barrio_codigo_registro,
    b_reg.nombre AS barrio_nombre_registro,
    b_esp.codigo AS barrio_codigo_espacial,
    b_esp.nombre AS barrio_nombre_espacial
FROM public.incidente i
LEFT JOIN public.comuna co_reg ON co_reg.id = i.comuna_id
LEFT JOIN public.comuna co_esp ON co_esp.id = i.comuna_id_espacial
LEFT JOIN public.barrio b_reg ON b_reg.id = i.barrio_id
LEFT JOIN public.barrio b_esp ON b_esp.id = i.barrio_id_espacial;

-- Discrepancias registro vs poligono (F2.4)
CREATE OR REPLACE VIEW public.v_incidente_territorio_discrepancia AS
SELECT
    v.*,
    (v.comuna_id IS DISTINCT FROM v.comuna_id_espacial) AS discrepancia_comuna,
    (v.barrio_id IS DISTINCT FROM v.barrio_id_espacial) AS discrepancia_barrio
FROM public.v_incidente_territorio_espacial v
WHERE v.ubicacion IS NOT NULL
  AND (
        v.comuna_id IS DISTINCT FROM v.comuna_id_espacial
        OR v.barrio_id IS DISTINCT FROM v.barrio_id_espacial
      );

-- Resumen rapido (post-ejecucion; backfill completo via manage.py)
SELECT
    count(*) AS total_incidentes,
    count(*) FILTER (WHERE ubicacion IS NOT NULL) AS con_ubicacion,
    count(*) FILTER (WHERE comuna_id_espacial IS NOT NULL) AS con_comuna_espacial,
    count(*) FILTER (WHERE barrio_id_espacial IS NOT NULL) AS con_barrio_espacial
FROM public.incidente;
