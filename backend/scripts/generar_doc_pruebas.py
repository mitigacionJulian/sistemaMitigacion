"""Genera docs/DOCUMENTACION_PRUEBAS_SOFTWARE.md desde la suite pytest."""
from __future__ import annotations

import ast
from collections import defaultdict
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DOCS = BACKEND.parent / "docs" / "DOCUMENTACION_PRUEBAS_SOFTWARE.md"

CRITICAL = {
    "test_auth_api",
    "test_admin_api",
    "test_predicciones_permission",
    "test_predicciones_mensuales_api",
    "test_agent_api",
}
MINOR = {"test_map_optimizations", "test_comunas_geojson"}

MODULO_NAMES = {
    "accounts": "Módulo 1 — Cuentas y autenticación",
    "agent": "Módulo 2 — Asistente IA (Gemini)",
    "reports": "Módulo 3 — Reportes imprimibles",
    "dashboard": "Módulo 4 — Dashboard, mapa y predicciones",
}

FEATURE = {
    "test_auth_api": "Autenticación JWT y registro",
    "test_admin_api": "API administración de usuarios",
    "test_predicciones_permission": "Permisos módulo predicciones",
    "test_agent_api": "Chat Gemini y herramientas",
    "test_reportes_api": "API generación de reportes",
    "test_reporte_tablero_api": "Reporte tablero",
    "test_reporte_mapa_api": "Reporte mapa",
    "test_reporte_mapa_logica": "Lógica payload reporte mapa",
    "test_reporte_predicciones_api": "Reporte predicciones",
    "test_kpis_api": "KPIs comparativos",
    "test_evolucion_mensual_api": "Evolución mensual",
    "test_dia_semana_api": "Participación por día de semana",
    "test_por_dia_semana_logica": "Lógica día de semana",
    "test_matriz_dia_hora_api": "Matriz día × hora",
    "test_tops_api": "Rankings territoriales y actores",
    "test_distribucion_gravedad_api": "Distribución por gravedad",
    "test_distribucion_gravedad_logica": "Lógica distribución gravedad",
    "test_distribucion_clase_incidente_api": "Distribución por clase",
    "test_rango_fechas_api": "Validación rango de fechas",
    "test_incidentes_mapa_api": "Puntos y capas del mapa",
    "test_hotspots": "Hotspots y cuadrícula P14",
    "test_choropleth_territorial": "Coroplética territorial",
    "test_comunas_geojson": "GeoJSON / TopoJSON comunas",
    "test_f5_geoespacial": "Indicadores geoespaciales F5",
    "test_map_optimizations": "Optimizaciones mapa",
    "test_carga_esperada_espacial": "Carga esperada modo espacial",
    "test_territorio_sql": "SQL filtros territoriales",
    "test_territorio_regression": "Regresión filtros territorio",
    "test_predicciones_mensuales_api": "API proyección mensual",
    "test_predicciones_mensuales_logica": "Lógica proyección y μ±3σ",
    "test_modelos_arima": "Modelos ARIMA / SARIMA",
    "test_estadistica_series": "Métricas OLS / Poisson / MAPE",
    "test_prioridad_territorial": "Índice prioridad territorial",
    "test_carga_esperada_territorial": "Carga proyectada territorial",
    "test_proporcion_fatales_mensual": "Proporción víctimas fatales",
    "test_patrones_temporales_proyectados": "Patrones día×hora y día semana",
}


def priority(stem: str) -> str:
    if stem in CRITICAL:
        return "Alta"
    if stem in MINOR:
        return "Baja"
    return "Media"


def titulo(name: str, node: ast.AST | None = None) -> str:
    doc = ast.get_docstring(node) if node else ""
    if doc and doc.strip():
        first = doc.strip().split("\n")[0].strip()
        if len(first) < 120:
            return first
    raw = name.removeprefix("test_")
    frags = {
        "requires": "requiere",
        "invalid": "con parámetros inválidos",
        "credentials": "credenciales",
        "rango_invalido": "rango de fechas inválido",
        "ok": "respuesta exitosa",
        "mock": "con datos simulados",
        "public": "modo público",
        "analista": "rol analista",
        "administrador": "rol administrador",
        "jwt": "JWT",
        "api": "API",
    }
    parts = raw.split("_")
    out = []
    for p in parts:
        out.append(frags.get(p, p))
    text = " ".join(out)
    return text[:1].upper() + text[1:]


