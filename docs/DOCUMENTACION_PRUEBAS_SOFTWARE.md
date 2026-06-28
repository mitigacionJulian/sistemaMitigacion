# Documentación de pruebas de software — ViaData Medellín

> **Versión:** 1.0 · **Fecha:** 2026-06-26 · **Total casos:** 160

## 1. Introducción

Este documento registra los **casos de prueba automatizados** del backend ViaData (Django REST), organizados por módulo funcional. Cada caso utiliza la plantilla del curso de pruebas de software:
título, prioridad, objetivo, precondiciones, criterio de aceptación, resultado y observaciones.

### 1.1 Alcance

| Aspecto | Detalle |
|---------|---------|
| Componente probado | Backend Django: `accounts`, `dashboard`, `agent`, `reports` |
| Tipo de prueba | Unitarias, lógica de negocio y API REST (caja negra sobre endpoints) |
| Framework | pytest 9.x + pytest-django + allure-pytest (etiquetado JSON) |
| Base de datos de prueba | SQLite (`config.settings_test`) |
| Consulta en la aplicación | Panel `/admin/pruebas` (UI + reporte PDF; sin Node/Java) |
| Reporte Allure HTML (opcional) | Consola: `backend/run_pytest_allure.ps1` (requiere Node.js + Java) |
| Validación PostGIS | Fuera de pytest: `python manage.py check_postgis` en PostgreSQL real |

### 1.2 Cómo ejecutar

**Consola:**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest --alluredir=allure-results --clean-alluredir
```

**Panel administrador** (`/admin/pruebas`, rol administrador): botones *Ejecutar suite* y *Generar reporte* (PDF). Ver `evaluaciones/LEEME_PRUEBAS_SISTEMA.txt`.

**Allure HTML opcional** (consola, Node.js + Java):

```powershell
.\run_pytest_allure.ps1 -Serve
```

### 1.3 Escala de prioridad

| Prioridad | Significado |
|-----------|-------------|
| **Alta** | Seguridad, autenticación, permisos, API de predicciones, agente IA |
| **Media** | Tablero, mapa, modelos estadísticos, reportes, regresiones |
| **Baja** | Optimizaciones de rendimiento y utilidades auxiliares |

### 1.4 Resumen por módulo

| Módulo | Archivos de prueba | Casos |
|--------|-------------------|-------|
| Módulo 1 — Cuentas y autenticación | 4 | 18 |
| Módulo 2 — Asistente IA (Gemini) | 1 | 8 |
| Módulo 3 — Reportes imprimibles | 5 | 20 |
| Módulo 4 — Dashboard, mapa y predicciones | 27 | 114 |
| **Total** | **36** | **160** |

### 1.5 Plantilla de caso de prueba

Cada caso documentado incluye la siguiente tabla:

| Campo | Descripción |
|-------|-------------|
| **ID** | Identificador único del caso |
| **Título** | Nombre legible del escenario |
| **Función pytest** | Nombre técnico del test automatizado |
| **Prioridad** | Alta / Media / Baja |
| **Objetivo** | Qué se pretende validar |
| **Precondiciones** | Estado y datos requeridos antes de ejecutar |
| **Criterio de aceptación** | Condición para considerar exitoso el caso |
| **Resultado** | Salida de la última ejecución documentada |
| **Estado** | Aprobado / No aprobado |
| **Observaciones** | Notas adicionales |

---

## 2. Módulo 1 — Cuentas y autenticación

### 2.1 API administración de usuarios

**Archivo:** `accounts/tests/test_admin_api.py` · **Casos:** 5 · **Prioridad del bloque:** Alta

#### Caso `ACC-ADMIN_API-001` — Admin usuarios requiere rol administrador

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_API-001` |
| **Título** | Admin usuarios requiere rol administrador |
| **Función pytest** | `test_admin_usuarios_requires_administrador` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Admin usuarios requiere rol administrador» se comporta según lo definido en API administración de usuarios. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Acceso denegado (401/403) sin el rol o token requerido. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_API-002` — Admin list create update delete

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_API-002` |
| **Título** | Admin list create update delete |
| **Función pytest** | `test_admin_list_create_update_delete` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Admin list create update delete» se comporta según lo definido en API administración de usuarios. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_API-003` — Admin cannot delete self

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_API-003` |
| **Título** | Admin cannot delete self |
| **Función pytest** | `test_admin_cannot_delete_self` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Admin cannot delete self» se comporta según lo definido en API administración de usuarios. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_API-004` — Rol administrador access predicciones

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_API-004` |
| **Título** | Rol administrador access predicciones |
| **Función pytest** | `test_administrador_access_predicciones` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Rol administrador access predicciones» se comporta según lo definido en API administración de usuarios. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_API-005` — Seed admin user exists

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_API-005` |
| **Título** | Seed admin user exists |
| **Función pytest** | `test_seed_admin_user_exists` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Seed admin user exists» se comporta según lo definido en API administración de usuarios. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 2.2 Panel admin — ejecución y reporte de pruebas

**Archivo:** `accounts/tests/test_admin_pruebas_api.py` · **Casos:** 7 · **Prioridad del bloque:** Media

