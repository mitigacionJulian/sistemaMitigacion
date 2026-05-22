-- =====================================================
-- CARGA MEDE A POSTGRES (pgAdmin) - IDPOTENTE
-- Base destino: reviNuwBD | schema: public
-- Requiere: esquema_base_datos.sql ya ejecutado
-- =====================================================
-- PASO 0 (fuera de SQL): convertir XLSX -> CSV UTF-8 (preserva tildes/ñ)
--   python -c "import pandas as pd; df=pd.read_excel('salida/Mede_Victimas_inci_depurado.xlsx', engine='openpyxl'); cols={c:('Anio' if c in ('Año','A\u00f1o','A�o','Ano') else c) for c in df.columns}; df=df.rename(columns=cols); df.to_csv('salida/Mede_Victimas_inci_depurado.csv', index=False, encoding='utf-8-sig')"
--
-- PASO 1: ejecutar este archivo completo una vez (crea staging y objetos ETL)
-- PASO 2: en pgAdmin importar CSV a public.mede_stg (Import/Export Data):
--   - File: .../salida/Mede_Victimas_inci_depurado.csv
--   - Format: csv | Header: Yes | Encoding: UTF8 | Delimiter: ,
-- PASO 3: volver a ejecutar este archivo completo (es idempotente)
-- =====================================================

BEGIN;

SET search_path TO public;

-- -----------------------------
-- A) Objetos de apoyo ETL
-- -----------------------------
CREATE OR REPLACE FUNCTION public.fn_norm_code(p text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
WITH base AS (
  SELECT upper(
    regexp_replace(
      translate(coalesce(trim(p), ''), 'áéíóúÁÉÍÓÚñÑüÜ', 'aeiouAEIOUnNuU'),
      '[^A-Za-z0-9]+',
      '_',
      'g'
    )
  ) AS s
)
SELECT CASE
  WHEN length(s) <= 20 THEN s
  -- 12 + '_' + 7 = 20 (estable y evita overflow en VARCHAR(20))
  ELSE left(s, 12) || '_' || left(md5(s), 7)
END
FROM base;
$$;

CREATE TABLE IF NOT EXISTS public.mede_stg (
  gravedad_victima text,
  fecha_incidente text,
  hora_incidente text,
  clase_incidente text,
  direccion_incidente text,
  sexo text,
  edad text,
  condicion text,
  mes text,
  dia text,
  num_dia text,
  hora text,
  grupo_edad text,
  anio text,
  radicado text,
  latitud text,
  longitud text,
  comuna text,
  barrio text
);

-- Tabla de control para idempotencia de víctimas
CREATE TABLE IF NOT EXISTS public.etl_mede_victima_cargada (
  source_key text PRIMARY KEY,
  victima_id integer,
  created_at timestamp default now()
);

COMMIT;

-- Si necesitas limpiar staging antes de importar de nuevo, ejecuta:
-- TRUNCATE TABLE public.mede_stg;

BEGIN;
SET search_path TO public;

-- -----------------------------
-- B) Catálogos desde staging
-- -----------------------------
WITH src AS (
  SELECT DISTINCT trim(clase_incidente) AS nombre
  FROM public.mede_stg
  WHERE clase_incidente IS NOT NULL AND trim(clase_incidente) <> ''
), dedup AS (
  SELECT DISTINCT ON (fn_norm_code(nombre))
    fn_norm_code(nombre) AS codigo,
    nombre
  FROM src
  ORDER BY fn_norm_code(nombre), length(nombre) DESC, nombre
)
INSERT INTO public.clase_incidente (codigo, nombre)
SELECT codigo, nombre
FROM dedup
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre;

WITH src AS (
  SELECT DISTINCT trim(gravedad_victima) AS nombre
  FROM public.mede_stg
  WHERE gravedad_victima IS NOT NULL AND trim(gravedad_victima) <> ''
), dedup AS (
  SELECT DISTINCT ON (fn_norm_code(nombre))
    fn_norm_code(nombre) AS codigo,
    nombre
  FROM src
  ORDER BY fn_norm_code(nombre), length(nombre) DESC, nombre
)
INSERT INTO public.gravedad_victima (codigo, nombre, orden)
SELECT codigo, nombre,
       row_number() OVER (ORDER BY nombre)
FROM dedup
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre;

