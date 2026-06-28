# Cierre del proyecto — ViaData Medellín

**Proyecto:** Sistema de información para mitigación de accidentes de tránsito (caso Medellín, datos Mede)  
**Institución:** Universidad San Buenaventura — proyecto de grado  
**Estado del software:** funcional para demo y sustentación  
**Última actualización:** 2026-06-26  

---

## 1. Alcance entregado

| Módulo | Ruta / API | Estado | Notas |
|--------|------------|--------|-------|
| Mapa analítico | `/`, `/mapa` | ✅ Entregado | Puntos, heatmap, clusters, G03, P14, modo registro/espacial |
| Tablero descriptivo | `/tablero` | ✅ Entregado | KPIs, series, matrices día×hora, rankings |
| Asistente IA | `/agente` | ✅ Entregado | Gemini + function calling; predicciones con JWT analista/admin |
| Predicciones | `/predicciones` | ✅ **Evaluado y cerrado** | Cinco bloques §1–§5; ver `evaluaciones/EVALUACION_MODULO_PREDICCIONES.md` |
| Reportes imprimibles | `/reporte/vista` | ✅ Entregado | Tablero, mapa, predicciones; pie en cada hoja |
| Autenticación JWT | `/login`, `/registro` | ✅ Entregado | Roles ciudadano, analista, administrador, autoridad (reservado) |
| Gestión usuarios | `/admin/usuarios` | ✅ Entregado | Solo rol administrador |
| Panel pruebas | `/admin/pruebas` | ✅ Entregado | Ejecutar pytest, UI resultados, reporte PDF (sin Node/Java) |
| ETL y carga PostGIS | Scripts raíz + SQL | ✅ Documentado | `MANUAL_CARGA_DATOS_BD.md` |

---

## 2. Evaluación del módulo Predicciones (cerrada 2026-06-18)

| Bloque UI | Decisión adoptada |
|-----------|-------------------|
| §1 Proyección mensual | **SARIMA(2,1,3)(1,1,1,12)** incidentes ciudad; alternativa media móvil 3 m |
| §2 Prioridad P05 | Índice 30/15/20/20/15; delta de promedios en tendencia |
| §3 Carga territorial | Estacional por territorio; ranking > cifras exactas |
| §4 % fatales P07 | Estacional sobre %; alternativas logit_offset y ratio_compuesto |
| §5 Patrones P12+P13 | Hereda §1; reparto histórico + Laplace |

**Registros:** CSV en `evaluaciones/` + documento unificado `EVALUACION_MODULO_PREDICCIONES.md` v2.0.

**Criterio de confiabilidad exploratoria:** MAPE hold-out ≤ 20 % (≈ 80 % precisión estimada).

---

## 3. Alcance explícitamente omitido (cronograma)

| ID / tema | Motivo |
|-----------|--------|
| P11 ranking vía / punto crítico | Mede no alimenta catálogos `via` / `punto_critico` |
| G04 buffer punto crítico | Tabla `punto_critico` vacía |
| G05 filtro bbox mapa | Redundante con comuna/barrio |
| P15 / ML espacial avanzado | Fuera de alcance v1; modelos parsimoniosos |
| Ingesta automática diaria | ETL manual documentado |
| PDF servidor (Puppeteer/jsPDF) | Impresión nativa del navegador |
| scikit-learn / redes neuronales | No acordado con el director |

---

## 4. Pendientes hacia el informe de grado

| Tarea | Fuente sugerida |
|-------|-----------------|
| Marco teórico y conceptual | Literatura (Lord & Mannering; Washington et al.; PostGIS) + `GUIA_SUSTENTACION_COMPLETA.md` §7 |
| Capítulo resultados (predicciones) | `EVALUACION_MODULO_PREDICCIONES.md` + CSV |
| Conclusiones y trabajo futuro | Este documento §3 + limitaciones en evaluación |
| Anexos (instalación, ETL, esquema BD) | Manuales + `esquema_base_datos.sql` |
| Redacción narrativa integrada | En curso — **`docs/VIADATA_DOCUMENTACION_INTEGRAL.md`** |

---

## 5. Checklist de cierre técnico

- [x] Backend pytest en verde (`dashboard`, `agent`, `reports`, `accounts`)
- [x] PostGIS verificable (`manage.py check_postgis`)
- [x] Cinco secciones de Predicciones evaluadas con CSV reproducible
- [x] Usuario admin demo (`admin` / `AdminUSB2026!`, migración `0005_seed_admin_user`)
- [x] Documentación en `docs/` versionada en Git (índice `docs/README.md`)
- [x] Panel `/admin/pruebas`: pytest + reporte imprimible documentado
- [ ] Integración final al documento de tesis (en curso)
- [ ] Sustentación oral (usar `GUIA_SUSTENTACION_COMPLETA.md`)

---

## 6. Documentación vigente (sin duplicados obsoletos)

| Archivo | Rol |
|---------|-----|
| `README.md` | Inicio rápido (versionado en Git) |
| `docs/README.md` | Índice de documentación (versionada en Git) |
| `docs/DOCUMENTO_TECNICO_SISTEMA.md` | Arquitectura y APIs |
| `docs/LIBRERIAS_Y_SECCIONES.md` | Librerías por pantalla |
| `docs/GUIA_SUSTENTACION_LIBRERIAS.md` | FAQ corto jurado |
| `docs/GUIA_SUSTENTACION_COMPLETA.md` | Demo, fórmulas, FAQ integral |
| `docs/MANUAL_INSTALACION_EJECUCION.md` | Instalación |
| `docs/MANUAL_CARGA_DATOS_BD.md` | ETL y PostGIS |
| `docs/DOCUMENTACION_PRUEBAS_SOFTWARE.md` | Casos pytest documentados |
| `docs/VIADATA_DOCUMENTACION_INTEGRAL.md` | **Documento maestro para tesis** |
| `docs/CIERRE_PROYECTO.md` | **Este archivo** |
| `docs/esquema_base_datos.sql` | DDL referencia |
| `evaluaciones/LEEME_PRUEBAS_SISTEMA.txt` | Guía panel admin pruebas |
| `evaluaciones/EVALUACION_MODULO_PREDICCIONES.md` | Evaluación modelos |

**Obsoleto / redundante:** archivos `.txt` en `evaluaciones/` (contenido consolidado en el MD v2.0). Pueden eliminarse.

**Retirado:** `backend/ARBOL.md`, wiki duplicada `docs/sistemaMitigacion.wiki/` (si existía en copias antiguas).

---

## 7. Usuario de demostración

| Rol | Usuario | Contraseña | Acceso |
|-----|---------|------------|--------|
| Administrador | `admin` | `AdminUSB2026!` | Todo + `/admin/usuarios` + `/admin/pruebas` |

Crear analista adicional: `/registro` o `createsuperuser` + asignar rol en admin.

---

*Documento de cierre — ViaData Medellín — USB.*
