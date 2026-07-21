# Guía rápida — Preguntas del jurado sobre librerías e implementación

Respuestas cortas para sustentación oral. Detalle ampliado en `LIBRERIAS_Y_SECCIONES.md`.

---

## Preguntas generales

**¿Con qué está hecho el frontend?**  
React 19 + Vite, enrutamiento con React Router, gráficos con Recharts, mapa con Leaflet/react-leaflet, estilos CSS propios (sin Bootstrap).

**¿Con qué está hecho el backend?**  
Django 5 + Django REST Framework, JWT con `djangorestframework-simplejwt`, PostgreSQL/PostGIS vía GeoDjango, CORS con `django-cors-headers`.

**¿Usa pandas en producción?**  
No en la API en línea. Pandas está en el **ETL offline** (`requirements-etl.txt`) para limpiar y cargar Mede. En runtime el backend usa **SQL + NumPy** (y **statsmodels** solo para ARIMA/SARIMA).

**¿Por qué no TensorFlow / scikit-learn?**  
Los modelos acordados con el director son **descriptivos/estadísticos** (OLS, Poisson, media móvil, μ±3σ, ARIMA/SARIMA). No hay entrenamiento de redes neuronales ni Random Forest implementado aún.

**¿Cómo habla con la IA?**  
Cliente HTTP propio (`urllib`) a la **API REST de Google Gemini** (`generateContent` + function calling). No usamos el SDK oficial de Google en Python.

---

## Por sección (una frase)

| Sección | Librería clave | Qué hace |
|---------|----------------|----------|
| Login / registro | SimpleJWT + React Context | Tokens JWT; sesión 15 min inactividad |
| Tablero | Recharts + DRF | KPIs SQL; gráficos de barras/líneas |
| Mapa | Leaflet + plugins | Puntos, heatmap, clusters, coroplética TopoJSON |
| Asistente | Gemini API | LLM elige herramientas que llaman al mismo backend |
| Predicciones | NumPy + statsmodels + Recharts | Modelos en Python; gráficos y tablas en React |
| Reportes | Recharts + html2canvas + CSS print | Vista previa SPA; PDF vía “Imprimir” del navegador |
| Admin usuarios | DRF (CRUD propio) | Sin Django Admin en la UI pública |
| Admin pruebas | pytest + allure-pytest (JSON) | Panel `/admin/pruebas`; reporte PDF sin Allure HTML |

---

## Predicciones — modelos (respuesta tipo)

| Modelo | ¿Librería? | Idea en una línea |
|--------|------------|-------------------|
| OLS | NumPy (ecuaciones normales propias) | Recta `y = a + b·t` sobre meses |
| Estacional | NumPy | OLS + variables dummy por mes calendario |
| Poisson | NumPy (WLS log-lineal) | Conteos con tendencia en escala log |
| Media móvil | Python puro | Promedio de últimos *k* meses |
| μ±3σ | NumPy (`mean`, `std`) | Banda histórica media ± 3 desviaciones |
| ARIMA / SARIMA | **statsmodels** | `ARIMA.fit` / `SARIMAX`; proyección multi-paso |

**Hold-out:** lógica propia en `predicciones_mensuales.py` (reserva últimos N meses, reentrena, compara MAPE).

---

## Mapa — plugins Leaflet

| Necesidad | Librería |
|-----------|----------|
| Mapa base | `leaflet`, `react-leaflet` |
| Muchos puntos agrupados | `leaflet.markercluster` |
| Mapa de calor | `leaflet.heat` |
| Dibujar polígono de área | `@bopen/leaflet-area-selection` |
| Comunas más livianas | `topojson-client` (decode TopoJSON → GeoJSON) |
| Captura para reporte | `html2canvas` |

---

## Gráficos — zoom

**Librería:** `react-zoom-pan-pinch` en `ChartWheelZoom.jsx`.  
Zoom **visual** (no recorta fechas). Tooltip con portal fijo (`WheelZoomTooltip.jsx`) para que no se deforme al ampliar.

---

## Reportes — pie de página en cada hoja

**Sin librería PDF.** HTML + `@media print` + `position: fixed` en portal (`ReportePrintLayer.jsx`). Chrome usa `@page` margin boxes para “Página X de Y”.

---

## Usuario administrador (demo)

- Usuario: `admin`  
- Contraseña: `AdminUSB2026!` (creado en migración `accounts/0005_seed_admin_user.py`)  
- Rol `administrador`: gestión de usuarios, panel de pruebas (`/admin/pruebas`) + acceso completo (equivalente analista en predicciones/reportes).

---

## Pruebas de software — ¿cómo las ejecuta el administrador?

**Desde la UI:** `/admin/pruebas` → *Ejecutar suite* (pytest en segundo plano) → resultados en pantalla → *Generar reporte* → PDF.

**Librerías:** pytest + allure-pytest (JSON etiquetado). **No usa Node.js ni Java** en la aplicación.

**En consola:** `python -m pytest -q` desde `backend/`.