#### Caso `ACC-ADMIN_PRUE-001` — Admin pruebas estado requiere rol administrador

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_PRUE-001` |
| **Título** | Admin pruebas estado requiere rol administrador |
| **Función pytest** | `test_admin_pruebas_estado_requires_administrador` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Admin pruebas estado requiere rol administrador» se comporta según lo definido en Panel admin — ejecución y reporte de pruebas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Acceso denegado (401/403) sin el rol o token requerido. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_PRUE-002` — Admin pruebas estado payload

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_PRUE-002` |
| **Título** | Admin pruebas estado payload |
| **Función pytest** | `test_admin_pruebas_estado_payload` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Admin pruebas estado payload» se comporta según lo definido en Panel admin — ejecución y reporte de pruebas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_PRUE-003` — Admin pruebas ejecutar disabled

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_PRUE-003` |
| **Título** | Admin pruebas ejecutar disabled |
| **Función pytest** | `test_admin_pruebas_ejecutar_disabled` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Admin pruebas ejecutar disabled» se comporta según lo definido en Panel admin — ejecución y reporte de pruebas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_PRUE-004` — Parse allure summary incluye casos

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_PRUE-004` |
| **Título** | Parse allure summary incluye casos |
| **Función pytest** | `test_parse_allure_summary_incluye_casos` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Parse allure summary incluye casos» se comporta según lo definido en Panel admin — ejecución y reporte de pruebas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_PRUE-005` — Admin pruebas reporte imprimible sin resultados

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_PRUE-005` |
| **Título** | Admin pruebas reporte imprimible sin resultados |
| **Función pytest** | `test_admin_pruebas_reporte_imprimible_sin_resultados` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Admin pruebas reporte imprimible sin resultados» se comporta según lo definido en Panel admin — ejecución y reporte de pruebas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_PRUE-006` — Admin pruebas reporte imprimible con resultados

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_PRUE-006` |
| **Título** | Admin pruebas reporte imprimible con resultados |
| **Función pytest** | `test_admin_pruebas_reporte_imprimible_con_resultados` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Admin pruebas reporte imprimible con resultados» se comporta según lo definido en Panel admin — ejecución y reporte de pruebas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-ADMIN_PRUE-007` — State file no rompe estado

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-ADMIN_PRUE-007` |
| **Título** | State file no rompe estado |
| **Función pytest** | `test_state_file_no_rompe_estado` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «State file no rompe estado» se comporta según lo definido en Panel admin — ejecución y reporte de pruebas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 2.3 Autenticación JWT y registro

**Archivo:** `accounts/tests/test_auth_api.py` · **Casos:** 5 · **Prioridad del bloque:** Alta

#### Caso `ACC-AUTH_API-001` — Register creates user perfil and JWT

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-AUTH_API-001` |
| **Título** | Register creates user perfil and JWT |
| **Función pytest** | `test_register_creates_user_perfil_and_jwt` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Register creates user perfil and JWT» se comporta según lo definido en Autenticación JWT y registro. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-AUTH_API-002` — Register rol analista

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-AUTH_API-002` |
| **Título** | Register rol analista |
| **Función pytest** | `test_register_analista` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Register rol analista» se comporta según lo definido en Autenticación JWT y registro. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-AUTH_API-003` — Login JWT me logout

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-AUTH_API-003` |
| **Título** | Login JWT me logout |
| **Función pytest** | `test_login_jwt_me_logout` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Login JWT me logout» se comporta según lo definido en Autenticación JWT y registro. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-AUTH_API-004` — Login con parámetros inválidos credenciales

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-AUTH_API-004` |
| **Título** | Login con parámetros inválidos credenciales |
| **Función pytest** | `test_login_invalid_credentials` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Login con parámetros inválidos credenciales» se comporta según lo definido en Autenticación JWT y registro. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `ACC-AUTH_API-005` — Password reset whatsapp flow

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-AUTH_API-005` |
| **Título** | Password reset whatsapp flow |
| **Función pytest** | `test_password_reset_whatsapp_flow` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Password reset whatsapp flow» se comporta según lo definido en Autenticación JWT y registro. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 2.4 Permisos módulo predicciones

**Archivo:** `accounts/tests/test_predicciones_permission.py` · **Casos:** 1 · **Prioridad del bloque:** Alta

#### Caso `ACC-PREDICCION-001` — Predicciones requiere rol analista

| Campo | Descripción |
|-------|-------------|
| **ID** | `ACC-PREDICCION-001` |
| **Título** | Predicciones requiere rol analista |
| **Función pytest** | `test_predicciones_requires_analista` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Predicciones requiere rol analista» se comporta según lo definido en Permisos módulo predicciones. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Acceso denegado (401/403) sin el rol o token requerido. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

## 3. Módulo 2 — Asistente IA (Gemini)

### 3.1 Chat Gemini y herramientas

**Archivo:** `agent/tests/test_agent_api.py` · **Casos:** 8 · **Prioridad del bloque:** Alta

#### Caso `AGE-AGENT_API-001` — Agent info modo público

| Campo | Descripción |
|-------|-------------|
| **ID** | `AGE-AGENT_API-001` |
| **Título** | Agent info modo público |
| **Función pytest** | `test_agent_info_public` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Agent info modo público» se comporta según lo definido en Chat Gemini y herramientas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `AGE-AGENT_API-002` — Agent info rol analista

| Campo | Descripción |
|-------|-------------|
| **ID** | `AGE-AGENT_API-002` |
| **Título** | Agent info rol analista |
| **Función pytest** | `test_agent_info_analista` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Agent info rol analista» se comporta según lo definido en Chat Gemini y herramientas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `AGE-AGENT_API-003` — Agent chat requiere message

| Campo | Descripción |
|-------|-------------|
| **ID** | `AGE-AGENT_API-003` |
| **Título** | Agent chat requiere message |
| **Función pytest** | `test_agent_chat_requires_message` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Agent chat requiere message» se comporta según lo definido en Chat Gemini y herramientas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Acceso denegado (401/403) sin el rol o token requerido. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `AGE-AGENT_API-004` — Agent chat modo público no JWT

| Campo | Descripción |
|-------|-------------|
| **ID** | `AGE-AGENT_API-004` |
| **Título** | Agent chat modo público no JWT |
| **Función pytest** | `test_agent_chat_public_no_jwt` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Agent chat modo público no JWT» se comporta según lo definido en Chat Gemini y herramientas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `AGE-AGENT_API-005` — Agent chat rol analista enables predictions

| Campo | Descripción |
|-------|-------------|
| **ID** | `AGE-AGENT_API-005` |
| **Título** | Agent chat rol analista enables predictions |
| **Función pytest** | `test_agent_chat_analista_enables_predictions` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Agent chat rol analista enables predictions» se comporta según lo definido en Chat Gemini y herramientas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `AGE-AGENT_API-006` — Analyst tools blocked for modo público

| Campo | Descripción |
|-------|-------------|
| **ID** | `AGE-AGENT_API-006` |
| **Título** | Analyst tools blocked for modo público |
| **Función pytest** | `test_analyst_tools_blocked_for_public` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Analyst tools blocked for modo público» se comporta según lo definido en Chat Gemini y herramientas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `AGE-AGENT_API-007` — Analyst tools available for rol analista

| Campo | Descripción |
|-------|-------------|
| **ID** | `AGE-AGENT_API-007` |
| **Título** | Analyst tools available for rol analista |
| **Función pytest** | `test_analyst_tools_available_for_analista` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Analyst tools available for rol analista» se comporta según lo definido en Chat Gemini y herramientas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `AGE-AGENT_API-008` — Normalize question cache key scopes

| Campo | Descripción |
|-------|-------------|
| **ID** | `AGE-AGENT_API-008` |
| **Título** | Normalize question cache key scopes |
| **Función pytest** | `test_normalize_question_cache_key_scopes` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Normalize question cache key scopes» se comporta según lo definido en Chat Gemini y herramientas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

## 4. Módulo 3 — Reportes imprimibles

### 4.1 Reporte mapa

**Archivo:** `reports/tests/test_reporte_mapa_api.py` · **Casos:** 3 · **Prioridad del bloque:** Media

#### Caso `REP-REPORTE_MA-001` — Reporte mapa requiere rol analista

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_MA-001` |
| **Título** | Reporte mapa requiere rol analista |
| **Función pytest** | `test_reporte_mapa_requires_analista` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reporte mapa requiere rol analista» se comporta según lo definido en Reporte mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Acceso denegado (401/403) sin el rol o token requerido. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_MA-002` — Reporte mapa respuesta exitosa con datos simulados

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_MA-002` |
| **Título** | Reporte mapa respuesta exitosa con datos simulados |
| **Función pytest** | `test_reporte_mapa_ok_mock` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reporte mapa respuesta exitosa con datos simulados» se comporta según lo definido en Reporte mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_MA-003` — Reporte mapa rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_MA-003` |
| **Título** | Reporte mapa rango invalido |
| **Función pytest** | `test_reporte_mapa_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reporte mapa rango invalido» se comporta según lo definido en Reporte mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 4.2 Lógica payload reporte mapa

**Archivo:** `reports/tests/test_reporte_mapa_logica.py` · **Casos:** 5 · **Prioridad del bloque:** Media

#### Caso `REP-REPORTE_MA-001` — Resolve mapa nivel comuna con filtro comuna

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_MA-001` |
| **Título** | Resolve mapa nivel comuna con filtro comuna |
| **Función pytest** | `test_resolve_mapa_nivel_comuna_con_filtro_comuna` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Resolve mapa nivel comuna con filtro comuna» se comporta según lo definido en Lógica payload reporte mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_MA-002` — Resolve mapa nivel barrio con filtro barrio

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_MA-002` |
| **Título** | Resolve mapa nivel barrio con filtro barrio |
| **Función pytest** | `test_resolve_mapa_nivel_barrio_con_filtro_barrio` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Resolve mapa nivel barrio con filtro barrio» se comporta según lo definido en Lógica payload reporte mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_MA-003` — Resolve mapa nivel detalle comuna

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_MA-003` |
| **Título** | Resolve mapa nivel detalle comuna |
| **Función pytest** | `test_resolve_mapa_nivel_detalle_comuna` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Resolve mapa nivel detalle comuna» se comporta según lo definido en Lógica payload reporte mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_MA-004` — To top territorios solo con incidentes

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_MA-004` |
| **Título** | To top territorios solo con incidentes |
| **Función pytest** | `test_to_top_territorios_solo_con_incidentes` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «To top territorios solo con incidentes» se comporta según lo definido en Lógica payload reporte mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_MA-005` — Build mapa territorio con datos simulados

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_MA-005` |
| **Título** | Build mapa territorio con datos simulados |
| **Función pytest** | `test_build_mapa_territorio_mock` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build mapa territorio con datos simulados» se comporta según lo definido en Lógica payload reporte mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Payload o reporte generado correctamente con datos simulados. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 4.3 Reporte predicciones

