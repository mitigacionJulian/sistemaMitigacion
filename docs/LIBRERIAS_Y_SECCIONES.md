# Librerías y funciones por sección — ViaData Medellín

Documento de referencia para sustentación: **qué dependencia se usa, dónde, y para qué**.  
Versiones exactas: `frontend/package.json`, `backend/requirements.txt`, `requirements-etl.txt`.

---

## 1. Inventario global

### 1.1 Backend (`backend/requirements.txt`)

| Librería | Versión (mín.) | Uso en el sistema |
|----------|----------------|-------------------|
| **Django** | 5.x | Framework web, ORM, admin interno, migraciones |
| **djangorestframework** | 3.15+ | API REST JSON (`/api/...`) |
| **djangorestframework-simplejwt** | 5.3+ | Login JWT (`access` + `refresh`), claim `rol` en token |
| **django-cors-headers** | 4.3+ | Permitir peticiones desde Vite (`localhost:5173`) |
| **python-dotenv** | 1.0+ | Cargar `.env` en `config/settings.py` |
| **psycopg2-binary** | 2.9+ | Driver PostgreSQL (+ PostGIS si `DJANGO_USE_POSTGIS=1`) |
| **numpy** | 1.26+ | OLS, Poisson WLS, métricas R²/RMSE/MAPE, μ±3σ |
| **statsmodels** | 0.14+ | **Solo** ARIMA/SARIMA en `dashboard/modelos_arima.py` |
| **pytest**, **pytest-django**, **allure-pytest** | 8+ / 4.8+ / 2.13+ | Pruebas automatizadas; etiquetado JSON Allure |

**GeoDjango** (`django.contrib.gis`): incluido en Django cuando PostGIS está activo. Consultas espaciales en `territorio_sql.py`, hotspots, coroplética.

**Sin librería externa (stdlib / código propio):** cliente Gemini (`urllib.request`), validación teléfono CO, generación SQL dinámico, Poisson/OLS/estacional (implementados sobre NumPy en `estadistica_series.py`).

### 1.2 Frontend (`frontend/package.json`)

| Librería | Uso en el sistema |
|----------|-------------------|
| **react**, **react-dom** 19 | UI por componentes |
| **vite** | Bundler y servidor de desarrollo |
| **react-router-dom** 7 | Rutas: `/`, `/tablero`, `/mapa`, `/agente`, `/predicciones`, `/admin/usuarios`, `/admin/pruebas`, `/reporte/vista` |
| **recharts** 3 | Gráficos de líneas, barras, áreas (tablero, predicciones, reportes) |
| **leaflet** 1.9 | Motor de mapas |
| **react-leaflet** 5 | Componentes React sobre Leaflet |
| **leaflet.markercluster** | Agrupar miles de puntos de incidentes |
| **leaflet.heat** | Capa de densidad (heatmap) |
| **@bopen/leaflet-area-selection** | Dibujar polígono para filtrar por área |
| **topojson-client** | Decodificar TopoJSON territorial (menor peso que GeoJSON) |
| **html2canvas** | Captura del mapa para incrustar en reporte PDF |
| **react-zoom-pan-pinch** | Zoom con rueda/pellizco en gráficos (`ChartWheelZoom.jsx`) |

**CSS propio** (`frontend/src/index.css`): layout, responsive, impresión de reportes. No Tailwind ni Material UI.

### 1.3 ETL offline (`requirements-etl.txt`)

| Librería | Uso |
|----------|-----|
| **pandas** | Lectura/limpieza Mede, export parquet/CSV |
| **openpyxl** | Excel fuente si aplica |
| **matplotlib**, **seaborn** | EDA en scripts de exploración (`mede_eda_export.py`) |

El ETL **no corre** dentro del servidor Django en cada petición.

---

## 2. Autenticación y roles