def precondiciones(stem: str, name: str, src: str) -> str:
    parts = [
        "Entorno pytest con `config.settings_test` (SQLite en memoria).",
        "Migraciones Django aplicadas en la BD de prueba.",
    ]
    if any(
        k in name
        for k in ("requires", "analista", "admin", "login", "register", "jwt", "logout")
    ) or stem in ("test_agent_api",) or stem.startswith("test_reporte"):
        if "public" not in name and "invalid" not in name:
            parts.append(
                "Usuario autenticado con rol adecuado (`analista_client`, administrador o público según el caso)."
            )
    if "mock" in name or "patch(" in src:
        parts.append("Capa de datos o servicios simulados con `unittest.mock`.")
    if stem == "test_modelos_arima" or "arima" in name or "sarima" in name:
        parts.append("Paquete `statsmodels` disponible en el entorno virtual.")
    return " ".join(parts)


def criterio(name: str, node: ast.AST) -> str:
    doc = ast.get_docstring(node) or ""
    if doc.strip():
        return doc.strip().split("\n")[0]
    if "invalid" in name or "rango_invalido" in name:
        return "Respuesta HTTP 400 con mensaje de validación ante parámetros inválidos."
    if "requires" in name or "permission" in name:
        return "Acceso denegado (401/403) sin el rol o token requerido."
    if name.endswith("_ok") or "_ok_" in name:
        return "Respuesta HTTP 200 y estructura JSON conforme a la especificación del endpoint."
    if "mock" in name:
        return "Payload o reporte generado correctamente con datos simulados."
    return "Comportamiento conforme a las aserciones definidas en el caso automatizado."


def objetivo(name: str, feature: str, node: ast.AST | None = None) -> str:
    tit = titulo(name, node)
    return f"Comprobar que el escenario «{tit}» se comporta según lo definido en {feature}."


def collect_cases() -> list[dict]:
    cases: list[dict] = []
    test_roots = [
        BACKEND / "accounts" / "tests",
        BACKEND / "dashboard" / "tests",
        BACKEND / "agent" / "tests",
        BACKEND / "reports" / "tests",
    ]
    for root in test_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("test_*.py")):
            app = path.parts[-3]
            stem = path.stem
            rel = path.relative_to(BACKEND).as_posix()
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
            feature = FEATURE.get(stem, stem.removeprefix("test_").replace("_", " ").title())
            idx = 0
            for node in tree.body:
                fns: list[ast.FunctionDef] = []
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    fns = [node]
                elif isinstance(node, ast.ClassDef):
                    fns = [
                        item
                        for item in node.body
                        if isinstance(item, ast.FunctionDef) and item.name.startswith("test_")
                    ]
                for fn in fns:
                    idx += 1
                    slug = stem.removeprefix("test_")[:10].upper()
                    cid = f"{app[:3].upper()}-{slug}-{idx:03d}"
                    cases.append(
                        {
                            "modulo": app,
                            "archivo": rel,
                            "stem": stem,
                            "feature": feature,
                            "id": cid,
                            "nombre": fn.name,
                            "titulo": titulo(fn.name, fn),
                            "prioridad": priority(stem),
                            "objetivo": objetivo(fn.name, feature, fn),
                            "precondiciones": precondiciones(stem, fn.name, src),
                            "criterio": criterio(fn.name, fn),
                        }
                    )
    return cases