**Archivo:** `reports/tests/test_reporte_predicciones_api.py` · **Casos:** 3 · **Prioridad del bloque:** Media

#### Caso `REP-REPORTE_PR-001` — Reporte predicciones requiere rol analista

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_PR-001` |
| **Título** | Reporte predicciones requiere rol analista |
| **Función pytest** | `test_reporte_predicciones_requires_analista` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reporte predicciones requiere rol analista» se comporta según lo definido en Reporte predicciones. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Acceso denegado (401/403) sin el rol o token requerido. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_PR-002` — Reporte predicciones rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_PR-002` |
| **Título** | Reporte predicciones rango invalido |
| **Función pytest** | `test_reporte_predicciones_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reporte predicciones rango invalido» se comporta según lo definido en Reporte predicciones. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_PR-003` — Reporte predicciones respuesta exitosa con datos simulados

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_PR-003` |
| **Título** | Reporte predicciones respuesta exitosa con datos simulados |
| **Función pytest** | `test_reporte_predicciones_ok_mock` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reporte predicciones respuesta exitosa con datos simulados» se comporta según lo definido en Reporte predicciones. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 4.4 Reporte tablero

**Archivo:** `reports/tests/test_reporte_tablero_api.py` · **Casos:** 3 · **Prioridad del bloque:** Media

#### Caso `REP-REPORTE_TA-001` — Reporte tablero requiere rol analista

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_TA-001` |
| **Título** | Reporte tablero requiere rol analista |
| **Función pytest** | `test_reporte_tablero_requires_analista` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reporte tablero requiere rol analista» se comporta según lo definido en Reporte tablero. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Acceso denegado (401/403) sin el rol o token requerido. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_TA-002` — Reporte tablero rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_TA-002` |
| **Título** | Reporte tablero rango invalido |
| **Función pytest** | `test_reporte_tablero_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reporte tablero rango invalido» se comporta según lo definido en Reporte tablero. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTE_TA-003` — Reporte tablero respuesta exitosa con datos simulados

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTE_TA-003` |
| **Título** | Reporte tablero respuesta exitosa con datos simulados |
| **Función pytest** | `test_reporte_tablero_ok_mock` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reporte tablero respuesta exitosa con datos simulados» se comporta según lo definido en Reporte tablero. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 4.5 API generación de reportes

**Archivo:** `reports/tests/test_reportes_api.py` · **Casos:** 6 · **Prioridad del bloque:** Media

#### Caso `REP-REPORTES_A-001` — Reportes preview requiere rol analista

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTES_A-001` |
| **Título** | Reportes preview requiere rol analista |
| **Función pytest** | `test_reportes_preview_requires_analista` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reportes preview requiere rol analista» se comporta según lo definido en API generación de reportes. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Acceso denegado (401/403) sin el rol o token requerido. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTES_A-002` — Reportes preview post con filtros

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTES_A-002` |
| **Título** | Reportes preview post con filtros |
| **Función pytest** | `test_reportes_preview_post_con_filtros` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reportes preview post con filtros» se comporta según lo definido en API generación de reportes. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTES_A-003` — Reportes preview filtros json invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTES_A-003` |
| **Título** | Reportes preview filtros json invalido |
| **Función pytest** | `test_reportes_preview_filtros_json_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reportes preview filtros json invalido» se comporta según lo definido en API generación de reportes. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTES_A-004` — Reportes preview seccion invalida

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTES_A-004` |
| **Título** | Reportes preview seccion invalida |
| **Función pytest** | `test_reportes_preview_seccion_invalida` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reportes preview seccion invalida» se comporta según lo definido en API generación de reportes. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTES_A-005` — Reportes preview titulo predeterminado

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTES_A-005` |
| **Título** | Reportes preview titulo predeterminado |
| **Función pytest** | `test_reportes_preview_titulo_predeterminado` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reportes preview titulo predeterminado» se comporta según lo definido en API generación de reportes. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `REP-REPORTES_A-006` — Reportes preview get filtros json

| Campo | Descripción |
|-------|-------------|
| **ID** | `REP-REPORTES_A-006` |
| **Título** | Reportes preview get filtros json |
| **Función pytest** | `test_reportes_preview_get_filtros_json` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Reportes preview get filtros json» se comporta según lo definido en API generación de reportes. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso). |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

## 5. Módulo 4 — Dashboard, mapa y predicciones

### 5.1 Carga esperada modo espacial

**Archivo:** `dashboard/tests/test_carga_esperada_espacial.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-CARGA_ESPE-001` — Series territorial top

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-CARGA_ESPE-001` |
| **Título** | Series territorial top |
| **Función pytest** | `test_series_territorial_top` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Series territorial top» se comporta según lo definido en Carga esperada modo espacial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-CARGA_ESPE-002` — API carga espacial respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-CARGA_ESPE-002` |
| **Título** | API carga espacial respuesta exitosa |
| **Función pytest** | `test_api_carga_espacial_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API carga espacial respuesta exitosa» se comporta según lo definido en Carga esperada modo espacial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.2 Carga proyectada territorial

**Archivo:** `dashboard/tests/test_carga_esperada_territorial.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-CARGA_ESPE-001` — Carga terciles

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-CARGA_ESPE-001` |
| **Título** | Carga terciles |
| **Función pytest** | `test_carga_terciles` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Carga terciles» se comporta según lo definido en Carga proyectada territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-CARGA_ESPE-002` — API carga esperada respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-CARGA_ESPE-002` |
| **Título** | API carga esperada respuesta exitosa |
| **Función pytest** | `test_api_carga_esperada_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API carga esperada respuesta exitosa» se comporta según lo definido en Carga proyectada territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.3 Coroplética territorial

**Archivo:** `dashboard/tests/test_choropleth_territorial.py` · **Casos:** 3 · **Prioridad del bloque:** Media