| Elemento | Archivos | Librerías / técnica |
|----------|----------|---------------------|
| Registro / login | `backend/accounts/`, `frontend/src/pages/Login.jsx`, `Register.jsx` | DRF + SimpleJWT |
| Sesión en SPA | `frontend/src/context/AuthContext.jsx`, `auth/tokenStorage.js` | JWT en `localStorage`; cierre a 15 min sin actividad |
| Rol analista | `accounts/permissions.py` → `IsAnalista` | Permiso DRF; incluye **administrador** |
| Rol administrador | `accounts/admin_views.py`, `AdminUsuarios.jsx`, `AdminPruebas.jsx` | API `/api/admin/usuarios/`, `/api/admin/pruebas/` |
| Usuario demo admin | Migración `0005_seed_admin_user.py` | `admin` / `AdminUSB2026!` |

**Roles en BD:** `ciudadano`, `autoridad`, `analista`, `administrador` (seed `0002_seed_roles.py`).

---

## 3. Sección por sección (UI)

### 3.1 Inicio (`/` — `Landing.jsx`)

| Función | Implementación | Librería |
|---------|----------------|----------|
| Hero y enlaces | React + CSS | React |
| Mapa demostrativo | `LandingIncidentMap.jsx` | Leaflet, react-leaflet |
| Responsive mapa | `useSyncExternalStore` + `matchMedia` | API nativa del navegador |

---

### 3.2 Tablero de indicadores (`/tablero` — `Dashboard.jsx`)

| Función | Backend | Frontend |
|---------|---------|----------|
| KPIs comparativos | `dashboard/kpis.py` | Panel numérico React |
| Evolución mensual | `evolucion_mensual.py` | **Recharts** `BarChart` |
| Día de semana | `por_dia_semana.py` | Recharts barras apiladas |
| Matriz día×hora | `matriz_dia_hora.py` | Tabla HTML + heatmap CSS; en móvil gráficos por hora |
| Tops barrios/comunas | `tops.py` | Tabla con scroll horizontal |
| Distribución gravedad/clase | `distribucion_*.py` | Recharts |
| Filtros fecha/territorio | SQL parametrizado `territorio_sql.py` | Formulario `filter-grid` |
| Zoom en gráficos | — | **react-zoom-pan-pinch** + **Recharts** |
| Tabla bajo gráfico | — | `SerieLineChartDatosTabla.jsx` (sin librería extra) |
| Generar reporte | `reports/tablero.py` | `GenerarReporteButton` → modal |

**Consultas:** SQL crudo vía `django.db.connection` (sin ORM pesado para agregaciones).

---

### 3.3 Mapa analítico (`/mapa` — `Mapa.jsx`)

| Función | Librería | Archivo clave |
|---------|----------|---------------|
| Mapa base OSM | Leaflet | `map/MapView.jsx` |
| Puntos incidentes | react-leaflet `CircleMarker` / capas | `incidentes_mapa.py` |
| Clustering | leaflet.markercluster | `map/leafletPlugins.js` |
| Heatmap | leaflet.heat | idem |
| Coroplética comunas | TopoJSON + color ramp propio | `choropleth_territorial.py`, `topojson-client` |
| Hotspots (grid) | GeoDjango/SQL espacial | `hotspots.py` |
| Selección área usuario | @bopen/leaflet-area-selection | `MapAreaSelection.jsx` |
| Caché cliente mapa | — | `map/mapPageCache.js` (sin lib) |
| Captura para reporte | html2canvas | `map/mapCapture.js` |
| Worker expandir puntos | Web Worker nativo | `expandPuntosMapa.worker.js` |

---

### 3.4 Asistente IA (`/agente` — `Agente.jsx`)

| Función | Librería | Detalle |
|---------|----------|---------|
| Modelo lenguaje | **Google Gemini API** (HTTP) | `agent/gemini.py` — `urllib`, no SDK |
| Function calling | JSON schema en prompt | El modelo elige herramientas |
| Herramientas | Reutiliza módulos `dashboard/*` | `agent/tools.py` — mismos cálculos que tablero/predicciones |
| Caché respuestas | Django cache framework | `agent/cache.py` |
| Límite por IP/día | Django cache | idem |
| Acceso predicciones en chat | JWT opcional | `agent/auth.py` → `user_is_analista` |

