# Manual de carga de datos y cambio de base de datos

**Audiencia:** operador que recibe un **Excel Mede** nuevo, instala el sistema en un servidor limpio o **migra** a otra instancia PostgreSQL.  
**Supuesto inicial:** base PostgreSQL **vacía** (o dominio truncado para recarga).  
**Última actualización:** 2026-06-22  

**Documentación relacionada:** índice en `docs/README.md`; evaluación de modelos en `evaluaciones/EVALUACION_MODULO_PREDICCIONES.md`.

**Scripts en la raíz del repositorio:**

| Archivo | Rol |
|---------|-----|
| `mede_limpieza.py` | Reglas únicas de depuración (`depurar_mede`, `load_mede_xlsx`) |
| `mede_eda_export.py` | EDA, figuras, export XLSX depurado |
| `mede_pipeline_guiado.py` | Orquestación por pasos con checkpoints |
| `carga_mede_pgadmin.sql` | Staging → modelo normalizado en PostgreSQL |
| `requirements-etl.txt` | Dependencias Python del ETL |
| `docs/esquema_base_datos.sql` | DDL completo (local; puede no estar en Git público) |

---

## Tabla de contenidos

1. [Visión del flujo](#1-visión-del-flujo)  
2. [Preparar PostgreSQL](#2-preparar-postgresql)  
3. [PostGIS (orden obligatorio)](#3-postgis-orden-obligatorio)  
4. [Depurar el Excel (ETL)](#4-depurar-el-excel-etl)  
5. [Cargar CSV a PostgreSQL](#5-cargar-csv-a-postgresql)  
6. [Polígonos y territorio espacial](#6-polígonos-y-territorio-espacial)  
7. [Cambiar de base de datos](#7-cambiar-de-base-de-datos)  
8. [Archivos a modificar según el caso](#8-archivos-a-modificar-según-el-caso)  
9. [Verificación post-carga](#9-verificación-post-carga)  
10. [Decisiones de calidad de datos (referencia)](#10-decisiones-de-calidad-de-datos-referencia)

---

## 1. Visión del flujo

```text
Mede_Victimas_inci.xlsx  (datos abiertos Medellín)
        │
        ▼
  mede_limpieza.depurar_mede()
        │
        ├── mede_eda_export.py  ──►  salida/*.xlsx, figuras EDA
        └── mede_pipeline_guiado.py  ──►  checkpoints Parquet, CSV
        │
        ▼
  salida/Mede_Victimas_inci_depurado.csv  (UTF-8, columna Anio)
        │
        ▼
  carga_mede_pgadmin.sql  (1ª vez: DDL + staging)
        │
        ▼
  pgAdmin: COPY / Import → public.mede_stg
        │
        ▼
  carga_mede_pgadmin.sql  (2ª vez: merge idempotente)
        │
        ▼
  backend/sql/postgis/001 … 006
        │
        ▼
  cargar_poligonos_medellin + actualizar_territorio_espacial
        │
        ▼
  Aplicación web (Django consulta incidente / victima)
```

**Principio de diseño:** toda regla de limpieza vive en **`mede_limpieza.py`**. No duplique lógica en otros scripts; impórtela. Así EDA, pipeline y memoria de grado describen el mismo comportamiento.

**Volumen de referencia del proyecto:** del orden de **160 000+** incidentes con coordenadas válidas tras depuración (depende del Excel y flags).

**Periodo típico en BD:** aproximadamente **2014-01-01 — 2021-09-30**.

---

## 2. Preparar PostgreSQL

### 2.1 Crear la base

En pgAdmin o `psql` (como superusuario):

```sql
CREATE DATABASE mitigacion_accidentes
  ENCODING 'UTF8'
  LC_COLLATE 'Spanish_Colombia.1252'
  LC_CTYPE 'Spanish_Colombia.1252'
  TEMPLATE template0;
```

Ajuste locale según su SO. Conéctese **a esa base** antes de ejecutar scripts.

### 2.2 Esquema relacional + tablas Django

#### Camino A — SQL manual (recomendado para replicar el diseño del grado)

1. Ejecutar **`docs/esquema_base_datos.sql`** completo en la base (Query Tool en pgAdmin).
2. Sincronizar historial Django sin recrear tablas ya existentes:

```powershell
cd backend
.\.venv\Scripts\activate
python manage.py sync_migration_history
python manage.py migrate
```

3. Verificar:

```powershell
python manage.py showmigrations accounts
```

Todas las migraciones de `accounts` deben estar marcadas `[X]`.

#### Camino B — Solo migraciones Django

```powershell
python manage.py migrate
```

Crea tablas de autenticación (`auth_user`, `rol`, `perfil_usuario`, etc.). **No** crea el dominio `incidente`/`victima` si no hay migraciones de dominio en Django; para Mede use **Camino A** o ejecute `esquema_base_datos.sql` después.

### 2.3 Configurar la aplicación

En la raíz del repo, `.env` debe apuntar a esta base (`POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_PASSWORD`).

---

## 3. PostGIS (orden obligatorio)

Ejecutar **en orden** (pgAdmin o comando `run_postgis_sql`). Rutas relativas a `backend/sql/postgis/`.

| Orden | Archivo | Qué hace |
|-------|---------|----------|
| 1 | `001_postgis_extension.sql` | `CREATE EXTENSION IF NOT EXISTS postgis` |
| 2 | `002_incidente_ubicacion.sql` | Columna `ubicacion` (Point, SRID 4326), trigger lat/lon → geometría |
| 3 | `003_punto_critico_ubicacion.sql` | Geometría en `punto_critico` (tabla puede quedar vacía) |
| 4 | `004_comuna_barrio_geom.sql` | Columnas `geom` en `comuna` y `barrio` |
| 5 | `005_incidente_territorio_espacial.sql` | `comuna_id_espacial`, `barrio_id_espacial`, triggers |
| 6 | `006_incidente_mapa_indexes.sql` | Índices GIST y de consulta para mapa y hotspots |

Desde `backend/`:

```powershell
python manage.py run_postgis_sql --only 001_postgis_extension.sql
```

Repita cambiando el nombre de archivo, o ejecute los seis en pgAdmin.

Verificación:

```powershell
python manage.py check_postgis
python manage.py postgis_f1_status
```

`postgis_f1_status` confirma extensión, columnas geometry y triggers básicos.

---

## 4. Depurar el Excel (ETL)

### 4.1 Dependencias

Desde la **raíz** del repositorio:

```powershell
pip install -r requirements-etl.txt
```

Incluye entre otros: `pandas`, `openpyxl`, `matplotlib`, `seaborn`.

### 4.2 Archivo fuente

Copiar el Excel oficial a la raíz, por ejemplo:

`Mede_Victimas_inci.xlsx`

Fuente: portal de datos abiertos de Medellín (MedeDatos / accidentalidad con víctimas).

### 4.3 Opción rápida — `mede_eda_export.py`

```powershell
python mede_eda_export.py --input Mede_Victimas_inci.xlsx --output salida/Mede_Victimas_inci_depurado.xlsx
```

Comportamiento por defecto:

- Aplica `mede_limpieza.depurar_mede`
- Elimina filas con valores nulos en columnas críticas (salvo flags `--keep-rows-with-nulls`)
- Tope de edad ≤ 67 años (desactivar con `--sin-tope-edad-67` si documenta el motivo)
- Genera figuras en `salida/mede_eda_figuras/` para revisión en memoria
- Exporta XLSX depurado

**Convertir a CSV** (pgAdmin espera CSV; columna `Anio` sin tilde):

```powershell
python -c "import pandas as pd; df=pd.read_excel('salida/Mede_Victimas_inci_depurado.xlsx', engine='openpyxl'); cols={c:('Anio' if c in ('Año','Ano') else c) for c in df.columns}; df=df.rename(columns=cols); df.to_csv('salida/Mede_Victimas_inci_depurado.csv', index=False, encoding='utf-8-sig')"
```

### 4.4 Opción guiada — `mede_pipeline_guiado.py`

```powershell
python mede_pipeline_guiado.py --list-steps

python mede_pipeline_guiado.py --input Mede_Victimas_inci.xlsx --pause --checkpoint-dir salida/pipeline_run
```

Pasos típicos: `load` → `depurar` → `filter` → `export_csv` → `sql_help`.

El CSV final debe ser **`salida/Mede_Victimas_inci_depurado.csv`**:

- Codificación UTF-8 con BOM (`utf-8-sig`) aceptable para Excel/pgAdmin  
- Separador coma  
- Primera fila: encabezados  
- Columna de año: **`Anio`** (sin tilde)

### 4.5 CLI directa de limpieza

```powershell
python mede_limpieza.py analyze --input Mede_Victimas_inci.xlsx
python mede_limpieza.py clean --input Mede_Victimas_inci.xlsx --output salida/depurado.csv
```

### 4.6 Qué hace `mede_limpieza.py` (resumen)

| Área | Acción |
|------|--------|
| Texto | Corrección mojibake, normalización de tildes, trim, comuna/barrio |
| Fechas | Serial Excel → fecha ISO; validación de rango |
| Coordenadas | Coma decimal → punto; filtro fuera de bbox Medellín |
| Radicado | Clave de incidente; deduplicación en carga SQL |
| Edad | Tope 67 alineado a política del proyecto |
| Catálogos | Códigos normalizados antes del merge SQL |

Cualquier **nueva regla** de negocio debe implementarse aquí y documentarse en la memoria de grado.

---

## 5. Cargar CSV a PostgreSQL

### 5.1 Primera ejecución de `carga_mede_pgadmin.sql`

En pgAdmin, conectado a su base, ejecutar **todo** el archivo **`carga_mede_pgadmin.sql`**.

Crea entre otros:

- Tabla staging **`mede_stg`**
- Funciones `fn_norm_code`, utilidades de normalización
- Tablas de control ETL (`etl_mede_victima_cargada`, etc.)
- Procedimientos que insertan/actualizan catálogos, **`incidente`** y **`victima`**

### 5.2 Importar CSV a staging

Tabla **`public.mede_stg`** → clic derecho → **Import/Export Data…**

| Opción | Valor |
|--------|--------|
| Filename | `salida/Mede_Victimas_inci_depurado.csv` |
| Format | csv |
| Header | Yes |
| Encoding | UTF8 |
| Delimiter | `,` |
| Quote | `"` |

Si falla por filas problemáticas, revise el log de pgAdmin; suele ser comillas sin escapar o filas con separadores extra (corregir en ETL, no “a mano” en producción).

### 5.3 Segunda ejecución del SQL (merge idempotente)

Volver a ejecutar **todo** `carga_mede_pgadmin.sql`.

- Inserta catálogos nuevos  
- Hace upsert de incidentes por radicado  
- Inserta víctimas no registradas en `etl_mede_victima_cargada`  

### 5.4 Comprobaciones SQL

```sql
SELECT COUNT(*) AS incidentes FROM incidente;
SELECT COUNT(*) AS victimas FROM victima;
SELECT MIN(fecha_incidente), MAX(fecha_incidente) FROM incidente;
SELECT COUNT(*) FROM incidente WHERE ubicacion IS NOT NULL;
```

Valores esperados del proyecto de referencia: cientos de miles de incidentes y víctimas; fechas dentro del rango del Excel depurado.

---

## 6. Polígonos y territorio espacial

Necesario para coropleta, modo **territorio=espacial** y indicador **G03** (calidad registro vs polígono).

### 6.1 Shapefile

Copiar el material oficial a:

`docs/shp/shp_barrios_y_veredas_mr/`

(No suele estar en el repositorio público por tamaño; usar copia del equipo USB.)

### 6.2 Preparar geometrías en tablas (script 004)

```powershell
cd backend
python manage.py run_postgis_sql --only 004_comuna_barrio_geom.sql
```

### 6.3 Cargar polígonos desde shapefile

Vista previa (sin escribir):

```powershell
python manage.py cargar_poligonos_medellin --dry-run
```

Carga real:

```powershell
python manage.py cargar_poligonos_medellin
```

Desde la raíz del repo también: `python scripts/cargar_poligonos_medellin.py` (wrapper al mismo comando).

**Matching implementado:**

- **Barrios urbanos** (`subtipo_ba=1`, comunas 01–16): por `nombre + comuna` o código oficial.
- **Comunas / corregimientos:** unión de polígonos del shapefile por `limitecomu` (veredas en 50, 60, 70, 80, 90).
- SRID origen EPSG:9377 (MAGNA-SIRGAS) → EPSG:4326 en Python (requiere OSGeo4W / `PROJ_LIB` en Windows).

### 6.4 Actualizar FK espaciales por punto

```powershell
python manage.py actualizar_territorio_espacial
```

Verifique con las consultas SQL de [§9.3](#93-consultas-de-sanidad) (conteos con `comuna_id_espacial` / `barrio_id_espacial` y muestra G03).

---

## 7. Cambiar de base de datos

### 7.1 Nueva instancia, misma estructura

1. Crear base vacía en el servidor destino.  
2. **Opción 1:** ejecutar `esquema_base_datos.sql` + PostGIS + ETL completo.  
3. **Opción 2:** `pg_dump -Fc` de la base origen y `pg_restore` en destino.  
4. Actualizar `.env` (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_PASSWORD`).  
5. `python manage.py sync_migration_history` + `migrate` si el dump no incluyó `django_migrations` al día.  
6. `python manage.py check_postgis`.

### 7.2 Recarga Mede en el mismo servidor

1. **Respaldo:** `pg_dump -Fc mitigacion_accidentes > backup.dump`  
2. Truncar dominio (destruye datos de accidentes):

```sql
TRUNCATE victima, incidente RESTART IDENTITY CASCADE;
-- Opcional: TRUNCATE mede_stg;
```

3. Repetir secciones [4](#4-depurar-el-excel-etl) y [5](#5-cargar-csv-a-postgresql).  
4. Si cambió coordenadas: `actualizar_territorio_espacial` de nuevo.

La carga es **idempotente** por radicado y claves ETL de víctima.

### 7.3 Docker ↔ PostgreSQL local

| Entorno | Host en `.env` | Puerto típico | Datos |
|---------|----------------|---------------|--------|
| Postgres local (pgAdmin) | `localhost` | `5432` o `5434` | Su BD manual |
| Docker `db` | `localhost` (desde host) | `5432` mapeado | Volumen `pgdata` |

**No asuma** que Docker y su `reviNuwBD` en `5434` son la misma base. Cargue Mede en cada entorno donde vaya a demostrar.

### 7.4 Backend en Docker, carga desde el host

Con `docker compose up db -d`:

- Conectar pgAdmin a `localhost:5432` (usuario/contraseña del `.env`).  
- Ejecutar esquema, PostGIS y carga contra esa instancia.  
- El contenedor `backend` usa `POSTGRES_HOST=db` internamente; desde el host sigue siendo `localhost:5432`.

---

## 8. Archivos a modificar según el caso

| Situación | Archivo |
|-----------|---------|
| Nueva regla de limpieza | `mede_limpieza.py` |
| Flags EDA (NA, edad, figuras) | `mede_eda_export.py` o argumentos del pipeline |
| Orden de pasos / checkpoints | `mede_pipeline_guiado.py` |
| Columna nueva en Excel | `mede_limpieza.py` + columna en `mede_stg` + `carga_mede_pgadmin.sql` |
| Nueva tabla catálogo | `docs/esquema_base_datos.sql` + SQL de carga |
| Índices de rendimiento mapa | `006_incidente_mapa_indexes.sql` |
| Conexión de la app | `.env` en la raíz |
| Migración Django (auth/perfil) | `backend/accounts/migrations/` + `migrate` |

---

## 9. Verificación post-carga

### 9.1 Comandos Django

```powershell
cd backend
python manage.py check_postgis
python manage.py shell -c "from django.db import connection; c=connection.cursor(); c.execute('SELECT COUNT(*) FROM incidente'); print('incidentes:', c.fetchone()[0])"
```

### 9.2 Aplicación web

| Prueba | Resultado esperado |
|--------|-------------------|
| `GET /api/dashboard/kpis/?desde=2016-01-01&hasta=2020-12-31` | Totales > 0 |
| `/mapa` | Puntos visibles con filtros amplios; hotspots P14; modo área opcional |
| `/tablero` | Gráficos con series |
| `/agente` | Respuesta con `GEMINI_API_KEY` configurada |
| Modo espacial + coropleta | Requiere polígonos cargados (§6) |
| `/predicciones` (analista) | Proyección mensual con R² en meta |

### 9.3 Consultas de sanidad

```sql
-- Incidentes sin geometría (debería ser bajo tras 002)
SELECT COUNT(*) FROM incidente WHERE ubicacion IS NULL AND latitud IS NOT NULL;

-- Discrepancia registro vs espacial (muestra G03)
SELECT COUNT(*) FILTER (WHERE comuna_id IS DISTINCT FROM comuna_id_espacial) * 100.0 / NULLIF(COUNT(*),0)
FROM incidente;
```

---

## 10. Decisiones de calidad de datos (referencia)

Para sustentación oral o memoria:

| Decisión | Motivo |
|----------|--------|
| Excluir filas con NA en columnas clave | Evitar incidentes incompletos en agregados |
| Tope edad 67 | Coherencia con rangos del catálogo Mede y outliers de captura |
| Bbox Medellín en coordenadas | Eliminar errores de geocodificación fuera del municipio |
| UTF-8 en CSV | Compatibilidad con PostgreSQL y caracteres en nombres de barrio |
| Exclusión COVID en **ajuste** predictivo (no en histórico) | Meses 2020-03…2020-08 atípicos por confinamiento |
| Territorio registro vs espacial | El texto del informe policial no siempre coincide con el polígono oficial |

Detalle de modelos predictivos e indicadores: **`DOCUMENTO_TECNICO_SISTEMA.md`**, sección 9.

---

*Fin del manual de carga y cambio de base de datos.*