#### Caso `DAS-CHOROPLETH-001` — Build payload empty

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-CHOROPLETH-001` |
| **Título** | Build payload empty |
| **Función pytest** | `test_build_payload_empty` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build payload empty» se comporta según lo definido en Coroplética territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-CHOROPLETH-002` — API choropleth respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-CHOROPLETH-002` |
| **Título** | API choropleth respuesta exitosa |
| **Función pytest** | `test_api_choropleth_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API choropleth respuesta exitosa» se comporta según lo definido en Coroplética territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-CHOROPLETH-003` — Ratio baseline ignores territorial filters

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-CHOROPLETH-003` |
| **Título** | Ratio baseline ignores territorial filters |
| **Función pytest** | `test_ratio_baseline_ignores_territorial_filters` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Ratio baseline ignores territorial filters» se comporta según lo definido en Coroplética territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.4 GeoJSON / TopoJSON comunas

**Archivo:** `dashboard/tests/test_comunas_geojson.py` · **Casos:** 2 · **Prioridad del bloque:** Baja

#### Caso `DAS-COMUNAS_GE-001` — Build comunas geojson empty

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-COMUNAS_GE-001` |
| **Título** | Build comunas geojson empty |
| **Función pytest** | `test_build_comunas_geojson_empty` |
| **Prioridad** | Baja |
| **Objetivo** | Comprobar que el escenario «Build comunas geojson empty» se comporta según lo definido en GeoJSON / TopoJSON comunas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-COMUNAS_GE-002` — API comunas geojson respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-COMUNAS_GE-002` |
| **Título** | API comunas geojson respuesta exitosa |
| **Función pytest** | `test_api_comunas_geojson_ok` |
| **Prioridad** | Baja |
| **Objetivo** | Comprobar que el escenario «API comunas geojson respuesta exitosa» se comporta según lo definido en GeoJSON / TopoJSON comunas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.5 Participación por día de semana

**Archivo:** `dashboard/tests/test_dia_semana_api.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-DIA_SEMANA-001` — Dashboard dia semana respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-DIA_SEMANA-001` |
| **Título** | Dashboard dia semana respuesta exitosa |
| **Función pytest** | `test_dashboard_dia_semana_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard dia semana respuesta exitosa» se comporta según lo definido en Participación por día de semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-DIA_SEMANA-002` — Dashboard dia semana rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-DIA_SEMANA-002` |
| **Título** | Dashboard dia semana rango invalido |
| **Función pytest** | `test_dashboard_dia_semana_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard dia semana rango invalido» se comporta según lo definido en Participación por día de semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.6 Distribución por clase

**Archivo:** `dashboard/tests/test_distribucion_clase_incidente_api.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-DISTRIBUCI-001` — Dashboard distribucion clase incidente respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-DISTRIBUCI-001` |
| **Título** | Dashboard distribucion clase incidente respuesta exitosa |
| **Función pytest** | `test_dashboard_distribucion_clase_incidente_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard distribucion clase incidente respuesta exitosa» se comporta según lo definido en Distribución por clase. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-DISTRIBUCI-002` — Dashboard distribucion clase incidente rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-DISTRIBUCI-002` |
| **Título** | Dashboard distribucion clase incidente rango invalido |
| **Función pytest** | `test_dashboard_distribucion_clase_incidente_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard distribucion clase incidente rango invalido» se comporta según lo definido en Distribución por clase. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.7 Distribución por gravedad

**Archivo:** `dashboard/tests/test_distribucion_gravedad_api.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-DISTRIBUCI-001` — Dashboard distribucion gravedad respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-DISTRIBUCI-001` |
| **Título** | Dashboard distribucion gravedad respuesta exitosa |
| **Función pytest** | `test_dashboard_distribucion_gravedad_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard distribucion gravedad respuesta exitosa» se comporta según lo definido en Distribución por gravedad. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-DISTRIBUCI-002` — Dashboard distribucion gravedad rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-DISTRIBUCI-002` |
| **Título** | Dashboard distribucion gravedad rango invalido |
| **Función pytest** | `test_dashboard_distribucion_gravedad_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard distribucion gravedad rango invalido» se comporta según lo definido en Distribución por gravedad. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.8 Lógica distribución gravedad

**Archivo:** `dashboard/tests/test_distribucion_gravedad_logica.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-DISTRIBUCI-001` — Serie omite categorias sin victimas

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-DISTRIBUCI-001` |
| **Título** | Serie omite categorias sin victimas |
| **Función pytest** | `test_serie_omite_categorias_sin_victimas` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Serie omite categorias sin victimas» se comporta según lo definido en Lógica distribución gravedad. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-DISTRIBUCI-002` — Serie no duplica otro vacio

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-DISTRIBUCI-002` |
| **Título** | Serie no duplica otro vacio |
| **Función pytest** | `test_serie_no_duplica_otro_vacio` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Serie no duplica otro vacio» se comporta según lo definido en Lógica distribución gravedad. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.9 Métricas OLS / Poisson / MAPE

**Archivo:** `dashboard/tests/test_estadistica_series.py` · **Casos:** 3 · **Prioridad del bloque:** Media

#### Caso `DAS-ESTADISTIC-001` — Ols linea perfecta

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-ESTADISTIC-001` |
| **Título** | Ols linea perfecta |
| **Función pytest** | `test_ols_linea_perfecta` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Ols linea perfecta» se comporta según lo definido en Métricas OLS / Poisson / MAPE. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-ESTADISTIC-002` — Sample std

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-ESTADISTIC-002` |
| **Título** | Sample std |
| **Función pytest** | `test_sample_std` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Sample std» se comporta según lo definido en Métricas OLS / Poisson / MAPE. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-ESTADISTIC-003` — Design ols rank

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-ESTADISTIC-003` |
| **Título** | Design ols rank |
| **Función pytest** | `test_design_ols_rank` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Design ols rank» se comporta según lo definido en Métricas OLS / Poisson / MAPE. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.10 Evolución mensual

