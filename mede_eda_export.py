# -*- coding: utf-8 -*-
"""
Pipeline Mede: carga .xlsx, estructura y nulos en consola, gráficas para decisiones
sobre atípicos y nulos, export .xlsx depurado (misma lógica que `mede_limpieza.depurar_mede`).

Ejecución desde la raíz del repositorio:

  pip install -r requirements-etl.txt
  python mede_eda_export.py
  python mede_eda_export.py --input Mede_Victimas_inci.xlsx --output salida/limpio.xlsx
  python mede_eda_export.py --show   # además de guardar PNG, abre ventanas matplotlib
  python mede_eda_export.py --keep-rows-with-nulls   # no quitar filas con NA (comportamiento antiguo)
  python mede_eda_export.py --sin-tope-edad-67       # no eliminar filas con Edad > 67
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _null_table(df, *, label: str) -> None:
    import pandas as pd

    n = len(df)
    na = df.isna().sum().sort_values(ascending=False)
    na_pct = (100 * na / n).round(2)
    tab = (
        pd.DataFrame({"nulos": na, "pct_filas": na_pct})
        .query("nulos > 0")
        .sort_values("pct_filas", ascending=False)
    )
    print(f"\n=== Nulos ({label}) — columnas con al menos un NA ===")
    if tab.empty:
        print("(ninguna columna con nulos)")
    else:
        print(tab.to_string())


def _print_info(df, *, label: str) -> None:
    import pandas as pd

    print(f"\n=== info() — {label} ===")
    buf = io.StringIO()
    df.info(buf=buf, memory_usage="deep")
    print(buf.getvalue())
    print(f"Filas: {len(df):,}  |  Columnas: {len(df.columns)}")


def _figure_nulos(df, out: Path) -> None:
    import matplotlib.pyplot as plt

    n = len(df)
    na_pct = (100 * df.isna().sum() / n).sort_values(ascending=True)
    na_pct = na_pct[na_pct > 0]
    if na_pct.empty:
        return
    fig, ax = plt.subplots(figsize=(12, max(4.0, 0.4 * len(na_pct))))
    na_pct.plot.barh(ax=ax, color="steelblue")
    ax.set_xlabel("% de filas con NA")
    ax.set_title("Nulos por columna (depurado)")
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def _figure_edad(df, out: Path) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    if "Edad" not in df.columns:
        return
    e = df["Edad"].dropna().astype(float)
    if e.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
    sns.histplot(e.clip(0, 100), bins=45, kde=True, color="teal", ax=axes[0])
    axes[0].set_title("Edad (capada a 100) + densidad")
    axes[0].set_xlabel("Edad")
    axes[0].grid(axis="y", linestyle="--", alpha=0.25)
    e.plot.box(ax=axes[1], vert=True, color="darkslateblue")
    axes[1].set_title("Edad (boxplot)")
    axes[1].grid(axis="y", linestyle="--", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def _figure_edad_anio(df, out: Path) -> None:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    col_anio = "Año" if "Año" in df.columns else ("Ano" if "Ano" in df.columns else None)
    if col_anio is None or "Edad" not in df.columns:
        return

    work = df[[col_anio, "Edad"]].copy()
    work[col_anio] = pd.to_numeric(work[col_anio], errors="coerce")
    work["Edad"] = pd.to_numeric(work["Edad"], errors="coerce")
    work = work.dropna(subset=[col_anio, "Edad"])
    if work.empty:
        return

    # Evita años basura y ordena cronológicamente.
    work = work[work[col_anio].between(1990, 2100)]
    if work.empty:
        return
    work[col_anio] = work[col_anio].astype(int)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.2))

    med = work.groupby(col_anio)["Edad"].median().sort_index()
    q1 = work.groupby(col_anio)["Edad"].quantile(0.25).sort_index()
    q3 = work.groupby(col_anio)["Edad"].quantile(0.75).sort_index()
    axes[0].plot(med.index, med.values, marker="o", linewidth=2.2, color="darkorange", label="Mediana")
    axes[0].fill_between(med.index, q1.values, q3.values, color="orange", alpha=0.18, label="IQR (p25-p75)")
    axes[0].set_title("Edad por año (mediana e IQR)")
    axes[0].set_xlabel("Año")
    axes[0].set_ylabel("Edad")
    axes[0].grid(True, linestyle="--", alpha=0.3)
    axes[0].legend()

    top_years = med.index.tolist()
    sns.boxplot(data=work[work[col_anio].isin(top_years)], x=col_anio, y="Edad", ax=axes[1], color="lightsteelblue", fliersize=2)
    axes[1].set_title("Distribución de edad por año (boxplot)")
    axes[1].set_xlabel("Año")
    axes[1].set_ylabel("Edad")
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].grid(axis="y", linestyle="--", alpha=0.25)

    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def _figure_mapa(df, out: Path) -> None:
    import matplotlib.pyplot as plt

    if not {"Latitud", "Longitud"}.issubset(df.columns):
        return
    lat, lon = df["Latitud"], df["Longitud"]
    ok = lat.notna() & lon.notna()
    if not ok.any():
        return
    LAT_MIN, LAT_MAX = 6.05, 6.55
    LON_MIN, LON_MAX = -75.78, -75.42
    sub = df.loc[ok]
    sample = min(12_000, len(sub))
    if sample < len(sub):
        sub = sub.sample(sample, random_state=42)
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    ax.scatter(sub["Longitud"], sub["Latitud"], s=7, alpha=0.35, c="#1f4e79")
    ax.axvline(LON_MIN, color="red", ls="--", lw=0.8)
    ax.axvline(LON_MAX, color="red", ls="--", lw=0.8)
    ax.axhline(LAT_MIN, color="red", ls="--", lw=0.8)
    ax.axhline(LAT_MAX, color="red", ls="--", lw=0.8)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title("Coordenadas (caja roja aproximada — revisar atípicos)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", alpha=0.22)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def _figure_categorias(df, out: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    cols = [c for c in ("Condicion", "Gravedad_victima", "Sexo", "Comuna") if c in df.columns]
    if not cols:
        return
    ncols = 2
    nrows = (len(cols) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 3.8 * nrows))
    axes_flat = np.atleast_1d(axes).ravel()
    for i, col in enumerate(cols):
        ax = axes_flat[i]
        df[col].value_counts(dropna=False).head(12).plot.barh(ax=ax, color="cadetblue")
        ax.set_title(col)
        ax.invert_yaxis()
    for j in range(len(cols), len(axes_flat)):
        axes_flat[j].set_visible(False)
    fig.suptitle("Top categorías (depurado)", y=1.02)
    fig.tight_layout()
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EDA visual + export .xlsx depurado Mede (usa mede_limpieza).",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "datos_mede_decodificados.xlsx",
        help="Ruta al .xlsx de entrada",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "salida" / "Mede_Victimas_inci_depurado.xlsx",
        help="Ruta al .xlsx depurado de salida",
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=ROOT / "salida" / "mede_eda_figuras",
        help="Carpeta donde guardar PNG de apoyo para decisiones",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Abrir ventanas matplotlib además de guardar PNG (requiere entorno gráfico)",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Solo consola + export, sin generar figuras",
    )
    parser.add_argument(
        "--keep-rows-with-nulls",
        action="store_true",
        help=(
            "Tras depurar_mede, no eliminar filas: conserva filas con al menos un NA. "
            "Por defecto se descartan filas con cualquier valor nulo (solo en este script)."
        ),
    )
    parser.add_argument(
        "--sin-tope-edad-67",
        action="store_true",
        help="No eliminar víctimas con Edad > 67 (por defecto sí se eliminan, solo en este script).",
    )
    args = parser.parse_args(argv)

    inp = args.input.resolve()
    if not inp.is_file():
        print(f"No existe el archivo de entrada: {inp}", file=sys.stderr)
        return 1

    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("Falta openpyxl. Ejecuta: pip install -r requirements-etl.txt", file=sys.stderr)
        return 1

    import matplotlib

    matplotlib.use("TkAgg" if args.show else "Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid", context="talk")

    import mede_limpieza as mede

    print("=== 1) Carga .xlsx ===", flush=True)
    df_raw = mede.load_mede_xlsx(inp)
    print(f"Archivo: {inp}")
    print(f"Dimensiones crudas: {df_raw.shape[0]:,} filas × {df_raw.shape[1]} columnas")

    print("\n=== 2) Estructura y nulos (crudo) ===")
    _print_info(df_raw, label="crudo")
    _null_table(df_raw, label="crudo")
    print("\n--- Resumen exploratorio (crudo, top 10 por columna texto) ---")
    mede.imprimir_resumen_exploratorio(df_raw, top_k=10)

    print("\n=== Depuración (mede_limpieza.depurar_mede) ===")
    df = mede.depurar_mede(df_raw)
    n_tras_depurar = len(df)
    if not args.keep_rows_with_nulls:
        df = df.dropna(how="any")
        quitadas = n_tras_depurar - len(df)
        if n_tras_depurar > 0:
            pct_elim = 100.0 * quitadas / n_tras_depurar
            pct_quedan = 100.0 * len(df) / n_tras_depurar
        else:
            pct_elim = pct_quedan = 0.0
        print(
            f"Filas con al menos un NA eliminadas: {quitadas:,} "
            f"({pct_elim:.2f}% sobre las {n_tras_depurar:,} filas tras depurar_mede). "
            f"Permanecen {len(df):,} ({pct_quedan:.2f}%).",
            flush=True,
        )
        if len(df) == 0:
            print(
                "Advertencia: no queda ninguna fila sin nulos. "
                "Prueba --keep-rows-with-nulls o revisa columnas con muchos NA.",
                file=sys.stderr,
            )
    else:
        print("(Se conservan filas con nulos: --keep-rows-with-nulls)", flush=True)

    # Tope de edad (solo eda_export): reducir cola derecha / desviación típica de Edad.
    EDAD_MAX_INCLUSA = 67
    n_antes_tope_edad = len(df)
    if "Edad" in df.columns and not args.sin_tope_edad_67:
        mask_mayor_67 = df["Edad"].notna() & (df["Edad"] > EDAD_MAX_INCLUSA)
        n_edad_out = int(mask_mayor_67.sum())
        df = df.loc[~mask_mayor_67].copy()
        if n_antes_tope_edad > 0:
            pct_edad = 100.0 * n_edad_out / n_antes_tope_edad
        else:
            pct_edad = 0.0
        print(
            f"Filas con Edad > {EDAD_MAX_INCLUSA} eliminadas: {n_edad_out:,} "
            f"({pct_edad:.2f}% sobre las {n_antes_tope_edad:,} filas antes de este filtro). "
            f"Permanecen {len(df):,}.",
            flush=True,
        )
    elif "Edad" not in df.columns:
        print("(Sin columna Edad: se omite tope de 67 años)", flush=True)
    elif args.sin_tope_edad_67:
        print("(Se conservan todas las edades: --sin-tope-edad-67)", flush=True)

    print(f"Dimensiones listas para análisis/export: {df.shape[0]:,} × {df.shape[1]}")

    if not args.keep_rows_with_nulls and not args.sin_tope_edad_67 and "Edad" in df.columns:
        lab2b = "depurado (sin NA; Edad≤67)"
    elif args.keep_rows_with_nulls and not args.sin_tope_edad_67 and "Edad" in df.columns:
        lab2b = "depurado (con posibles NA; Edad≤67)"
    elif not args.keep_rows_with_nulls:
        lab2b = "depurado (solo filas sin NA)"
    else:
        lab2b = "depurado"
    print(f"\n=== 2b) Estructura y nulos ({lab2b}) ===")
    _print_info(df, label=lab2b)
    _null_table(df, label=lab2b)
    print("\n--- Resumen exploratorio (depurado) ---")
    mede.imprimir_resumen_exploratorio(df, top_k=10)

    if not args.skip_plots:
        print("\n=== 3) Figuras (para atípicos y nulos) ===")
        fig_dir = args.figures_dir.resolve()
        fig_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        p1 = fig_dir / "01_nulos_pct.png"
        _figure_nulos(df, p1)
        if p1.is_file():
            paths.append(p1)
        p2 = fig_dir / "02_edad.png"
        _figure_edad(df, p2)
        if p2.is_file():
            paths.append(p2)
        p3 = fig_dir / "03_coordenadas.png"
        _figure_mapa(df, p3)
        if p3.is_file():
            paths.append(p3)
        p4 = fig_dir / "04_categorias.png"
        _figure_categorias(df, p4)
        if p4.is_file():
            paths.append(p4)
        p5 = fig_dir / "05_edad_por_anio.png"
        _figure_edad_anio(df, p5)
        if p5.is_file():
            paths.append(p5)
        if paths:
            print("Figuras guardadas:")
            for p in paths:
                print(" ", p)
        else:
            print("(Sin figuras: sin datos para nulos/edad/coords/categorías)")
        if args.show and paths:
            for p in paths:
                img = plt.imread(p)
                plt.figure(figsize=(10, 6))
                plt.imshow(img)
                plt.axis("off")
                plt.title(p.name)
            plt.show()

    print("\n=== 4) Export .xlsx depurado ===")
    out = args.output.resolve()
    mede.guardar_mede(df, out)
    print(f"Guardado: {out}  ({len(df):,} filas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
