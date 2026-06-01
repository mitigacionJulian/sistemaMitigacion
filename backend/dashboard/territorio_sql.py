"""
F3 — Modo territorial registro (Mede) vs espacial (PostGIS polígonos).
"""
from __future__ import annotations

from typing import Any, Literal, Protocol

ModoTerritorio = Literal["registro", "espacial"]
ModoPuntoCritico = Literal["registro", "proximidad"]

DEFAULT_RADIO_PUNTO_METROS = 150


class FiltrosTerritorio(Protocol):
    comuna_id: int | None
    barrio_id: int | None
    clase_incidente_id: int | None
    modo_territorio: str
    punto_critico_id: int | None
    punto_critico_modo: str


def parse_modo_territorio(raw: str | None) -> ModoTerritorio:
    if raw and str(raw).strip().lower() in ("espacial", "spatial", "postgis"):
        return "espacial"
    return "registro"


def parse_modo_punto_critico(raw: str | None) -> ModoPuntoCritico:
    if raw and str(raw).strip().lower() in ("proximidad", "dwithin", "radio", "espacial"):
        return "proximidad"
    return "registro"


def radio_punto_metros_sql(alias_pc: str = "pc") -> str:
    return f"COALESCE(NULLIF({alias_pc}.radio_metros, 0), {DEFAULT_RADIO_PUNTO_METROS})"


def dwithin_incidente_punto_sql(alias_i: str = "i", alias_pc: str = "pc") -> str:
    return f"""ST_DWithin(
        {alias_i}.ubicacion::geography,
        {alias_pc}.ubicacion::geography,
        {radio_punto_metros_sql(alias_pc)}
    )"""


def punto_critico_serie_sql(
    filtros: FiltrosTerritorio,
) -> tuple[str, list[Any], list[str], list[Any]]:
    """
    Fragmentos SQL para filtrar serie mensual por punto crítico.
    Returns: join_clause, join_params, extra_where, extra_params
    """
    if filtros.punto_critico_id is None:
        return "", [], [], []
    modo = parse_modo_punto_critico(getattr(filtros, "punto_critico_modo", None))
    if modo == "proximidad":
        return (
            "INNER JOIN punto_critico pc ON pc.id = %s",
            [filtros.punto_critico_id],
            [
                "i.ubicacion IS NOT NULL",
                "pc.ubicacion IS NOT NULL",
                dwithin_incidente_punto_sql(),
            ],
            [],
        )
    return "", [], ["i.punto_critico_id = %s"], [filtros.punto_critico_id]


def nota_modo_punto_critico(modo: str) -> str | None:
    if parse_modo_punto_critico(modo) == "proximidad":
        return (
            "P11 proximidad: incidentes con coordenada dentro del radio del punto crítico "
            f"(ST_DWithin; radio por registro o {DEFAULT_RADIO_PUNTO_METROS} m por defecto). "
            "Compare con modo registro (FK punto_critico_id en Mede)."
        )
    return None


def comuna_fk_col(modo: str) -> str:
    return "comuna_id_espacial" if modo == "espacial" else "comuna_id"


def barrio_fk_col(modo: str) -> str:
    return "barrio_id_espacial" if modo == "espacial" else "barrio_id"


def append_filtros_territoriales(
    where: list[str],
    params: list[Any],
    filtros: FiltrosTerritorio,
    *,
    alias: str = "i",
) -> None:
    modo = filtros.modo_territorio or "registro"
    if modo == "espacial":
        where.append(f"{alias}.ubicacion IS NOT NULL")
    col_c = comuna_fk_col(modo)
    col_b = barrio_fk_col(modo)
    if filtros.comuna_id is not None:
        where.append(f"{alias}.{col_c} = %s")
        params.append(filtros.comuna_id)
    if filtros.barrio_id is not None:
        where.append(f"{alias}.{col_b} = %s")
        params.append(filtros.barrio_id)
    if filtros.clase_incidente_id is not None:
        where.append(f"{alias}.clase_incidente_id = %s")
        params.append(filtros.clase_incidente_id)


def meta_filtros_dict(filtros: FiltrosTerritorio) -> dict[str, Any]:
    return {
        "comuna_id": filtros.comuna_id,
        "barrio_id": filtros.barrio_id,
        "clase_incidente_id": filtros.clase_incidente_id,
        "territorio": filtros.modo_territorio or "registro",
    }


def nota_modo_territorio(modo: str) -> str | None:
    if modo == "espacial":
        return (
            "Filtros y rankings usan comuna_id_espacial / barrio_id_espacial "
            "(punto dentro del polígono oficial). Compare con modo registro y G03."
        )
    return None


def parse_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    """Legacy G05 — omitido del producto; filtros comuna/barrio cubren el alcance."""
    if raw is None or not str(raw).strip():
        return None
    parts = [p.strip() for p in str(raw).split(",")]
    if len(parts) != 4:
        raise ValueError("bbox")
    min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("bbox")
    return (min_lon, min_lat, max_lon, max_lat)


def append_filtro_bbox(
    where: list[str],
    params: list[Any],
    bbox: tuple[float, float, float, float] | None,
    *,
    alias: str = "i",
) -> None:
    if bbox is None:
        return
    min_lon, min_lat, max_lon, max_lat = bbox
    where.append(
        f"ST_Intersects({alias}.ubicacion, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
    )
    params.extend([min_lon, min_lat, max_lon, max_lat])


def append_filtro_geojson(
    where: list[str],
    params: list[Any],
    geojson: str | None,
    *,
    alias: str = "i",
) -> None:
    if not geojson or not str(geojson).strip():
        return
    where.append(
        f"ST_Intersects({alias}.ubicacion, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))"
    )
    params.append(str(geojson).strip())


def meta_bbox_dict(bbox: tuple[float, float, float, float] | None) -> dict[str, Any] | None:
    if bbox is None:
        return None
    min_lon, min_lat, max_lon, max_lat = bbox
    return {
        "min_lon": min_lon,
        "min_lat": min_lat,
        "max_lon": max_lon,
        "max_lat": max_lat,
    }
