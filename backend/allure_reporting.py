"""
Etiquetado automático Allure (JSON) para la suite pytest de ViaData.

Los archivos *-result.json en allure-results/ alimentan:
  · Panel administrador /admin/pruebas (UI)
  · Reporte imprimible/PDF (sección pruebas)

No requiere Node.js ni Java. El reporte HTML oficial de Allure (consola) es opcional.

Se invoca desde conftest.py en pytest_runtest_setup (sin decorar cada test a mano).
"""
from __future__ import annotations

import sys
from pathlib import Path

# (feature, categoría funcional, indicador opcional)
_FEATURE_BY_FILE: dict[str, tuple[str, str, str]] = {
    # accounts
    "test_auth_api": ("Autenticación JWT y registro", "Autenticación y roles", "—"),
    "test_admin_api": ("API administración de usuarios", "Autenticación y roles", "—"),
    "test_admin_pruebas_api": ("Panel admin — pruebas del sistema", "Autenticación y roles", "—"),
    "test_predicciones_permission": ("Permisos módulo predicciones", "Autenticación y roles", "—"),
    # agent
    "test_agent_api": ("Chat Gemini y herramientas", "Asistente IA", "—"),
    # reports
    "test_reportes_api": ("API generación de reportes", "Reportes imprimibles", "—"),
    "test_reporte_tablero_api": ("Reporte tablero", "Reportes imprimibles", "Tablero"),
    "test_reporte_mapa_api": ("Reporte mapa", "Reportes imprimibles", "Mapa"),
    "test_reporte_mapa_logica": ("Lógica payload reporte mapa", "Reportes imprimibles", "Mapa"),
    "test_reporte_predicciones_api": ("Reporte predicciones", "Reportes imprimibles", "Predicciones"),
    # dashboard — tablero
    "test_kpis_api": ("KPIs comparativos", "Tablero descriptivo", "KPIs"),
    "test_evolucion_mensual_api": ("Evolución mensual", "Tablero descriptivo", "—"),
    "test_dia_semana_api": ("Participación por día de semana", "Tablero descriptivo", "—"),
    "test_por_dia_semana_logica": ("Lógica día de semana", "Tablero descriptivo", "—"),
    "test_matriz_dia_hora_api": ("Matriz día × hora", "Tablero descriptivo", "—"),
    "test_tops_api": ("Rankings territoriales y actores", "Tablero descriptivo", "—"),
    "test_distribucion_gravedad_api": ("Distribución por gravedad", "Tablero descriptivo", "—"),
    "test_distribucion_gravedad_logica": ("Lógica distribución gravedad", "Tablero descriptivo", "—"),
    "test_distribucion_clase_incidente_api": ("Distribución por clase", "Tablero descriptivo", "—"),
    "test_rango_fechas_api": ("Validación rango de fechas", "Tablero descriptivo", "—"),
    # dashboard — mapa
    "test_incidentes_mapa_api": ("Puntos y capas del mapa", "Mapa y geoespacial", "—"),
    "test_hotspots": ("Hotspots y cuadrícula P14", "Mapa y geoespacial", "P14"),
    "test_choropleth_territorial": ("Coroplética territorial", "Mapa y geoespacial", "G01–G02"),
    "test_comunas_geojson": ("GeoJSON / TopoJSON comunas", "Mapa y geoespacial", "—"),
    "test_f5_geoespacial": ("Filtro geoespacial F5", "Mapa y geoespacial", "F3"),
    "test_map_optimizations": ("Optimizaciones mapa", "Mapa y geoespacial", "—"),
    "test_carga_esperada_espacial": ("Carga esperada modo espacial", "Mapa y geoespacial", "P09–P10"),
    # dashboard — territorio / SQL
    "test_territorio_sql": ("SQL filtros territoriales", "Infraestructura técnica", "F3"),
    "test_territorio_regression": ("Regresión filtros territorio", "Infraestructura técnica", "F3"),
    # dashboard — predicciones
    "test_predicciones_mensuales_api": ("API proyección mensual", "Predicciones — proyección mensual", "P01–P04"),
    "test_predicciones_mensuales_logica": ("Lógica proyección y μ±3σ", "Predicciones — proyección mensual", "P01–P04"),
    "test_modelos_arima": ("Modelos ARIMA / SARIMA", "Predicciones — proyección mensual", "P01–P04"),
    "test_estadistica_series": ("Métricas OLS / Poisson / MAPE", "Predicciones — proyección mensual", "P01–P04"),
    "test_prioridad_territorial": ("Índice prioridad territorial", "Predicciones — prioridad territorial", "P05"),
    "test_carga_esperada_territorial": ("Carga proyectada territorial", "Predicciones — carga territorial", "P08–P10"),
    "test_proporcion_fatales_mensual": ("Proporción víctimas fatales", "Predicciones — proporción fatales", "P07"),
    "test_patrones_temporales_proyectados": ("Patrones día×hora y día semana", "Predicciones — patrones temporales", "P12–P13"),
}

