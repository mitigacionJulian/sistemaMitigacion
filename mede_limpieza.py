# -*- coding: utf-8 -*-
"""
Reglas de limpieza del dataset MedeDatos (víctimas / incidentes): mojibake, tildes, ñ,
comuna/barrio, día, Grupo_edad, coordenadas, radicado, sexo/condición.

El flujo completo (estructura, gráficas y export) se ejecuta con `mede_eda_export.py`.

Uso desde la raíz del proyecto:
  pip install -r requirements-etl.txt
  python mede_limpieza.py analyze
  python mede_limpieza.py analyze --path Mede_Victimas_inci.xlsx
  python mede_limpieza.py clean --output datos_mede_depurados.xlsx
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

# Comuna / barrio: sin tildes (ASCII “legible”) y capitalización tipo título con
# partículas en minúsculas, p. ej. “Corregimiento de San Cristobal”.
COLUMNAS_GEO_ASCII = ("Comuna", "Barrio")

# Partículas que se dejan en minúsculas salvo si son la primera palabra del tramo.
_GEO_PARTICULAS = frozenset({"de", "del", "y", "e"})

# Columnas de texto donde conviene normalizar Unicode y espacios (tildes, ñ).
COLUMNAS_TEXTO = (
    "Gravedad_victima",
    "Hora_incidente",
    "Clase_incidente",
    "Direccion_incidente",
    "Sexo",
    "Edad",
    "Condicion",
    "Mes",
    "Dia",
    "Hora",
    "Grupo_edad",
    "Comuna",
    "Barrio",
)

# Excel suele interpretar "10 - 19" como fecha 2019-10-01.
_FECHA_EXCEL_GRUPO_EDAD = pd.Timestamp("2019-10-01")

# Rutas relativas típicas al CSV legado (misma convención que el antiguo Exploratorio.py).
_MEDE_CSV_CANDIDATES = (
    Path("Mede_Victimas_inci (1).csv"),
    Path("data") / "Mede_Victimas_inci (1).csv",
    Path("datos") / "Mede_Victimas_inci (1).csv",
)
_DEFAULT_MEDE_XLSX = Path("Mede_Victimas_inci.xlsx")

# Variantes de Condición que vimos en el archivo (clave = minúsculas NFC).
_CONDICION_CANONICA = {
    "motociclista": "Motociclista",
    "peatón": "Peatón",
    "peaton": "Peatón",
    "acompañante de motocicleta": "Acompañante de Motocicleta",
    "acompanante de motocicleta": "Acompañante de Motocicleta",
    "pasajero": "Pasajero",
    "conductor": "Conductor",
    "ciclista": "Ciclista",
}

# Sexo
_SEXO_CANONICO = {
    "m": "M",
    "f": "F",
    "sin inf": "Sin Inf",
    "sin información": "Sin Inf",
    "sin informacion": "Sin Inf",
}


def _nfc(val: object) -> object:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return val
    if not isinstance(val, str):
        return val
    t = unicodedata.normalize("NFC", val.strip())
    t = " ".join(t.split())
    return t


def fix_mojibake_utf8(s: str) -> str:
    """
    Repara texto UTF-8 leído/guardado como Latin-1 (p. ej. PeatÃ³n -> Peatón).
    Solo intenta la recodificación si hay secuencias típicas de mojibake.
    """
    if not s or not isinstance(s, str):
        return s
    cur = s
    for _ in range(3):
        if "Ã" not in cur and "Â" not in cur:
            break
        try:
            nxt = cur.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            break
        if nxt == cur:
            break
        cur = nxt
    return cur


def _strip_accents_ascii(s: str) -> str:
    """Quita marcas diacríticas (á->a, ñ->n) para nombres geográficos en ASCII."""
    if not s:
        return s
    return "".join(
        c
        for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _capitalizar_palabra_geo(w: str) -> str:
    if not w:
        return w
    if len(w) == 1:
        return w.upper()
    return w[0].upper() + w[1:].lower()


def _casing_geo_tras_ascii(s: str) -> str:
    """
    “12 - la america” -> “12 - La America”; “Corregimiento de SAN cristobal” coherente.
    """
    s = " ".join(s.split())
    if not s:
        return s
    m = re.match(r"^(\d+\s*-\s*)(.+)$", s)
    if m:
        pref, resto = m.group(1), m.group(2).strip()
        return pref + _casing_geo_tras_ascii(resto)
    partes = s.split()
    out: list[str] = []
    for i, w in enumerate(partes):
        lw = w.lower()
        if i > 0 and lw in _GEO_PARTICULAS:
            out.append(lw)
        else:
            out.append(_capitalizar_palabra_geo(w))
    return " ".join(out)


def _normalizar_geo_ascii(val: object) -> object:
    s = _nfc(val)
    if not isinstance(s, str):
        return val
    return _casing_geo_tras_ascii(_strip_accents_ascii(s))


# Día de la semana (abreviado): sin tilde, primera letra en mayúscula (Mier, Sab).
_DIA_FOLD_TO_CANON = {
    "lun": "Lun",
    "lunes": "Lun",
    "mar": "Mar",
    "martes": "Mar",
    "mie": "Mier",
    "mier": "Mier",
    "miercoles": "Mier",
    "jue": "Jue",
    "jueves": "Jue",
    "vie": "Vie",
    "viernes": "Vie",
    "sab": "Sab",
    "sabado": "Sab",
    "dom": "Dom",
    "domingo": "Dom",
}


def _fold_dia(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower().strip())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _canonico_dia(val: object) -> object:
    s = _nfc(val)
    if not isinstance(s, str):
        return val
    clave = _fold_dia(s)
    return _DIA_FOLD_TO_CANON.get(clave, s)


def _prep_texto_mede(val: object) -> object:
    """Mojibake UTF-8 + NFC + espacios (antes de reglas por columna)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return val
    if not isinstance(val, str):
        return val
    return _nfc(fix_mojibake_utf8(val))