WITH src AS (
  SELECT DISTINCT trim(condicion) AS nombre
  FROM public.mede_stg
  WHERE condicion IS NOT NULL AND trim(condicion) <> ''
), dedup AS (
  SELECT DISTINCT ON (fn_norm_code(nombre))
    fn_norm_code(nombre) AS codigo,
    nombre
  FROM src
  ORDER BY fn_norm_code(nombre), length(nombre) DESC, nombre
)
INSERT INTO public.condicion (codigo, nombre)
SELECT codigo, nombre
FROM dedup
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre;

WITH src AS (
  SELECT DISTINCT trim(sexo) AS nombre
  FROM public.mede_stg
  WHERE sexo IS NOT NULL AND trim(sexo) <> ''
), m AS (
  SELECT
    nombre,
    CASE
      WHEN upper(nombre) IN ('M','F','O') THEN upper(nombre)
      WHEN lower(nombre) LIKE 'm%' THEN 'M'
      WHEN lower(nombre) LIKE 'f%' THEN 'F'
      ELSE 'O'
    END AS codigo
  FROM src
)
INSERT INTO public.sexo (codigo, nombre)
SELECT codigo,
       CASE codigo WHEN 'M' THEN 'Masculino' WHEN 'F' THEN 'Femenino' ELSE 'Otro' END
FROM m
ON CONFLICT (codigo) DO NOTHING;

WITH src AS (
  SELECT DISTINCT trim(comuna) AS comuna_raw
  FROM public.mede_stg
  WHERE comuna IS NOT NULL AND trim(comuna) <> ''
), parsed AS (
  SELECT
    comuna_raw,
    CASE
      WHEN comuna_raw LIKE '% - %' THEN trim(split_part(comuna_raw, ' - ', 1))
      ELSE fn_norm_code(comuna_raw)
    END AS codigo,
    CASE
      WHEN comuna_raw LIKE '% - %' THEN trim(split_part(comuna_raw, ' - ', 2))
      ELSE comuna_raw
    END AS nombre
  FROM src
), dedup AS (
  SELECT DISTINCT ON (codigo)
    codigo,
    nombre
  FROM parsed
  ORDER BY codigo, length(nombre) DESC, nombre
)
INSERT INTO public.comuna (codigo, nombre)
SELECT codigo, nombre
FROM dedup
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre;

WITH src AS (
  SELECT DISTINCT trim(barrio) AS barrio_raw, trim(comuna) AS comuna_raw
  FROM public.mede_stg
  WHERE barrio IS NOT NULL AND trim(barrio) <> ''
), parsed AS (
  SELECT
    fn_norm_code(barrio_raw) AS codigo,
    barrio_raw AS nombre,
    CASE
      WHEN comuna_raw LIKE '% - %' THEN trim(split_part(comuna_raw, ' - ', 1))
      ELSE fn_norm_code(comuna_raw)
    END AS comuna_codigo
  FROM src
), dedup AS (
  SELECT DISTINCT ON (codigo)
    codigo,
    nombre,
    comuna_codigo
  FROM parsed
  ORDER BY codigo, length(nombre) DESC, nombre
)
INSERT INTO public.barrio (codigo, nombre, comuna_id)
SELECT p.codigo, p.nombre, c.id
FROM dedup p
LEFT JOIN public.comuna c ON c.codigo = p.comuna_codigo
ON CONFLICT (codigo) DO UPDATE
SET nombre = EXCLUDED.nombre,
    comuna_id = COALESCE(public.barrio.comuna_id, EXCLUDED.comuna_id);