_EPIC_BY_APP = {
    "accounts": "Cuentas y autenticación",
    "agent": "Asistente IA (Gemini)",
    "reports": "Reportes imprimibles",
    "dashboard": "Dashboard, mapa y predicciones",
}

_CRITICAL_FILES = frozenset(
    {
        "test_auth_api",
        "test_admin_api",
        "test_predicciones_permission",
        "test_predicciones_mensuales_api",
        "test_agent_api",
    }
)

_MINOR_FILES = frozenset(
    {
        "test_map_optimizations",
        "test_comunas_geojson",
    }
)


def _app_from_path(path: Path) -> str:
    parts = path.parts
    for app in ("accounts", "dashboard", "agent", "reports"):
        if app in parts:
            return app
    return "backend"


def _file_stem(path: Path) -> str:
    return path.stem


def _story_from_name(test_name: str) -> str:
    raw = test_name.removeprefix("test_").replace("_", " ")
    return raw[:1].upper() + raw[1:] if raw else test_name


def _tipo_prueba(stem: str) -> str:
    if stem.endswith("_api"):
        return "API REST"
    if stem.endswith("_logica") or "logica" in stem:
        return "Lógica / unitaria"
    if "postgis" in stem or "geoespacial" in stem or "geojson" in stem:
        return "Integración geoespacial"
    if "regression" in stem:
        return "Regresión"
    return "Lógica de negocio"


def _capa(tipo: str) -> str:
    if tipo == "API REST":
        return "API"
    if tipo == "Integración geoespacial":
        return "Integración"
    if tipo == "Regresión":
        return "Regresión"
    return "Unidad"


def _severity_for(stem: str, allure_module):
    if stem in _CRITICAL_FILES:
        return allure_module.severity_level.CRITICAL
    if stem in _MINOR_FILES:
        return allure_module.severity_level.MINOR
    if stem.endswith("_api"):
        return allure_module.severity_level.NORMAL
    return allure_module.severity_level.NORMAL


def apply_allure_labels(item, allure_module) -> None:
    """Aplica epic, feature, story, severity y labels dinámicos al test en curso."""
    path = Path(str(item.fspath))
    stem = _file_stem(path)
    app = _app_from_path(path)

    epic = _EPIC_BY_APP.get(app, "Backend ViaData")
    feature, categoria, indicador = _FEATURE_BY_FILE.get(
        stem,
        (stem.removeprefix("test_").replace("_", " ").title(), "General", "—"),
    )

    tipo = _tipo_prueba(stem)
    capa = _capa(tipo)
    story = _story_from_name(item.name)
    doc = getattr(item.function, "__doc__", None) or ""
    description = doc.strip() if doc and doc.strip() else f"Prueba automática: {story}."

    allure_module.dynamic.parent_suite("ViaData Medellín — Backend")
    allure_module.dynamic.suite(epic)
    allure_module.dynamic.sub_suite(categoria)
    allure_module.dynamic.epic(epic)
    allure_module.dynamic.feature(feature)
    allure_module.dynamic.story(story)
    allure_module.dynamic.title(story)
    allure_module.dynamic.description(description)
    allure_module.dynamic.severity(_severity_for(stem, allure_module))

    allure_module.dynamic.label("modulo", app)
    allure_module.dynamic.label("categoria", categoria)
    allure_module.dynamic.label("tipo_prueba", tipo)
    allure_module.dynamic.label("capa", capa)
    allure_module.dynamic.label("archivo", stem)
    if indicador != "—":
        allure_module.dynamic.label("indicador", indicador)
        for tag in indicador.replace("–", "-").split("-"):
            tag = tag.strip()
            if tag:
                allure_module.dynamic.tag(tag)

    # Enlace al código fuente en el reporte
    try:
        allure_module.dynamic.link(
            url=path.as_uri(),
            name=path.name,
            link_type=allure_module.link_type.LINK,
        )
    except Exception:
        pass


def write_allure_metadata(allure_dir: Path) -> None:
    """Escribe environment.properties, executor.json y categories.json."""
    allure_dir.mkdir(parents=True, exist_ok=True)

    django_ver = ""
    try:
        import django

        django_ver = django.get_version()
    except Exception:
        pass

    env_lines = [
        "Proyecto=ViaData — Medellín (USB)",
        "Componente=Backend Django REST",
        f"Python={sys.version.split()[0]}",
        f"Django={django_ver}",
        "Base_de_datos_pruebas=SQLite (settings_test)",
        "Framework_pruebas=pytest + pytest-django",
        "Reporte=Allure",
    ]
    (allure_dir / "environment.properties").write_text(
        "\n".join(env_lines) + "\n",
        encoding="utf-8",
    )

    # Sin executor.json: Allure muestra la sección "Ejecutores" con icono de casco
    # para type=local; no aporta valor en ejecución local y puede confundir.

    categories_src = Path(__file__).resolve().parent / "allure" / "categories.json"
    if categories_src.is_file():
        (allure_dir / "categories.json").write_text(
            categories_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