**Archivo:** `dashboard/tests/test_evolucion_mensual_api.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-EVOLUCION_-001` — Dashboard evolucion mensual respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-EVOLUCION_-001` |
| **Título** | Dashboard evolucion mensual respuesta exitosa |
| **Función pytest** | `test_dashboard_evolucion_mensual_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard evolucion mensual respuesta exitosa» se comporta según lo definido en Evolución mensual. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-EVOLUCION_-002` — Dashboard evolucion rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-EVOLUCION_-002` |
| **Título** | Dashboard evolucion rango invalido |
| **Función pytest** | `test_dashboard_evolucion_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard evolucion rango invalido» se comporta según lo definido en Evolución mensual. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.11 Indicadores geoespaciales F5

**Archivo:** `dashboard/tests/test_f5_geoespacial.py` · **Casos:** 3 · **Prioridad del bloque:** Media

#### Caso `DAS-F5_GEOESPA-001` — Build densidad con datos simulados

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-F5_GEOESPA-001` |
| **Título** | Build densidad con datos simulados |
| **Función pytest** | `test_build_densidad_mock` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build densidad con datos simulados» se comporta según lo definido en Indicadores geoespaciales F5. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Payload o reporte generado correctamente con datos simulados. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-F5_GEOESPA-002` — Ranking con datos simulados

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-F5_GEOESPA-002` |
| **Título** | Ranking con datos simulados |
| **Función pytest** | `test_ranking_mock` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Ranking con datos simulados» se comporta según lo definido en Indicadores geoespaciales F5. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Payload o reporte generado correctamente con datos simulados. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-F5_GEOESPA-003` — API densidad respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-F5_GEOESPA-003` |
| **Título** | API densidad respuesta exitosa |
| **Función pytest** | `test_api_densidad_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API densidad respuesta exitosa» se comporta según lo definido en Indicadores geoespaciales F5. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.12 Hotspots y cuadrícula P14

**Archivo:** `dashboard/tests/test_hotspots.py` · **Casos:** 8 · **Prioridad del bloque:** Media

#### Caso `DAS-HOTSPOTS-001` — Parse metodo

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-HOTSPOTS-001` |
| **Título** | Parse metodo |
| **Función pytest** | `test_parse_metodo` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Parse metodo» se comporta según lo definido en Hotspots y cuadrícula P14. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-HOTSPOTS-002` — Clamp tamano celda

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-HOTSPOTS-002` |
| **Título** | Clamp tamano celda |
| **Función pytest** | `test_clamp_tamano_celda` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Clamp tamano celda» se comporta según lo definido en Hotspots y cuadrícula P14. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-HOTSPOTS-003` — Build cuadricula empty

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-HOTSPOTS-003` |
| **Título** | Build cuadricula empty |
| **Función pytest** | `test_build_cuadricula_empty` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build cuadricula empty» se comporta según lo definido en Hotspots y cuadrícula P14. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-HOTSPOTS-004` — Build area sin geojson

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-HOTSPOTS-004` |
| **Título** | Build area sin geojson |
| **Función pytest** | `test_build_area_sin_geojson` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build area sin geojson» se comporta según lo definido en Hotspots y cuadrícula P14. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-HOTSPOTS-005` — Build area malla excedida

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-HOTSPOTS-005` |
| **Título** | Build area malla excedida |
| **Función pytest** | `test_build_area_malla_excedida` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build area malla excedida» se comporta según lo definido en Hotspots y cuadrícula P14. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-HOTSPOTS-006` — Build cuadricula with cell

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-HOTSPOTS-006` |
| **Título** | Build cuadricula with cell |
| **Función pytest** | `test_build_cuadricula_with_cell` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build cuadricula with cell» se comporta según lo definido en Hotspots y cuadrícula P14. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-HOTSPOTS-007` — API hotspots respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-HOTSPOTS-007` |
| **Título** | API hotspots respuesta exitosa |
| **Función pytest** | `test_api_hotspots_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API hotspots respuesta exitosa» se comporta según lo definido en Hotspots y cuadrícula P14. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-HOTSPOTS-008` — API hotspots con parámetros inválidos date

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-HOTSPOTS-008` |
| **Título** | API hotspots con parámetros inválidos date |
| **Función pytest** | `test_api_hotspots_invalid_date` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API hotspots con parámetros inválidos date» se comporta según lo definido en Hotspots y cuadrícula P14. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.13 Puntos y capas del mapa

**Archivo:** `dashboard/tests/test_incidentes_mapa_api.py` · **Casos:** 3 · **Prioridad del bloque:** Media

#### Caso `DAS-INCIDENTES-001` — Dashboard incidentes mapa respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-INCIDENTES-001` |
| **Título** | Dashboard incidentes mapa respuesta exitosa |
| **Función pytest** | `test_dashboard_incidentes_mapa_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard incidentes mapa respuesta exitosa» se comporta según lo definido en Puntos y capas del mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-INCIDENTES-002` — Dashboard incidentes mapa limite cero pasa a build

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-INCIDENTES-002` |
| **Título** | Dashboard incidentes mapa limite cero pasa a build |
| **Función pytest** | `test_dashboard_incidentes_mapa_limite_cero_pasa_a_build` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard incidentes mapa limite cero pasa a build» se comporta según lo definido en Puntos y capas del mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-INCIDENTES-003` — Dashboard incidentes mapa rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-INCIDENTES-003` |
| **Título** | Dashboard incidentes mapa rango invalido |
| **Función pytest** | `test_dashboard_incidentes_mapa_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard incidentes mapa rango invalido» se comporta según lo definido en Puntos y capas del mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.14 KPIs comparativos

**Archivo:** `dashboard/tests/test_kpis_api.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-KPIS_API-001` — Dashboard kpis respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-KPIS_API-001` |
| **Título** | Dashboard kpis respuesta exitosa |
| **Función pytest** | `test_dashboard_kpis_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard kpis respuesta exitosa» se comporta según lo definido en KPIs comparativos. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-KPIS_API-002` — Dashboard kpis rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-KPIS_API-002` |
| **Título** | Dashboard kpis rango invalido |
| **Función pytest** | `test_dashboard_kpis_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard kpis rango invalido» se comporta según lo definido en KPIs comparativos. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.15 Optimizaciones mapa

**Archivo:** `dashboard/tests/test_map_optimizations.py` · **Casos:** 5 · **Prioridad del bloque:** Baja

#### Caso `DAS-MAP_OPTIMI-001` — Topojson from simple polygon

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MAP_OPTIMI-001` |
| **Título** | Topojson from simple polygon |
| **Función pytest** | `test_topojson_from_simple_polygon` |
| **Prioridad** | Baja |
| **Objetivo** | Comprobar que el escenario «Topojson from simple polygon» se comporta según lo definido en Optimizaciones mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MAP_OPTIMI-002` — Wrap choropleth keeps geojson

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MAP_OPTIMI-002` |
| **Título** | Wrap choropleth keeps geojson |
| **Función pytest** | `test_wrap_choropleth_keeps_geojson` |
| **Prioridad** | Baja |
| **Objetivo** | Comprobar que el escenario «Wrap choropleth keeps geojson» se comporta según lo definido en Optimizaciones mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MAP_OPTIMI-003` — Dashboard mapa detalle respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MAP_OPTIMI-003` |
| **Título** | Dashboard mapa detalle respuesta exitosa |
| **Función pytest** | `test_dashboard_mapa_detalle_ok` |
| **Prioridad** | Baja |
| **Objetivo** | Comprobar que el escenario «Dashboard mapa detalle respuesta exitosa» se comporta según lo definido en Optimizaciones mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MAP_OPTIMI-004` — Incidentes mapa formato compacto

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MAP_OPTIMI-004` |
| **Título** | Incidentes mapa formato compacto |
| **Función pytest** | `test_incidentes_mapa_formato_compacto` |
| **Prioridad** | Baja |
| **Objetivo** | Comprobar que el escenario «Incidentes mapa formato compacto» se comporta según lo definido en Optimizaciones mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MAP_OPTIMI-005` — Map cache hit

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MAP_OPTIMI-005` |
| **Título** | Map cache hit |
| **Función pytest** | `test_map_cache_hit` |
| **Prioridad** | Baja |
| **Objetivo** | Comprobar que el escenario «Map cache hit» se comporta según lo definido en Optimizaciones mapa. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.16 Matriz día × hora

