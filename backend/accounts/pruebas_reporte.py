"""Cuerpo del reporte imprimible de pruebas (administrador)."""
from __future__ import annotations

from typing import Any

from .pruebas_runner import _read_state, build_status_payload, parse_allure_summary


def build_pruebas_report_body() -> dict[str, Any]:
    estado = build_status_payload()
    resumen = parse_allure_summary()
    state = _read_state()
    return {
        "tipo": "pruebas",
        "hay_resultados": resumen.get("hay_resultados", False),
        "ejecucion": {
            "estado": estado.get("estado"),
            "iniciado_en": estado.get("iniciado_en"),
            "finalizado_en": estado.get("finalizado_en"),
            "codigo_salida": estado.get("codigo_salida"),
            "iniciado_por": estado.get("iniciado_por"),
            "mensaje": estado.get("mensaje"),
        },
        "resumen": resumen,
    }
