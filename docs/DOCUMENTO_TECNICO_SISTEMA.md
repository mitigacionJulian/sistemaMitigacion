# Documento técnico — ViaData Medellín

Sistema web de visualización y análisis de accidentalidad vial (datos Mede, Medellín ~2014–2021).  
Proyecto de grado — USB.

**Complemento obligatorio para sustentación:** [LIBRERIAS_Y_SECCIONES.md](./LIBRERIAS_Y_SECCIONES.md) (librerías por pantalla).

---

## 1. Arquitectura

```
[Navegador SPA React/Vite :5173]
        │  /api → proxy Vite (dev) o mismo host (prod)
        ▼
[Django REST :8000]
        │
        ├── PostgreSQL (+ PostGIS)
        └── Cache (Gemini / agente — Django cache, ej. LocMem o Redis)
```

- **Sin microservicios:** monolito Django + SPA estática.
- **Autenticación:** JWT (stateless); rol de negocio en tabla `perfil_usuario`.
- **Autorización:** permisos DRF (`IsAnalista`, `IsAdministrador`).

---

## 2. Módulos backend

| App | Responsabilidad |
|-----|-----------------|
| `accounts` | Usuarios Django, roles, JWT, reset clave WhatsApp, **API admin usuarios y panel de pruebas** |
| `dashboard` | KPIs, series, mapa, predicciones, prioridad, carga territorial |
| `agent` | Chat Gemini + function calling sobre APIs internas |
| `reports` | Metadatos y cuerpo JSON para reportes imprimibles |
| `config` | Settings, URLs, PostGIS |

Predicciones y tablero comparten **filtros territoriales** (`FiltrosKpi`, `territorio_sql.py`).

---

## 3. Rutas frontend

| Ruta | Componente | Acceso |
|------|------------|--------|
| `/` | Landing | Público |
| `/tablero` | Dashboard | Público |
| `/mapa` | Mapa | Público |
| `/agente` | Agente | Público (tools predictivos si analista/admin) |
| `/predicciones` | Predicciones | Analista o administrador |
| `/reporte/vista` | ReportePreview | Analista o administrador |
| `/admin/usuarios` | AdminUsuarios | Solo administrador |
| `/admin/pruebas` | AdminPruebas | Solo administrador |
| `/login`, `/registro` | Auth | Público |

---

## 4. API REST (prefijo `/api`)

| Prefijo | Ejemplos |
|---------|----------|
| `/auth/` | login, refresh, register, me, password-reset |
| `/admin/` | usuarios, roles, **pruebas** (ejecutar suite, reporte imprimible) |
| `/dashboard/` | kpis, evolucion, matriz, predicciones-mensuales, mapa, … |
| `/agent/` | chat |
| `/reportes/` | tablero, mapa, predicciones, preview |

Contrato: JSON; errores con `detail` o campos de validación DRF.

---

## 5. Datos

- **Fuente:** Mede (víctimas/incidentes depurados).
- **Carga:** scripts ETL raíz + `carga_mede_pgadmin.sql` (ver manuales de carga si existen en copia local).
- **Espacial:** comunas/barrios en PostGIS; modo `registro` vs `espacial` en filtros.
- **Exclusión COVID:** mar–ago 2020 opcional en ajuste de modelos.

---

## 6. Modelos predictivos (resumen)

Implementados en Python; ver sección 3.5 de `LIBRERIAS_Y_SECCIONES.md`.

- Conteos: OLS, estacional, Poisson, media móvil, ARIMA, SARIMA, μ±3σ.
- % fatales: regresión sobre proporción mensual.
- Territorial: agregación de proyección mensual + ranking prioridad.
- Patrones: prorrateo histórico día×hora / día semana.

Métricas: R², RMSE, MAPE; **hold-out** últimos 3–6 meses; umbral orientativo 80 % precisión (100 − MAPE).

---

## 7. Reportes

- Generados en cliente a partir de JSON del backend + captura mapa (mapa).
- Secciones: tablero, mapa, predicciones, asistente, **pruebas del sistema** (solo administrador).
- Impresión: CSS `@media print`, marca de agua, pie con título en **cada hoja**.
- No hay servidor de generación PDF.

---

## 8. Pruebas de software

### Consola

```powershell
cd backend
.\.venv\Scripts\activate
python -m pytest -q
```

Incluye `accounts`, `dashboard`, `agent`, `reports`. PostGIS: `python manage.py check_postgis` aparte.

Con salida estructurada (JSON Allure vía `allure-pytest`):

```powershell
python -m pytest --alluredir=allure-results --clean-alluredir -q
```

### Panel administrador (`/admin/pruebas`)

| Botón | Función |
|-------|---------|
| Ejecutar suite | `pytest` en segundo plano; resultados en UI |
| Generar reporte | Vista previa → Imprimir / Guardar PDF |

Requiere `DJANGO_DEBUG=1` o `ALLOW_ADMIN_TEST_RUNNER=1` en `.env`. **No requiere Node.js ni Java.**

API: `GET/POST /api/admin/pruebas/`, `POST .../ejecutar/`, `POST .../reporte/`.

Guía: `evaluaciones/LEEME_PRUEBAS_SISTEMA.txt` · Casos documentados: `docs/DOCUMENTACION_PRUEBAS_SOFTWARE.md`.

Allure HTML oficial (opcional, consola): `run_pytest_allure.ps1` (Node.js + Java).

---

## 9. Seguridad (nivel grado)

- Contraseñas: validadores Django.
- JWT expira; refresh token; idle 15 min en SPA.
- CORS restringido a origen frontend en producción.
- `.env` fuera de Git; `GEMINI_API_KEY` solo servidor.

---

## 10. Despliegue local

Ver `README.md` en la raíz del repositorio.

Usuario administrador de demostración: migración `accounts/0005_seed_admin_user` → `admin` / `AdminUSB2026!`.

---

## 11. Documentos relacionados (carpeta `docs/`)

| Archivo | Contenido |
|---------|-----------|
| `LIBRERIAS_Y_SECCIONES.md` | Librerías y funciones por sección |
| `GUIA_SUSTENTACION_LIBRERIAS.md` | FAQ corto para jurado |
| `GUIA_SUSTENTACION_COMPLETA.md` | Demo, fórmulas, FAQ integral, checklist |
| `CIERRE_PROYECTO.md` | Alcance final, módulos cerrados, pendientes |
| `MANUAL_INSTALACION_EJECUCION.md` | Instalación y ejecución |
| `MANUAL_CARGA_DATOS_BD.md` | ETL y PostGIS |
| `DOCUMENTACION_PRUEBAS_SOFTWARE.md` | Casos pytest + panel admin |
| `evaluaciones/EVALUACION_MODULO_PREDICCIONES.md` | Evaluación cerrada del módulo Predicciones (§1–§5) + CSV |
| `evaluaciones/LEEME_PRUEBAS_SISTEMA.txt` | Guía panel `/admin/pruebas` |

La carpeta `docs/` se versiona en Git (excepto `docs/shp/` opcional).

---

*Documento técnico — ViaData — junio 2026*