**Archivo:** `dashboard/tests/test_matriz_dia_hora_api.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-MATRIZ_DIA-001` — Dashboard matriz dia hora respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MATRIZ_DIA-001` |
| **Título** | Dashboard matriz dia hora respuesta exitosa |
| **Función pytest** | `test_dashboard_matriz_dia_hora_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard matriz dia hora respuesta exitosa» se comporta según lo definido en Matriz día × hora. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MATRIZ_DIA-002` — Dashboard matriz dia hora rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MATRIZ_DIA-002` |
| **Título** | Dashboard matriz dia hora rango invalido |
| **Función pytest** | `test_dashboard_matriz_dia_hora_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard matriz dia hora rango invalido» se comporta según lo definido en Matriz día × hora. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.17 Modelos ARIMA / SARIMA

**Archivo:** `dashboard/tests/test_modelos_arima.py` · **Casos:** 9 · **Prioridad del bloque:** Media

#### Caso `DAS-MODELOS_AR-001` — Arima requiere minimo meses

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MODELOS_AR-001` |
| **Título** | Arima requiere minimo meses |
| **Función pytest** | `test_arima_requiere_minimo_meses` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Arima requiere minimo meses» se comporta según lo definido en Modelos ARIMA / SARIMA. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MODELOS_AR-002` — Sarima requiere 24 meses

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MODELOS_AR-002` |
| **Título** | Sarima requiere 24 meses |
| **Función pytest** | `test_sarima_requiere_24_meses` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Sarima requiere 24 meses» se comporta según lo definido en Modelos ARIMA / SARIMA. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MODELOS_AR-003` — Arima ajusta y proyecta

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MODELOS_AR-003` |
| **Título** | Arima ajusta y proyecta |
| **Función pytest** | `test_arima_ajusta_y_proyecta` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Arima ajusta y proyecta» se comporta según lo definido en Modelos ARIMA / SARIMA. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MODELOS_AR-004` — Build payload arima con datos simulados serie

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MODELOS_AR-004` |
| **Título** | Build payload arima con datos simulados serie |
| **Función pytest** | `test_build_payload_arima_mock_serie` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build payload arima con datos simulados serie» se comporta según lo definido en Modelos ARIMA / SARIMA. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Payload o reporte generado correctamente con datos simulados. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MODELOS_AR-005` — Build payload sarima serie larga

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MODELOS_AR-005` |
| **Título** | Build payload sarima serie larga |
| **Función pytest** | `test_build_payload_sarima_serie_larga` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build payload sarima serie larga» se comporta según lo definido en Modelos ARIMA / SARIMA. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MODELOS_AR-006` — Parse arima order acepta parentesis

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MODELOS_AR-006` |
| **Título** | Parse arima order acepta parentesis |
| **Función pytest** | `test_parse_arima_order_acepta_parentesis` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Parse arima order acepta parentesis» se comporta según lo definido en Modelos ARIMA / SARIMA. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MODELOS_AR-007` — Parse sarima seasonal requiere periodo 12

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MODELOS_AR-007` |
| **Título** | Parse sarima seasonal requiere periodo 12 |
| **Función pytest** | `test_parse_sarima_seasonal_requiere_periodo_12` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Parse sarima seasonal requiere periodo 12» se comporta según lo definido en Modelos ARIMA / SARIMA. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MODELOS_AR-008` — Arima orden personalizado

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MODELOS_AR-008` |
| **Título** | Arima orden personalizado |
| **Función pytest** | `test_arima_orden_personalizado` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Arima orden personalizado» se comporta según lo definido en Modelos ARIMA / SARIMA. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-MODELOS_AR-009` — Build payload arima con orden query

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-MODELOS_AR-009` |
| **Título** | Build payload arima con orden query |
| **Función pytest** | `test_build_payload_arima_con_orden_query` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Build payload arima con orden query» se comporta según lo definido en Modelos ARIMA / SARIMA. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.18 Patrones día×hora y día semana

**Archivo:** `dashboard/tests/test_patrones_temporales_proyectados.py` · **Casos:** 8 · **Prioridad del bloque:** Media

#### Caso `DAS-PATRONES_T-001` — Distribuir enteros suma objetivo

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PATRONES_T-001` |
| **Título** | Distribuir enteros suma objetivo |
| **Función pytest** | `test_distribuir_enteros_suma_objetivo` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Distribuir enteros suma objetivo» se comporta según lo definido en Patrones día×hora y día semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PATRONES_T-002` — Matriz proyectada reparte total

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PATRONES_T-002` |
| **Título** | Matriz proyectada reparte total |
| **Función pytest** | `test_matriz_proyectada_reparte_total` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Matriz proyectada reparte total» se comporta según lo definido en Patrones día×hora y día semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PATRONES_T-003` — Δ celda = proyección − periodo; ΣΔ = total proy − total periodo.

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PATRONES_T-003` |
| **Título** | Δ celda = proyección − periodo; ΣΔ = total proy − total periodo. |
| **Función pytest** | `test_matriz_delta_coherente_por_celda` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Δ celda = proyección − periodo; ΣΔ = total proy − total periodo.» se comporta según lo definido en Patrones día×hora y día semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Δ celda = proyección − periodo; ΣΔ = total proy − total periodo. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PATRONES_T-004` — Matriz proyectada modelo media movil

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PATRONES_T-004` |
| **Título** | Matriz proyectada modelo media movil |
| **Función pytest** | `test_matriz_proyectada_modelo_media_movil` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Matriz proyectada modelo media movil» se comporta según lo definido en Patrones día×hora y día semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PATRONES_T-005` — Matriz proyectada sin modelo

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PATRONES_T-005` |
| **Título** | Matriz proyectada sin modelo |
| **Función pytest** | `test_matriz_proyectada_sin_modelo` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Matriz proyectada sin modelo» se comporta según lo definido en Patrones día×hora y día semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PATRONES_T-006` — Dia semana proyectado siete dias

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PATRONES_T-006` |
| **Título** | Dia semana proyectado siete dias |
| **Función pytest** | `test_dia_semana_proyectado_siete_dias` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dia semana proyectado siete dias» se comporta según lo definido en Patrones día×hora y día semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PATRONES_T-007` — API matriz dia hora proyectada respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PATRONES_T-007` |
| **Título** | API matriz dia hora proyectada respuesta exitosa |
| **Función pytest** | `test_api_matriz_dia_hora_proyectada_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API matriz dia hora proyectada respuesta exitosa» se comporta según lo definido en Patrones día×hora y día semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PATRONES_T-008` — API dia semana proyectado rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PATRONES_T-008` |
| **Título** | API dia semana proyectado rango invalido |
| **Función pytest** | `test_api_dia_semana_proyectado_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API dia semana proyectado rango invalido» se comporta según lo definido en Patrones día×hora y día semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.19 Lógica día de semana

**Archivo:** `dashboard/tests/test_por_dia_semana_logica.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-POR_DIA_SE-001` — Participacion incidentes suma 100

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-POR_DIA_SE-001` |
| **Título** | Participacion incidentes suma 100 |
| **Función pytest** | `test_participacion_incidentes_suma_100` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Participacion incidentes suma 100» se comporta según lo definido en Lógica día de semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-POR_DIA_SE-002` — Dia pico concentracion alta

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-POR_DIA_SE-002` |
| **Título** | Dia pico concentracion alta |
| **Función pytest** | `test_dia_pico_concentracion_alta` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dia pico concentracion alta» se comporta según lo definido en Lógica día de semana. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.20 API proyección mensual

**Archivo:** `dashboard/tests/test_predicciones_mensuales_api.py` · **Casos:** 5 · **Prioridad del bloque:** Alta