def renombrar_columnas_mojibake(df: pd.DataFrame) -> pd.DataFrame:
    """Corrige encabezados mal codificados (p. ej. AÃ±o -> Año)."""
    cmap: dict[str, str] = {}
    for c in df.columns:
        if isinstance(c, str):
            nuevo = fix_mojibake_utf8(c)
            if nuevo != c:
                cmap[c] = nuevo
    return df.rename(columns=cmap) if cmap else df


def load_mede_xlsx(path: str | Path, *, sheet_name: str | int = 0) -> pd.DataFrame:
    """
    Lee el Excel oficial con motor openpyxl (preserva mejor tildes/ñ que muchos CSV mal exportados).
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    return df


def _bajo_base(base: Path, rel: Path) -> Path:
    return (base / rel).resolve() if not rel.is_absolute() else rel.resolve()


def find_mede_xlsx(
    base_dir: str | Path,
    name: str | Path = _DEFAULT_MEDE_XLSX,
) -> Path | None:
    """Devuelve ruta al .xlsx si existe bajo `base_dir`, si no None."""
    base = Path(base_dir).resolve()
    cand = _bajo_base(base, Path(name))
    return cand if cand.is_file() else None


def find_first_mede_csv(base_dir: str | Path) -> Path | None:
    """Primera ruta CSV conocida que exista bajo `base_dir`."""
    base = Path(base_dir).resolve()
    for rel in _MEDE_CSV_CANDIDATES:
        cand = _bajo_base(base, rel)
        if cand.is_file():
            return cand
    return None


def load_mede_csv(
    path: str | Path,
    *,
    nrows: int | None = None,
    encoding: str | None = None,
) -> pd.DataFrame:
    """
    Lee CSV Mede; prueba encodings comunes. `nrows` limita filas (útil en CSV muy grande).
    Tras cargar, aplicar siempre `depurar_mede()` para las mismas reglas que el .xlsx.
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    kw: dict[str, object] = {"low_memory": False}
    if nrows is not None:
        kw["nrows"] = nrows
    if encoding is not None:
        return pd.read_csv(path, encoding=encoding, **kw)
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, **kw)


def load_mede_auto(
    *,
    base_dir: str | Path | None = None,
    fuente: str = "auto",
    xlsx_name: str | Path = _DEFAULT_MEDE_XLSX,
    csv_nrows: int | None = None,
) -> tuple[pd.DataFrame, str]:
    """
    Carga el dataset crudo: por defecto prioriza `.xlsx` y si no existe usa el CSV legado.

    Returns:
        (DataFrame, etiqueta) donde etiqueta es p. ej. ``xlsx:/ruta/archivo.xlsx``.
    """
    base = Path(base_dir).resolve() if base_dir is not None else Path.cwd().resolve()
    xls = find_mede_xlsx(base, xlsx_name)
    csvp = find_first_mede_csv(base)

    if fuente not in ("auto", "xlsx", "csv"):
        raise ValueError("fuente debe ser 'auto', 'xlsx' o 'csv'")

    if fuente == "csv":
        if not csvp:
            raise FileNotFoundError(
                "No se encontró ningún CSV en las rutas conocidas bajo "
                f"{base}: {[str(p) for p in _MEDE_CSV_CANDIDATES]}"
            )
        return load_mede_csv(csvp, nrows=csv_nrows), f"csv:{csvp}"

    if fuente == "xlsx":
        if not xls:
            raise FileNotFoundError(f"No existe el Excel: {_bajo_base(base, Path(xlsx_name))}")
        return load_mede_xlsx(xls), f"xlsx:{xls}"

    if xls:
        return load_mede_xlsx(xls), f"xlsx:{xls}"
    if csvp:
        return load_mede_csv(csvp, nrows=csv_nrows), f"csv:{csvp}"

    raise FileNotFoundError(
        f"No se encontró {xlsx_name!s} ni CSV típico bajo {base}. "
        "Coloca el .xlsx en la raíz del repo o uno de los CSV en rutas data/datos."
    )