Modelos configurables: `AGENT_MODEL_FLASH`, `AGENT_MODEL_FLASH_LITE` en `.env`.

---

### 3.5 Predicciones (`/predicciones` — `Predicciones.jsx`)

Cinco bloques en la UI (§1–§5). El selector de modelo aplica en §1, §3 y en el paso de total mensual que alimenta §5; §2 no tiene modelo predictivo; §5 **hereda** modelo y horizonte del §1 (sin selector propio en bloque 5).

#### Sección 1 — Proyección mensual (P01–P04)

| Modelo | Módulo backend | Librería |
|--------|----------------|----------|
| OLS | `predicciones_mensuales.py` | NumPy (`estadistica_series.py`) |
| Estacional | idem | NumPy (diseño con dummies mensuales) |
| Poisson log-lineal | idem | NumPy WLS |
| Media móvil | idem | Python |
| μ±3σ (`tres_sigma`) | idem | NumPy `mean`/`std` |
| ARIMA / SARIMA | `modelos_arima.py` | **statsmodels** `ARIMA`, `SARIMAX` |
| Hold-out | `predicciones_mensuales.py` | Lógica propia (3 o 6 meses reservados) |
| Gráfico bandas 3σ | — | Recharts `Area` + `Line` |
| Zoom | — | react-zoom-pan-pinch (`ChartWheelZoom.jsx`) |
| Tabla de puntos | — | `SerieLineChartDatosTabla.jsx` |

**Modelo adoptado (evaluación):** SARIMA(2,1,3)(1,1,1,12) para incidentes ciudad; alternativa media móvil 3 m.

#### Sección 2 — Prioridad territorial (P05)

| Función | Backend | Librería |
|---------|---------|----------|
| Ranking compuesto (pesos 30/15/20/20/15) | `prioridad_territorial.py` | SQL + NumPy (scores 0–100) |
| Tendencia por territorio | idem | **Delta de promedios mensuales** (no OLS del gráfico §1) |

Sin selector de modelo: fórmula fija y transparente.

#### Sección 3 — Carga esperada territorial (P08 · P09/P10)

| Función | Backend | Librería |
|---------|---------|----------|
| Proyección por comuna/barrio + ranking carga | `carga_esperada_territorial.py` | Reutiliza proyección mensual por territorio |
| Gráfico barras horizontales | — | Recharts |

**Modelo adoptado:** estacional por territorio, horizonte 3 meses; criterio principal = coherencia del ranking.

#### Sección 4 — Proporción víctimas fatales (P07)

| Función | Backend | Librería |
|---------|---------|----------|
| Estacional, logit_offset, ratio_compuesto, OLS, logística, MA, ARIMA, SARIMA | `proporcion_fatales_mensual.py` | NumPy |
| Hold-out y bandas en proyección | idem | Lógica propia + Recharts |

**Modelo adoptado:** estacional sobre % (default UI); alternativas logit con exposición y ratio compuesto.

#### Sección 5 — Patrones temporales (P12 · P13)

Un solo panel (`PatronesDiaHoraPanel.jsx`): matriz día×hora (P12) y barras por día de semana (P13).

| Función | Backend / UI | Librería |
|---------|--------------|----------|
| Total horizonte (modelo §1, incidentes) | `patrones_temporales_proyectados.py` | Reutiliza `predicciones_mensuales` |
| Reparto proporcional + Laplace | idem | SQL + NumPy |
| Heatmap P12, barras P13, zoom | `PatronesDiaHoraPanel.jsx` | Recharts; breakpoint 900px |

**Evaluación documentada:** `evaluaciones/EVALUACION_MODULO_PREDICCIONES.md` + CSV (`predicciones_seccion1` … `seccion5`, `predicciones_tres_sigma_evaluacion.csv`). Scripts: `backend/scripts/llenar_evaluacion_seccion*.py`.

---

### 3.6 Reportes (`/reporte/vista` — `ReportePreview.jsx`)