#### Caso `DAS-PREDICCION-001` — Dashboard predicciones mensuales respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-001` |
| **Título** | Dashboard predicciones mensuales respuesta exitosa |
| **Función pytest** | `test_dashboard_predicciones_mensuales_ok` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Dashboard predicciones mensuales respuesta exitosa» se comporta según lo definido en API proyección mensual. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-002` — Dashboard predicciones rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-002` |
| **Título** | Dashboard predicciones rango invalido |
| **Función pytest** | `test_dashboard_predicciones_rango_invalido` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Dashboard predicciones rango invalido» se comporta según lo definido en API proyección mensual. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-003` — Dashboard predicciones parametros fase a

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-003` |
| **Título** | Dashboard predicciones parametros fase a |
| **Función pytest** | `test_dashboard_predicciones_parametros_fase_a` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Dashboard predicciones parametros fase a» se comporta según lo definido en API proyección mensual. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-004` — Dashboard predicciones desglose con clase conflict

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-004` |
| **Título** | Dashboard predicciones desglose con clase conflict |
| **Función pytest** | `test_dashboard_predicciones_desglose_con_clase_conflict` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Dashboard predicciones desglose con clase conflict» se comporta según lo definido en API proyección mensual. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-005` — Dashboard predicciones modelo invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-005` |
| **Título** | Dashboard predicciones modelo invalido |
| **Función pytest** | `test_dashboard_predicciones_modelo_invalido` |
| **Prioridad** | Alta |
| **Objetivo** | Comprobar que el escenario «Dashboard predicciones modelo invalido» se comporta según lo definido en API proyección mensual. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.21 Lógica proyección y μ±3σ

**Archivo:** `dashboard/tests/test_predicciones_mensuales_logica.py` · **Casos:** 16 · **Prioridad del bloque:** Media

#### Caso `DAS-PREDICCION-001` — Un solo mes sin modelo

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-001` |
| **Título** | Un solo mes sin modelo |
| **Función pytest** | `test_un_solo_mes_sin_modelo` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Un solo mes sin modelo» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-002` — Recta conocida y proyeccion

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-002` |
| **Título** | Recta conocida y proyeccion |
| **Función pytest** | `test_recta_conocida_y_proyeccion` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Recta conocida y proyeccion» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-003` — Proyeccion recortada a cero

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-003` |
| **Título** | Proyeccion recortada a cero |
| **Función pytest** | `test_proyeccion_recortada_a_cero` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Proyeccion recortada a cero» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-004` — Estacional tres meses

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-004` |
| **Título** | Estacional tres meses |
| **Función pytest** | `test_estacional_tres_meses` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Estacional tres meses» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-005` — Victimas variable

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-005` |
| **Título** | Victimas variable |
| **Función pytest** | `test_victimas_variable` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Victimas variable» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-006` — Poisson dos meses minimo

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-006` |
| **Título** | Poisson dos meses minimo |
| **Función pytest** | `test_poisson_dos_meses_minimo` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Poisson dos meses minimo» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-007` — Poisson no explota con serie larga

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-007` |
| **Título** | Poisson no explota con serie larga |
| **Función pytest** | `test_poisson_no_explota_con_serie_larga` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Poisson no explota con serie larga» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-008` — Excluir covid deja hueco sin ajuste

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-008` |
| **Título** | Excluir covid deja hueco sin ajuste |
| **Función pytest** | `test_excluir_covid_deja_hueco_sin_ajuste` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Excluir covid deja hueco sin ajuste» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-009` — Media movil tres meses

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-009` |
| **Título** | Media movil tres meses |
| **Función pytest** | `test_media_movil_tres_meses` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Media movil tres meses» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-010` — Media movil insuficiente meses

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-010` |
| **Título** | Media movil insuficiente meses |
| **Función pytest** | `test_media_movil_insuficiente_meses` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Media movil insuficiente meses» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-011` — Desglose clase

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-011` |
| **Título** | Desglose clase |
| **Función pytest** | `test_desglose_clase` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Desglose clase» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-012` — Holdout ols linea perfecta

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-012` |
| **Título** | Holdout ols linea perfecta |
| **Función pytest** | `test_holdout_ols_linea_perfecta` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Holdout ols linea perfecta» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-013` — Holdout insuficiente meses

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-013` |
| **Título** | Holdout insuficiente meses |
| **Función pytest** | `test_holdout_insuficiente_meses` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Holdout insuficiente meses» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-014` — Holdout desactivado

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-014` |
| **Título** | Holdout desactivado |
| **Función pytest** | `test_holdout_desactivado` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Holdout desactivado» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-015` — Tres sigma media constante y bandas

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-015` |
| **Título** | Tres sigma media constante y bandas |
| **Función pytest** | `test_tres_sigma_media_constante_y_bandas` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Tres sigma media constante y bandas» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PREDICCION-016` — Tres sigma holdout

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PREDICCION-016` |
| **Título** | Tres sigma holdout |
| **Función pytest** | `test_tres_sigma_holdout` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Tres sigma holdout» se comporta según lo definido en Lógica proyección y μ±3σ. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.22 Índice prioridad territorial

**Archivo:** `dashboard/tests/test_prioridad_territorial.py` · **Casos:** 5 · **Prioridad del bloque:** Media

#### Caso `DAS-PRIORIDAD_-001` — Delta promedios territorio

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PRIORIDAD_-001` |
| **Título** | Delta promedios territorio |
| **Función pytest** | `test_delta_promedios_territorio` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Delta promedios territorio» se comporta según lo definido en Índice prioridad territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PRIORIDAD_-002` — Indice compuesto orden

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PRIORIDAD_-002` |
| **Título** | Indice compuesto orden |
| **Función pytest** | `test_indice_compuesto_orden` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Indice compuesto orden» se comporta según lo definido en Índice prioridad territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PRIORIDAD_-003` — Min incidentes por nivel

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PRIORIDAD_-003` |
| **Título** | Min incidentes por nivel |
| **Función pytest** | `test_min_incidentes_por_nivel` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Min incidentes por nivel» se comporta según lo definido en Índice prioridad territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PRIORIDAD_-004` — Alerta cuando lider no es frecuencia

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PRIORIDAD_-004` |
| **Título** | Alerta cuando lider no es frecuencia |
| **Función pytest** | `test_alerta_cuando_lider_no_es_frecuencia` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Alerta cuando lider no es frecuencia» se comporta según lo definido en Índice prioridad territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PRIORIDAD_-005` — API prioridad territorial respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PRIORIDAD_-005` |
| **Título** | API prioridad territorial respuesta exitosa |
| **Función pytest** | `test_api_prioridad_territorial_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API prioridad territorial respuesta exitosa» se comporta según lo definido en Índice prioridad territorial. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.23 Proporción víctimas fatales

**Archivo:** `dashboard/tests/test_proporcion_fatales_mensual.py` · **Casos:** 11 · **Prioridad del bloque:** Media

#### Caso `DAS-PROPORCION-001` — Pct fatales umbral

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-001` |
| **Título** | Pct fatales umbral |
| **Función pytest** | `test_pct_fatales_umbral` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Pct fatales umbral» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-002` — Proporcion ols con datos

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-002` |
| **Título** | Proporcion ols con datos |
| **Función pytest** | `test_proporcion_ols_con_datos` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Proporcion ols con datos» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-003` — Proporcion media movil

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-003` |
| **Título** | Proporcion media movil |
| **Función pytest** | `test_proporcion_media_movil` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Proporcion media movil» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-004` — Proyeccion estable no cae a cero

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-004` |
| **Título** | Proyeccion estable no cae a cero |
| **Función pytest** | `test_proyeccion_estable_no_cae_a_cero` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Proyeccion estable no cae a cero» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-005` — Proporcion arima con 12 meses

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-005` |
| **Título** | Proporcion arima con 12 meses |
| **Función pytest** | `test_proporcion_arima_con_12_meses` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Proporcion arima con 12 meses» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-006` — Proporcion sarima requiere 24 meses

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-006` |
| **Título** | Proporcion sarima requiere 24 meses |
| **Función pytest** | `test_proporcion_sarima_requiere_24_meses` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Proporcion sarima requiere 24 meses» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. Paquete `statsmodels` disponible en el entorno virtual. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-007` — % bajos (p. ej. 0,66) no deben colapsar a 0/1 al ajustar.

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-007` |
| **Título** | % bajos (p. ej. 0,66) no deben colapsar a 0/1 al ajustar. |
| **Función pytest** | `test_proporcion_estacional_usa_float_sin_redondeo` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «% bajos (p. ej. 0,66) no deben colapsar a 0/1 al ajustar.» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | % bajos (p. ej. 0,66) no deben colapsar a 0/1 al ajustar. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-008` — Proporcion logit offset

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-008` |
| **Título** | Proporcion logit offset |
| **Función pytest** | `test_proporcion_logit_offset` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Proporcion logit offset» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-009` — Proporcion ratio compuesto

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-009` |
| **Título** | Proporcion ratio compuesto |
| **Función pytest** | `test_proporcion_ratio_compuesto` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Proporcion ratio compuesto» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-010` — Proporcion holdout activo

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-010` |
| **Título** | Proporcion holdout activo |
| **Función pytest** | `test_proporcion_holdout_activo` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Proporcion holdout activo» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-PROPORCION-011` — API proporcion fatales respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-PROPORCION-011` |
| **Título** | API proporcion fatales respuesta exitosa |
| **Función pytest** | `test_api_proporcion_fatales_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «API proporcion fatales respuesta exitosa» se comporta según lo definido en Proporción víctimas fatales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.24 Validación rango de fechas

**Archivo:** `dashboard/tests/test_rango_fechas_api.py` · **Casos:** 1 · **Prioridad del bloque:** Media

#### Caso `DAS-RANGO_FECH-001` — Dashboard rango fechas hay datos

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-RANGO_FECH-001` |
| **Título** | Dashboard rango fechas hay datos |
| **Función pytest** | `test_dashboard_rango_fechas_hay_datos` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard rango fechas hay datos» se comporta según lo definido en Validación rango de fechas. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.25 Regresión filtros territorio