def imprimir_resumen_exploratorio(
    df: pd.DataFrame,
    *,
    top_k: int = 10,
    file: object | None = None,
) -> None:
    """
    Resumen tipo script legado: describe numérico + value_counts por columnas texto.
    Sirve desde terminal o desde el notebook (misma lógica, sin duplicar código).
    """
    out = file or sys.stdout
    print(f"\nFilas: {len(df):,}  |  Columnas: {len(df.columns)}\n", file=out)
    num = df.select_dtypes(include="number")
    if not num.empty:
        print("--- describe() numérico ---", file=out)
        print(num.describe().to_string(), file=out)
    obj = df.select_dtypes(include=("object", "string", "category"))
    for col in obj.columns:
        print(f"\n--- {col} (top {top_k}) ---", file=out)
        print(df[col].value_counts(dropna=False).head(top_k).to_string(), file=out)
        nu = int(df[col].nunique(dropna=False))
        if nu > top_k:
            print(f"... ({nu - top_k} valores más)", file=out)


def fix_grupo_edad_excel(val: object) -> object:
    """
    Corrige el caso típico en que Excel guardó el rango '10 - 19' como fecha 2019-10-01.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return val
    if isinstance(val, pd.Timestamp):
        if val.normalize() == _FECHA_EXCEL_GRUPO_EDAD.normalize():
            return "10 - 19"
        return str(val)
    if isinstance(val, datetime):
        ts = pd.Timestamp(val)
        if ts.normalize() == _FECHA_EXCEL_GRUPO_EDAD.normalize():
            return "10 - 19"
        return str(val)
    s = _nfc(val)
    if not isinstance(s, str):
        return val
    if s.startswith("2019-10-01"):
        return "10 - 19"
    return s


def _entero_nullable_seguro(v: object) -> object:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return pd.NA
    try:
        f = float(v)
    except (TypeError, ValueError):
        return pd.NA
    if f != f or f in (float("inf"), float("-inf")):  # NaN / inf
        return pd.NA
    try:
        return int(round(f))
    except (ValueError, OverflowError):
        return pd.NA


def _serie_a_enteros_nullable(serie: pd.Series) -> pd.Series:
    """Convierte a entero nullable (edad, etc.); evita overflow y valores no finitos."""
    return serie.map(_entero_nullable_seguro).astype("Int64")


def _radicado_a_texto(serie: pd.Series) -> pd.Series:
    """
    Radicado como texto estable (evita Int64 overflow y mantiene compatibilidad con SQL VARCHAR).
    Elimina '.0' típico de float en Excel.
    """
    def one(v: object) -> object:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return pd.NA
        num = pd.to_numeric(v, errors="coerce")
        if pd.notna(num):
            try:
                f = float(num)
                if f != f or not (-1e20 < f < 1e20):
                    return str(v).strip()
                return str(int(round(f)))
            except (ValueError, OverflowError):
                pass
        s = str(v).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return s or pd.NA

    return serie.map(one)


def parse_coordenada(val: object) -> float | type(pd.NA):
    """Convierte Latitud/Longitud a float; coma decimal; 'Sin Inf' -> NA."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return pd.NA
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in ("sin inf", "sin información", "sin informacion", "nan"):
        return pd.NA
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return pd.NA


def _canonico_condicion(val: object) -> object:
    s = _nfc(val)
    if not isinstance(s, str):
        return val
    clave = s.lower()
    return _CONDICION_CANONICA.get(clave, s)


def _canonico_sexo(val: object) -> object:
    s = _nfc(val)
    if not isinstance(s, str):
        return val
    if len(s) <= 2 and s.upper() in ("M", "F"):
        return s.upper()
    clave = s.lower()
    return _SEXO_CANONICO.get(clave, s)