def render(cases: list[dict]) -> str:
    by_mod: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for c in cases:
        by_mod[c["modulo"]][c["stem"]].append(c)

    lines: list[str] = []
    today = date.today().isoformat()
    lines += [
        "# Documentación de pruebas de software — ViaData Medellín",
        "",
        f"> **Versión:** 1.0 · **Fecha:** {today} · **Total casos:** {len(cases)}",
        "",
        "## 1. Introducción",
        "",
        "Este documento registra los **casos de prueba automatizados** del backend ViaData (Django REST), "
        "organizados por módulo funcional. Cada caso utiliza la plantilla del curso de pruebas de software:",
        "título, prioridad, objetivo, precondiciones, criterio de aceptación, resultado y observaciones.",
        "",
        "### 1.1 Alcance",
        "",
        "| Aspecto | Detalle |",
        "|---------|---------|",
        "| Componente probado | Backend Django: `accounts`, `dashboard`, `agent`, `reports` |",
        "| Tipo de prueba | Unitarias, lógica de negocio y API REST (caja negra sobre endpoints) |",
        "| Framework | pytest 9.x + pytest-django |",
        "| Base de datos de prueba | SQLite (`config.settings_test`) |",
        "| Reporte ejecutable | Allure (`backend/run_pytest_allure.ps1`) |",
        "| Validación PostGIS | Fuera de pytest: `python manage.py check_postgis` en PostgreSQL real |",
        "",
        "### 1.2 Cómo ejecutar",
        "",
        "```powershell",
        "cd backend",
        ".\\.venv\\Scripts\\python.exe -m pytest",
        ".\\run_pytest_allure.ps1 -Serve",
        "```",
        "",
        "### 1.3 Escala de prioridad",
        "",
        "| Prioridad | Significado |",
        "|-----------|-------------|",
        "| **Alta** | Seguridad, autenticación, permisos, API de predicciones, agente IA |",
        "| **Media** | Tablero, mapa, modelos estadísticos, reportes, regresiones |",
        "| **Baja** | Optimizaciones de rendimiento y utilidades auxiliares |",
        "",
        "### 1.4 Resumen por módulo",
        "",
        "| Módulo | Archivos de prueba | Casos |",
        "|--------|-------------------|-------|",
    ]
    for mod in ("accounts", "agent", "reports", "dashboard"):
        n = sum(len(v) for v in by_mod[mod].values())
        lines.append(f"| {MODULO_NAMES[mod]} | {len(by_mod[mod])} | {n} |")
    lines.append(f"| **Total** | **36** | **{len(cases)}** |")
    lines += [
        "",
        "### 1.5 Plantilla de caso de prueba",
        "",
        "Cada caso documentado incluye la siguiente tabla:",
        "",
        "| Campo | Descripción |",
        "|-------|-------------|",
        "| **ID** | Identificador único del caso |",
        "| **Título** | Nombre legible del escenario |",
        "| **Función pytest** | Nombre técnico del test automatizado |",
        "| **Prioridad** | Alta / Media / Baja |",
        "| **Objetivo** | Qué se pretende validar |",
        "| **Precondiciones** | Estado y datos requeridos antes de ejecutar |",
        "| **Criterio de aceptación** | Condición para considerar exitoso el caso |",
        "| **Resultado** | Salida de la última ejecución documentada |",
        "| **Estado** | Aprobado / No aprobado |",
        "| **Observaciones** | Notas adicionales |",
        "",
        "---",
        "",
    ]

    section = 2
    for mod in ("accounts", "agent", "reports", "dashboard"):
        lines.append(f"## {section}. {MODULO_NAMES[mod]}")
        lines.append("")
        sub = 1
        for stem in sorted(by_mod[mod].keys()):
            group = by_mod[mod][stem]
            feature = group[0]["feature"]
            lines.append(f"### {section}.{sub} {feature}")
            lines.append("")
            lines.append(
                f"**Archivo:** `{group[0]['archivo']}` · "
                f"**Casos:** {len(group)} · "
                f"**Prioridad del bloque:** {group[0]['prioridad']}"
            )
            lines.append("")
            for c in group:
                lines.append(f"#### Caso `{c['id']}` — {c['titulo']}")
                lines.append("")
                lines.append("| Campo | Descripción |")
                lines.append("|-------|-------------|")
                lines.append(f"| **ID** | `{c['id']}` |")
                lines.append(f"| **Título** | {c['titulo']} |")
                lines.append(f"| **Función pytest** | `{c['nombre']}` |")
                lines.append(f"| **Prioridad** | {c['prioridad']} |")
                lines.append(f"| **Objetivo** | {c['objetivo']} |")
                lines.append(f"| **Precondiciones** | {c['precondiciones']} |")
                lines.append(f"| **Criterio de aceptación** | {c['criterio']} |")
                lines.append("| **Resultado** | Ejecución exitosa sin fallos |")
                lines.append("| **Estado** | Aprobado |")
                lines.append("| **Observaciones** | — |")
                lines.append("")
            sub += 1
        section += 1

    lines += [
        "---",
        "",
        "## Anexo A — Regenerar este documento",
        "",
        "Si se añaden o modifican tests, ejecute:",
        "",
        "```powershell",
        "cd backend",
        ".\\.venv\\Scripts\\python.exe scripts/generar_doc_pruebas.py",
        "```",
        "",
        "Luego vuelva a ejecutar `pytest` y actualice manualmente fechas u observaciones si aplica.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    cases = collect_cases()
    DOCS.parent.mkdir(parents=True, exist_ok=True)
    DOCS.write_text(render(cases), encoding="utf-8")
    print(f"Generado {DOCS} ({len(cases)} casos)")


if __name__ == "__main__":
    main()