**Archivo:** `dashboard/tests/test_territorio_regression.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-TERRITORIO-001` — Kpis default territorio registro en meta

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-001` |
| **Título** | Kpis default territorio registro en meta |
| **Función pytest** | `test_kpis_default_territorio_registro_en_meta` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Kpis default territorio registro en meta» se comporta según lo definido en Regresión filtros territorio. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-TERRITORIO-002` — Kpis territorio espacial param

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-002` |
| **Título** | Kpis territorio espacial param |
| **Función pytest** | `test_kpis_territorio_espacial_param` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Kpis territorio espacial param» se comporta según lo definido en Regresión filtros territorio. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.26 SQL filtros territoriales

**Archivo:** `dashboard/tests/test_territorio_sql.py` · **Casos:** 8 · **Prioridad del bloque:** Media

#### Caso `DAS-TERRITORIO-001` — Parse modo territorio default

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-001` |
| **Título** | Parse modo territorio default |
| **Función pytest** | `test_parse_modo_territorio_default` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Parse modo territorio default» se comporta según lo definido en SQL filtros territoriales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-TERRITORIO-002` — Parse modo territorio espacial aliases

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-002` |
| **Título** | Parse modo territorio espacial aliases |
| **Función pytest** | `test_parse_modo_territorio_espacial_aliases` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Parse modo territorio espacial aliases» se comporta según lo definido en SQL filtros territoriales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-TERRITORIO-003` — Columnas fk por modo

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-003` |
| **Título** | Columnas fk por modo |
| **Función pytest** | `test_columnas_fk_por_modo` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Columnas fk por modo» se comporta según lo definido en SQL filtros territoriales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-TERRITORIO-004` — Append filtros registro

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-004` |
| **Título** | Append filtros registro |
| **Función pytest** | `test_append_filtros_registro` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Append filtros registro» se comporta según lo definido en SQL filtros territoriales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-TERRITORIO-005` — Append filtros espacial

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-005` |
| **Título** | Append filtros espacial |
| **Función pytest** | `test_append_filtros_espacial` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Append filtros espacial» se comporta según lo definido en SQL filtros territoriales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-TERRITORIO-006` — Parse modo punto critico

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-006` |
| **Título** | Parse modo punto critico |
| **Función pytest** | `test_parse_modo_punto_critico` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Parse modo punto critico» se comporta según lo definido en SQL filtros territoriales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-TERRITORIO-007` — Punto critico serie sql registro

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-007` |
| **Título** | Punto critico serie sql registro |
| **Función pytest** | `test_punto_critico_serie_sql_registro` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Punto critico serie sql registro» se comporta según lo definido en SQL filtros territoriales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-TERRITORIO-008` — Punto critico serie sql proximidad

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TERRITORIO-008` |
| **Título** | Punto critico serie sql proximidad |
| **Función pytest** | `test_punto_critico_serie_sql_proximidad` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Punto critico serie sql proximidad» se comporta según lo definido en SQL filtros territoriales. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. |
| **Criterio de aceptación** | Comportamiento conforme a las aserciones definidas en el caso automatizado. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

### 5.27 Rankings territoriales y actores

**Archivo:** `dashboard/tests/test_tops_api.py` · **Casos:** 2 · **Prioridad del bloque:** Media

#### Caso `DAS-TOPS_API-001` — Dashboard tops respuesta exitosa

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TOPS_API-001` |
| **Título** | Dashboard tops respuesta exitosa |
| **Función pytest** | `test_dashboard_tops_ok` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard tops respuesta exitosa» se comporta según lo definido en Rankings territoriales y actores. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

#### Caso `DAS-TOPS_API-002` — Dashboard tops rango invalido

| Campo | Descripción |
|-------|-------------|
| **ID** | `DAS-TOPS_API-002` |
| **Título** | Dashboard tops rango invalido |
| **Función pytest** | `test_dashboard_tops_rango_invalido` |
| **Prioridad** | Media |
| **Objetivo** | Comprobar que el escenario «Dashboard tops rango invalido» se comporta según lo definido en Rankings territoriales y actores. |
| **Precondiciones** | Entorno pytest con `config.settings_test` (SQLite en memoria). Migraciones Django aplicadas en la BD de prueba. Capa de datos o servicios simulados con `unittest.mock`. |
| **Criterio de aceptación** | Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos. |
| **Resultado** | Ejecución exitosa sin fallos |
| **Estado** | Aprobado |
| **Observaciones** | — |

---

## Anexo A — Regenerar este documento

Si se añaden o modifican tests, ejecute:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts/generar_doc_pruebas.py
```

Luego vuelva a ejecutar `pytest` y actualice manualmente fechas u observaciones si aplica.
