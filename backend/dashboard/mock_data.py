"""
Datos de demostración coherentes con los indicadores descritos en bases.txt
y CONTEXTO_CHAT.md, y con la lógica de agregación de queries_indicadores.sql
(sin datos reales de incidentes).
"""


def get_dashboard_mock():
    """Resumen de KPIs y series para el tablero (mock)."""
    return {
        "meta": {
            "periodo_etiqueta": "Últimos 12 meses (demostración)",
            "es_demostracion": True,
        },
        "kpis": {
            "total_incidentes": 1842,
            "total_victimas": 2315,
            "victimas_fatales": 87,
            "tasa_incidentes_por_dia": 5.04,
            "dias_en_periodo": 365,
        },
        "comparacion_anual": {
            "incidentes_variacion_pct": -4.2,
            "victimas_variacion_pct": -2.1,
            "fatales_variacion_pct": -8.5,
        },
        "evolucion_mensual": [
            {"mes": "2025-05", "total_incidentes": 142, "total_victimas": 178},
            {"mes": "2025-06", "total_incidentes": 151, "total_victimas": 189},
            {"mes": "2025-07", "total_incidentes": 163, "total_victimas": 201},
            {"mes": "2025-08", "total_incidentes": 158, "total_victimas": 195},
            {"mes": "2025-09", "total_incidentes": 149, "total_victimas": 188},
            {"mes": "2025-10", "total_incidentes": 155, "total_victimas": 192},
            {"mes": "2025-11", "total_incidentes": 161, "total_victimas": 198},
            {"mes": "2025-12", "total_incidentes": 168, "total_victimas": 205},
            {"mes": "2026-01", "total_incidentes": 159, "total_victimas": 199},
            {"mes": "2026-02", "total_incidentes": 152, "total_victimas": 191},
            {"mes": "2026-03", "total_incidentes": 147, "total_victimas": 184},
            {"mes": "2026-04", "total_incidentes": 139, "total_victimas": 176},
        ],
        "por_dia_semana": [
            {"dia": "Lunes", "orden": 1, "total_incidentes": 248, "porcentaje": 13.5},
            {"dia": "Martes", "orden": 2, "total_incidentes": 261, "porcentaje": 14.2},
            {"dia": "Miércoles", "orden": 3, "total_incidentes": 255, "porcentaje": 13.8},
            {"dia": "Jueves", "orden": 4, "total_incidentes": 272, "porcentaje": 14.8},
            {"dia": "Viernes", "orden": 5, "total_incidentes": 289, "porcentaje": 15.7},
            {"dia": "Sábado", "orden": 6, "total_incidentes": 301, "porcentaje": 16.3},
            {"dia": "Domingo", "orden": 0, "total_incidentes": 216, "porcentaje": 11.7},
        ],
        "por_hora": [
            {"hora": h, "total_incidentes": max(12, 95 - abs(h - 18) * 4 + (h % 5))}
            for h in range(24)
        ],
        "heatmap_dia_hora": _mock_heatmap_dia_hora(),
        "top_comunas": [
            {"nombre": "La Candelaria", "total_incidentes": 198, "total_victimas": 241, "victimas_fatales": 9},
            {"nombre": "El Poblado", "total_incidentes": 176, "total_victimas": 214, "victimas_fatales": 7},
            {"nombre": "Belén", "total_incidentes": 162, "total_victimas": 201, "victimas_fatales": 8},
            {"nombre": "Laureles", "total_incidentes": 151, "total_victimas": 188, "victimas_fatales": 6},
            {"nombre": "Buenos Aires", "total_incidentes": 143, "total_victimas": 179, "victimas_fatales": 7},
            {"nombre": "Aranjuez", "total_incidentes": 131, "total_victimas": 165, "victimas_fatales": 5},
            {"nombre": "Robledo", "total_incidentes": 128, "total_victimas": 159, "victimas_fatales": 6},
            {"nombre": "Itagüí (corredor)", "total_incidentes": 119, "total_victimas": 147, "victimas_fatales": 4},
            {"nombre": "Guayabal", "total_incidentes": 112, "total_victimas": 138, "victimas_fatales": 5},
            {"nombre": "San Javier", "total_incidentes": 105, "total_victimas": 129, "victimas_fatales": 4},
        ],
        "top_vias": [
            {
                "nombre": "Carrera 43A",
                "total_incidentes": 124,
                "total_victimas": 156,
                "victimas_fatales": 5,
                "victimas_graves": 28,
            },
            {
                "nombre": "Autopista Sur",
                "total_incidentes": 118,
                "total_victimas": 149,
                "victimas_fatales": 7,
                "victimas_graves": 31,
            },
            {
                "nombre": "Calle 80",
                "total_incidentes": 109,
                "total_victimas": 138,
                "victimas_fatales": 4,
                "victimas_graves": 24,
            },
            {
                "nombre": "Avenida Regional",
                "total_incidentes": 101,
                "total_victimas": 127,
                "victimas_fatales": 6,
                "victimas_graves": 22,
            },
            {
                "nombre": "Calle 10",
                "total_incidentes": 96,
                "total_victimas": 121,
                "victimas_fatales": 3,
                "victimas_graves": 19,
            },
        ],
        "top_puntos_criticos": [
            {
                "nombre": "Intersección Calle 10 con Carrera 43",
                "tipo_punto": "Intersección",
                "prioridad": 1,
                "total_incidentes": 42,
                "latitud": 6.2088,
                "longitud": -75.5678,
            },
            {
                "nombre": "Cruce Autopista Sur - Metro Itagüí",
                "tipo_punto": "Cruce",
                "prioridad": 1,
                "total_incidentes": 38,
                "latitud": 6.1724,
                "longitud": -75.5955,
            },
            {
                "nombre": "Curva sector La Aguacatala",
                "tipo_punto": "Curva",
                "prioridad": 2,
                "total_incidentes": 31,
                "latitud": 6.1972,
                "longitud": -75.5731,
            },
        ],
        "gravedad_distribucion": [
            {"codigo": "FATAL", "nombre": "Fatal", "cantidad": 87, "porcentaje": 3.8},
            {"codigo": "GRAVE", "nombre": "Grave", "cantidad": 412, "porcentaje": 17.8},
            {"codigo": "LEVE", "nombre": "Leve", "cantidad": 1289, "porcentaje": 55.7},
            {"codigo": "SOLO_DANOS", "nombre": "Solo daños", "cantidad": 527, "porcentaje": 22.7},
        ],
        "clase_incidente_distribucion": [
            {"nombre": "Choque", "total_incidentes": 612, "porcentaje": 33.2},
            {"nombre": "Atropello", "total_incidentes": 398, "porcentaje": 21.6},
            {"nombre": "Volcamiento", "total_incidentes": 241, "porcentaje": 13.1},
            {"nombre": "Caída de ocupante", "total_incidentes": 187, "porcentaje": 10.2},
            {"nombre": "Otro", "total_incidentes": 404, "porcentaje": 21.9},
        ],
        "mapa_calor_puntos": [
            {"lat": 6.2442, "lng": -75.5812, "intensidad": 0.9},
            {"lat": 6.2301, "lng": -75.5904, "intensidad": 0.75},
            {"lat": 6.2019, "lng": -75.5638, "intensidad": 0.65},
            {"lat": 6.2567, "lng": -75.5981, "intensidad": 0.55},
            {"lat": 6.1755, "lng": -75.6022, "intensidad": 0.48},
            {"lat": 6.2203, "lng": -75.5510, "intensidad": 0.42},
        ],
    }


def _mock_heatmap_dia_hora():
    """Matriz día (0=Dom) × hora coherente con 2.4 queries_indicadores."""
    dias = list(range(7))
    horas = list(range(24))
    out = []
    for d in dias:
        for h in horas:
            base = 1 + (d + h) % 5
            peak = 4 if 7 <= h <= 9 or 17 <= h <= 20 else 0
            weekend = 2 if d in (0, 6) and 14 <= h <= 23 else 0
            out.append(
                {
                    "dia_semana": d,
                    "hora": h,
                    "total_incidentes": base + peak + weekend,
                }
            )
    return out