def depurar_mede(df: pd.DataFrame) -> pd.DataFrame:
    """
    Copia depurada: corrección mojibake UTF-8/Latin-1, Unicode NFC, Grupo_edad
    (fecha Excel -> '10 - 19'), sexo/condición, comuna/barrio en ASCII con capitalización,
    días abreviados sin tilde, coordenadas numéricas, radicado estable.
    """
    out = renombrar_columnas_mojibake(df.copy())

    if "Grupo_edad" in out.columns:
        out["Grupo_edad"] = out["Grupo_edad"].map(fix_grupo_edad_excel)

    for col in COLUMNAS_TEXTO:
        if col not in out.columns:
            continue
        out[col] = out[col].map(_prep_texto_mede)

    for col in COLUMNAS_GEO_ASCII:
        if col not in out.columns:
            continue
        out[col] = out[col].map(_normalizar_geo_ascii)

    if "Dia" in out.columns:
        out["Dia"] = out["Dia"].map(_canonico_dia)

    if "Sexo" in out.columns:
        out["Sexo"] = out["Sexo"].map(_canonico_sexo)

    if "Condicion" in out.columns:
        out["Condicion"] = out["Condicion"].map(_canonico_condicion)

    for col in ("Latitud", "Longitud"):
        if col in out.columns:
            out[col] = out[col].map(parse_coordenada)
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "Radicado" in out.columns:
        out["Radicado"] = _radicado_a_texto(out["Radicado"])

    if "Edad" in out.columns:
        out["Edad"] = _serie_a_enteros_nullable(out["Edad"])

    return out


def analizar(df: pd.DataFrame, *, top_n: int = 10) -> None:
    """Imprime resumen útil en consola (similar a los análisis manuales previos)."""
    print("=== Resumen general ===")
    print(f"Filas: {len(df):,}  |  Columnas: {len(df.columns)}")
    print(f"Memoria aprox.: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MiB")
    print()

    print("=== info() ===")
    df.info()
    print()

    print("=== Valores nulos por columna ===")
    na = df.isna().sum().sort_values(ascending=False)
    for col, n in na.items():
        if n > 0:
            pct = 100.0 * n / len(df)
            print(f"  {col}: {n:,} ({pct:.2f}%)")
    if na.max() == 0:
        print("  (sin nulos)")
    print()

    print("=== Primeras filas ===")
    print(df.head().to_string())
    print()

    obj_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in obj_cols:
        print(f"--- {col} (top {top_n}) ---")
        vc = df[col].value_counts(dropna=False).head(top_n)
        print(vc.to_string())
        nu = df[col].nunique(dropna=False)
        if nu > top_n:
            print(f"... ({nu - top_n} valores más)")
        print()


def _guardar(df: pd.DataFrame, output: Path) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    suf = output.suffix.lower()
    if suf == ".xlsx":
        df.to_excel(output, index=False, engine="openpyxl")
    elif suf == ".csv":
        df.to_csv(output, index=False, encoding="utf-8-sig")
    elif suf == ".parquet":
        try:
            df.to_parquet(output, index=False)
        except ImportError as e:
            raise SystemExit(
                "Para escribir Parquet instala pyarrow: pip install pyarrow"
            ) from e
    else:
        raise SystemExit(f"Extensión no soportada: {suf} (use .xlsx, .csv o .parquet)")


def guardar_mede(df: pd.DataFrame, output: str | Path) -> None:
    """Exporta un DataFrame ya depurado (.xlsx, .csv o .parquet). Alias público de `_guardar`."""
    _guardar(df, Path(output))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exploración y depuración Mede_Victimas_inci.xlsx",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze", help="Cargar y mostrar análisis en consola")
    p_an.add_argument(
        "--path",
        type=Path,
        default=Path("Mede_Victimas_inci.xlsx"),
        help="Ruta al .xlsx (por defecto: Mede_Victimas_inci.xlsx en el cwd)",
    )
    p_an.add_argument("--depurado", action="store_true", help="Analizar tras depurar_mede()")

    p_cl = sub.add_parser("clean", help="Depurar y guardar en archivo")
    p_cl.add_argument("--input", type=Path, default=Path("Mede_Victimas_inci.xlsx"))
    p_cl.add_argument(
        "--output",
        type=Path,
        default=Path("salida") / "Mede_Victimas_inci_depurado.xlsx",
        help="Salida .xlsx, .csv o .parquet",
    )

    args = parser.parse_args(argv)

    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("Falta openpyxl. Ejecuta: pip install -r requirements-etl.txt", file=sys.stderr)
        return 1

    if args.cmd == "analyze":
        df = load_mede_xlsx(args.path)
        if args.depurado:
            df = depurar_mede(df)
            print("(Mostrando datos después de depurar_mede)\n")
        analizar(df)
        return 0

    if args.cmd == "clean":
        df = load_mede_xlsx(args.input)
        limpio = depurar_mede(df)
        _guardar(limpio, args.output)
        print(f"Guardado: {args.output.resolve()}  ({len(limpio):,} filas)")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