-- Grupo de edad desde staging (por si aparecen nombres no sembrados)
WITH src AS (
  SELECT DISTINCT trim(grupo_edad) AS ge
  FROM public.mede_stg
  WHERE grupo_edad IS NOT NULL AND trim(grupo_edad) <> ''
), parsed AS (
  SELECT
    ge,
    CASE
      WHEN ge ~ '^\d+\s*-\s*\d+$' THEN split_part(regexp_replace(ge, '\s+', '', 'g'), '-', 1)::int
      WHEN lower(translate(ge, 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) LIKE '80%mas%' THEN 80
      ELSE NULL
    END AS min_e,
    CASE
      WHEN ge ~ '^\d+\s*-\s*\d+$' THEN split_part(regexp_replace(ge, '\s+', '', 'g'), '-', 2)::int
      WHEN lower(translate(ge, 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) LIKE '80%mas%' THEN NULL
      ELSE NULL
    END AS max_e
  FROM src
)
INSERT INTO public.grupo_edad (codigo, nombre, edad_minima, edad_maxima, orden)
SELECT
  CASE WHEN p.max_e IS NULL THEN p.min_e::text || '+' ELSE p.min_e::text || '-' || p.max_e::text END AS codigo,
  CASE WHEN p.max_e IS NULL THEN p.min_e::text || ' o más años' ELSE p.min_e::text || ' - ' || p.max_e::text || ' años' END AS nombre,
  p.min_e,
  p.max_e,
  row_number() OVER (ORDER BY p.min_e NULLS LAST)
FROM parsed p
WHERE p.min_e IS NOT NULL
ON CONFLICT (codigo) DO NOTHING;

-- -----------------------------
-- C) Incidentes (idempotente por radicado UNIQUE)
-- -----------------------------
WITH prep AS (
  SELECT
    trim(radicado) AS radicado,
    trim(clase_incidente) AS clase_incidente,
    trim(direccion_incidente) AS direccion_incidente,
    trim(comuna) AS comuna_raw,
    trim(barrio) AS barrio_raw,
    CASE
      WHEN trim(fecha_incidente) ~ '^\d{4}-\d{2}-\d{2}$' THEN trim(fecha_incidente)::date
      WHEN trim(fecha_incidente) ~ '^\d{2}/\d{2}/\d{4}$' THEN to_date(trim(fecha_incidente), 'DD/MM/YYYY')
      ELSE NULL
    END AS fecha_d,
    CASE
      WHEN trim(hora_incidente) ~ '^\d{2}:\d{2}(:\d{2})?$' THEN
        (CASE WHEN length(trim(hora_incidente)) = 5 THEN trim(hora_incidente) || ':00' ELSE trim(hora_incidente) END)::time
      ELSE NULL
    END AS hora_t,
    NULLIF(replace(trim(latitud), ',', '.'), '')::numeric(10,8) AS latitud_n,
    NULLIF(replace(trim(longitud), ',', '.'), '')::numeric(11,8) AS longitud_n
  FROM public.mede_stg
  WHERE radicado IS NOT NULL AND trim(radicado) <> ''
), x AS (
  SELECT DISTINCT ON (radicado)
    p.*,
    ci.id AS clase_id,
    co.id AS comuna_id,
    b.id AS barrio_id
  FROM prep p
  LEFT JOIN public.clase_incidente ci ON lower(ci.nombre) = lower(p.clase_incidente)
  LEFT JOIN public.comuna co ON co.codigo = CASE WHEN p.comuna_raw LIKE '% - %' THEN trim(split_part(p.comuna_raw, ' - ', 1)) ELSE fn_norm_code(p.comuna_raw) END
  LEFT JOIN public.barrio b ON b.codigo = fn_norm_code(p.barrio_raw)
  ORDER BY radicado, fecha_d NULLS LAST, hora_t NULLS LAST
)
INSERT INTO public.incidente (
  radicado,
  fecha_incidente,
  hora_incidente,
  fecha_hora_incidente,
  clase_incidente_id,
  direccion_incidente,
  latitud,
  longitud,
  comuna_id,
  barrio_id
)
SELECT
  x.radicado,
  x.fecha_d,
  x.hora_t,
  (x.fecha_d::timestamp + x.hora_t) AS fecha_hora_incidente,
  x.clase_id,
  x.direccion_incidente,
  x.latitud_n,
  x.longitud_n,
  x.comuna_id,
  x.barrio_id
FROM x
WHERE x.fecha_d IS NOT NULL AND x.hora_t IS NOT NULL
ON CONFLICT (radicado) DO NOTHING;

-- -----------------------------
-- D) Víctimas (idempotente por source_key)
-- -----------------------------
WITH prep AS (
  SELECT
    s.ctid,
    trim(s.radicado) AS radicado,
    trim(s.sexo) AS sexo_raw,
    NULLIF(trim(s.edad), '')::int AS edad_i,
    trim(s.grupo_edad) AS grupo_edad_raw,
    trim(s.condicion) AS condicion_raw,
    trim(s.gravedad_victima) AS gravedad_raw
  FROM public.mede_stg s
  WHERE s.radicado IS NOT NULL AND trim(s.radicado) <> ''
), ranked AS (
  SELECT
    p.*,
    row_number() OVER (
      PARTITION BY p.radicado, coalesce(p.sexo_raw,''), coalesce(p.edad_i::text,''), coalesce(p.grupo_edad_raw,''), coalesce(p.condicion_raw,''), coalesce(p.gravedad_raw,'')
      ORDER BY p.ctid
    ) AS dup_orden
  FROM prep p
), m AS (
  SELECT
    r.*,
    md5(concat_ws('|', r.radicado, r.sexo_raw, coalesce(r.edad_i::text,''), r.grupo_edad_raw, r.condicion_raw, r.gravedad_raw, r.dup_orden::text)) AS source_key,
    i.id AS incidente_id,
    sx.id AS sexo_id,
    ge.id AS grupo_edad_id,
    c.id AS condicion_id,
    gv.id AS gravedad_id
  FROM ranked r
  JOIN public.incidente i ON i.radicado = r.radicado
  LEFT JOIN public.sexo sx ON sx.codigo = CASE
    WHEN upper(r.sexo_raw) IN ('M','F','O') THEN upper(r.sexo_raw)
    WHEN lower(r.sexo_raw) LIKE 'm%' THEN 'M'
    WHEN lower(r.sexo_raw) LIKE 'f%' THEN 'F'
    ELSE 'O'
  END
  LEFT JOIN public.condicion c ON lower(c.nombre) = lower(r.condicion_raw)
  LEFT JOIN public.gravedad_victima gv ON lower(gv.nombre) = lower(r.gravedad_raw)
  LEFT JOIN public.grupo_edad ge ON (
       (r.grupo_edad_raw ~ '^\d+\s*-\s*\d+$'
        AND ge.edad_minima = split_part(regexp_replace(r.grupo_edad_raw, '\s+', '', 'g'), '-', 1)::int
        AND ge.edad_maxima = split_part(regexp_replace(r.grupo_edad_raw, '\s+', '', 'g'), '-', 2)::int)
       OR
       (lower(translate(r.grupo_edad_raw, 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) LIKE '80%mas%'
        AND ge.edad_minima = 80 AND ge.edad_maxima IS NULL)
  )
)
, ins AS (
  INSERT INTO public.victima (
    incidente_id, sexo_id, edad, grupo_edad_id, condicion_id, gravedad_victima_id
  )
  SELECT
    m.incidente_id, m.sexo_id, m.edad_i, m.grupo_edad_id, m.condicion_id, m.gravedad_id
  FROM m
  WHERE NOT EXISTS (
    SELECT 1
    FROM public.etl_mede_victima_cargada z
    WHERE z.source_key = m.source_key
  )
  RETURNING id
)
INSERT INTO public.etl_mede_victima_cargada (source_key, victima_id)
SELECT m.source_key, v.id
FROM m
JOIN LATERAL (
  SELECT id
  FROM public.victima vv
  WHERE vv.incidente_id = m.incidente_id
    AND vv.edad IS NOT DISTINCT FROM m.edad_i
    AND vv.sexo_id IS NOT DISTINCT FROM m.sexo_id
    AND vv.grupo_edad_id IS NOT DISTINCT FROM m.grupo_edad_id
    AND vv.condicion_id IS NOT DISTINCT FROM m.condicion_id
    AND vv.gravedad_victima_id IS NOT DISTINCT FROM m.gravedad_id
  ORDER BY vv.id DESC
  LIMIT 1
) v ON true
WHERE NOT EXISTS (
  SELECT 1 FROM public.etl_mede_victima_cargada z WHERE z.source_key = m.source_key
)
ON CONFLICT (source_key) DO NOTHING;

COMMIT;

-- -----------------------------
-- E) Validaciones rápidas
-- -----------------------------
SELECT 'incidente' AS tabla, count(*) AS filas FROM public.incidente
UNION ALL
SELECT 'victima', count(*) FROM public.victima
UNION ALL
SELECT 'staging', count(*) FROM public.mede_stg;

-- Verificación de mojibake (debería tender a 0)
SELECT count(*) AS posibles_mojibake_condicion
FROM public.condicion
WHERE nombre LIKE '%Ã%' OR nombre LIKE '%Â%';

SELECT count(*) AS posibles_mojibake_comuna
FROM public.comuna
WHERE nombre LIKE '%Ã%' OR nombre LIKE '%Â%';