| Tipo reporte | Backend | Frontend |
|--------------|---------|----------|
| Tablero | `reports/tablero.py` | `ReporteTablero.jsx`, `TableroReportCharts.jsx` |
| Mapa | `reports/mapa.py` | `ReporteMapa.jsx` + imagen html2canvas |
| Predicciones | `reports/predicciones.py` | `ReportePredicciones.jsx` |
| Asistente | JSON en cliente | `ReporteAsistente.jsx` |
| Pruebas sistema | `accounts/pruebas_reporte.py` | `ReportePruebas.jsx` |

| Función reporte | Librería |
|-----------------|----------|
| Gráficos en PDF | **Recharts** (mismos componentes que UI) |
| Layout / logos / watermark | HTML + CSS |
| Pie de página cada hoja | CSS `@media print` + `ReportePrintLayer.jsx` (portal) |
| Numeración páginas | CSS `@page` margin boxes (Chrome/Edge) |
| Export PDF | **API del navegador** `window.print()` — no jsPDF |

---

### 3.7 Gestión de usuarios (`/admin/usuarios` — solo rol administrador)

| Función | Backend | Frontend |
|---------|---------|----------|
| Listar / CRUD usuarios | `accounts/admin_views.py` | `AdminUsuarios.jsx` |
| Serializers | `admin_serializers.py` | `api/client.js` (`fetchAdminUsuarios`, etc.) |
| Permiso | `IsAdministrador` | `RequireAdministrador.jsx` |

Sin librería de UI de tablas (DataGrid); tabla HTML + CSS propio.

---

### 3.8 Panel de pruebas (`/admin/pruebas` — solo rol administrador)

| Función | Backend | Frontend |
|---------|---------|----------|
| Ejecutar suite pytest | `accounts/pruebas_runner.py` | Botón «Ejecutar suite» |
| Parseo JSON Allure | `parse_allure_summary()` | KPIs, tablas por módulo y por caso |
| Reporte imprimible | `accounts/pruebas_reporte.py`, `POST /api/admin/pruebas/reporte/` | `GenerarReporteButton` → `ReportePruebas.jsx` |
| Permiso ejecución UI | `ALLOW_ADMIN_TEST_RUNNER` + `DJANGO_DEBUG` en `.env` | Deshabilita botón si producción |

**Librerías:** pytest + allure-pytest (etiquetado en `allure_reporting.py`). **Sin Node.js ni Java** en este flujo.

---

## 4. Mapa de archivos → responsabilidad

```
backend/
  accounts/          Auth JWT, roles, admin usuarios, panel pruebas
  dashboard/         Indicadores, predicciones, mapa (SQL/NumPy/statsmodels)
  agent/             Gemini + tools
  reports/           Payload JSON para reportes
  config/            Settings, URLs

frontend/src/
  pages/             Pantallas por ruta
  components/        Reportes, ChartWheelZoom, PatronesDiaHoraPanel
  map/               Leaflet, captura, TopoJSON
  api/client.js      Cliente HTTP hacia /api
  context/           AuthContext
```

---

## 5. Dependencias explícitamente NO usadas

| Tecnología | Motivo |
|------------|--------|
| scikit-learn / TensorFlow | Modelos acordados son estadísticos clásicos |
| Chart.js / D3 | Se eligió Recharts (declarativo en React) |
| Mapbox / Google Maps | Leaflet open source + OSM |
| jsPDF / Puppeteer | PDF vía impresión nativa del navegador |
| Redux | Estado local + Context para auth |
| pandas en API | Solo ETL offline |

---

## 6. Cómo responder en la sustentación (plantilla)

> “En la sección **[X]**, el frontend usa **[Recharts/Leaflet/…]** para **[visualización]**, y el cálculo lo hace el backend en **`dashboard/archivo.py`** usando **[NumPy/statsmodels/SQL]**, porque **[motivo breve]**.”

Ejemplo:

> “En proyección mensual, ARIMA está en `modelos_arima.py` con **statsmodels**; OLS y Poisson los implementamos nosotros con **NumPy** en `estadistica_series.py` para no depender de scikit-learn y mantener control de las métricas del grado.”

---

*Última actualización: 2026-06-26 — §3.8 panel pruebas; reporte PDF sin Allure HTML.*
