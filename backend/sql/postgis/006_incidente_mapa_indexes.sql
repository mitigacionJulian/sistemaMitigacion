-- F7 — Índices para consultas del mapa (fecha + territorio, solo filas con ubicación)
-- Ejecutar después de 002_incidente_ubicacion.sql

CREATE INDEX IF NOT EXISTS idx_incidente_mapa_fecha
    ON public.incidente (fecha_incidente DESC, id DESC)
    WHERE ubicacion IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_incidente_mapa_comuna_fecha
    ON public.incidente (comuna_id, fecha_incidente DESC)
    WHERE ubicacion IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_incidente_mapa_barrio_fecha
    ON public.incidente (barrio_id, fecha_incidente DESC)
    WHERE ubicacion IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_incidente_mapa_comuna_esp_fecha
    ON public.incidente (comuna_id_espacial, fecha_incidente DESC)
    WHERE ubicacion IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_incidente_mapa_barrio_esp_fecha
    ON public.incidente (barrio_id_espacial, fecha_incidente DESC)
    WHERE ubicacion IS NOT NULL;

-- Estadísticas para el planificador tras crear índices
ANALYZE public.incidente;
ANALYZE public.comuna;
ANALYZE public.barrio;
