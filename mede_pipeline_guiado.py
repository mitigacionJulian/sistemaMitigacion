# -*- coding: utf-8 -*-
"""
Orquestador del flujo Mede (sin modificar mede_limpieza.py ni mede_eda_export.py).

Ejecuta **pasos nombrados** en el orden indicado, con opción de **pausa** entre pasos
para revisar consola o archivos, **checkpoints** en Parquet y **reanudación** desde un
checkpoint si quieres ajustar datos fuera de este script y volver a filtrar/exportar.

Pasos disponibles (ver --list-steps):
  load            Carga el .xlsx (mede_limpieza.load_mede_xlsx)
  analyze_raw     Análisis en consola del crudo (analizar + resumen exploratorio)
  depurar         Reglas de limpieza (depurar_mede)
  analyze_clean   Análisis en consola tras depurar
  validate_coords Resumen F2.2 de coordenadas (rango Medellín, alineado a PostGIS)
  filter          Filtros opcionales: quitar filas con NA y tope Edad<=67 (como mede_eda_export)
  figures         PNG de apoyo (reutiliza funciones internas de mede_eda_export; requiere matplotlib)
  export_xlsx     Guarda .xlsx listo para revisión o para convertir a CSV
  export_csv      CSV UTF-8 con BOM (columna Año -> Anio) alineado a carga_mede_pgadmin.sql
  sql_help        Imprime recordatorio de import a mede_stg y ejecución del SQL

Ejemplos (desde la raíz del repositorio):
  pip install -r requirements-etl.txt

  python mede_pipeline_guiado.py --list-steps

  # Flujo completo típico, pausando entre pasos:
  python mede_pipeline_guiado.py --input Mede_Victimas_inci.xlsx --pause \\
      --checkpoint-dir salida/pipeline_run

  # Checkpoints Parquet: pip install pyarrow

  # Solo carga y análisis crudo (decides luego si continúas):
  python mede_pipeline_guiado.py --steps load,analyze_raw --checkpoint-dir salida/pipeline_run

  # Sin quitar filas con NA ni tope de edad (misma semántica que flags de mede_eda_export):
  python mede_pipeline_guiado.py --keep-rows-with-nulls --sin-tope-edad-67

  # Reanudar desde checkpoint tras depurar (p. ej. editaste el parquet con cuidado):
  python mede_pipeline_guiado.py \\
      --start-from salida/pipeline_run/checkpoint_02_depurado.parquet \\
      --steps analyze_clean,filter,export_xlsx,export_csv,sql_help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Orden canónico si usas --steps all
STEP_ORDER = (
    "load",
    "analyze_raw",
    "depurar",
    "analyze_clean",
    "validate_coords",
    "filter",
    "figures",
    "export_xlsx",
    "export_csv",
    "sql_help",
)

ALL_STEPS = ",".join(STEP_ORDER)


def _pause(msg: str, enabled: bool) -> None:
    if not enabled:
        return
    print(f"\n[Pausa] {msg}", flush=True)
    try:
        input("Enter = continuar  |  Ctrl+C = abortar\n")
    except EOFError:
        print("(sin TTY: se continúa automáticamente)", flush=True)


def _ensure_openpyxl() -> None:
    try:
        import openpyxl  # noqa: F401
    except ImportError as e:
        raise SystemExit(
            "Falta openpyxl. Ejecuta: pip install -r requirements-etl.txt"
        ) from e


def _rename_anio_for_sql(df):
    mapping = {}
    for c in df.columns:
        if c in ("Año", "A\u00f1o", "Ano"):
            mapping[c] = "Anio"
    if mapping:
        return df.rename(columns=mapping)
    return df


def _apply_filter(df, *, keep_rows_with_nulls: bool, sin_tope_edad_67: bool):
    """Replica la lógica de filas de mede_eda_export.py (post depurar_mede)."""
    import pandas as pd

    work = df.copy()
    n_tras_depurar = len(work)
    if not keep_rows_with_nulls:
        work = work.dropna(how="any")
        quitadas = n_tras_depurar - len(work)
        if n_tras_depurar > 0:
            pct_elim = 100.0 * quitadas / n_tras_depurar
            print(
                f"Filas con al menos un NA eliminadas: {quitadas:,} "
                f"({pct_elim:.2f}% sobre {n_tras_depurar:,} filas). "
                f"Permanecen {len(work):,}.",
                flush=True,
            )
        if len(work) == 0:
            print(
                "Advertencia: no queda ninguna fila sin nulos. "
                "Usa --keep-rows-with-nulls o revisa NA.",
                file=sys.stderr,
            )
    else:
        print("(Se conservan filas con nulos: --keep-rows-with-nulls)", flush=True)

    EDAD_MAX_INCLUSA = 67
    n_antes = len(work)
    if "Edad" in work.columns and not sin_tope_edad_67:
        mask_mayor = work["Edad"].notna() & (work["Edad"] > EDAD_MAX_INCLUSA)
        n_out = int(mask_mayor.sum())
        work = work.loc[~mask_mayor].copy()
        if n_antes > 0:
            pct = 100.0 * n_out / n_antes
            print(
                f"Filas con Edad > {EDAD_MAX_INCLUSA} eliminadas: {n_out:,} "
                f"({pct:.2f}% sobre {n_antes:,}). Permanecen {len(work):,}.",
                flush=True,
            )
    elif "Edad" not in work.columns:
        print("(Sin columna Edad: se omite tope 67)", flush=True)
    elif sin_tope_edad_67:
        print("(Se conservan todas las edades: --sin-tope-edad-67)", flush=True)

    return work


def _run_figures(df: "pd.DataFrame", fig_dir: Path, *, show: bool) -> None:
    import matplotlib

    matplotlib.use("TkAgg" if show else "Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Depende de mede_eda_export (mismo repo); no modifica ese archivo.
    import mede_eda_export as eda

    sns.set_theme(style="whitegrid", context="talk")
    fig_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, fn in (
        ("01_nulos_pct.png", eda._figure_nulos),
        ("02_edad.png", eda._figure_edad),
        ("03_coordenadas.png", eda._figure_mapa),
        ("04_categorias.png", eda._figure_categorias),
        ("05_edad_por_anio.png", eda._figure_edad_anio),
    ):
        p = fig_dir / name
        fn(df, p)
        if p.is_file():
            paths.append(p)
    if paths:
        print("Figuras guardadas:", flush=True)
        for p in paths:
            print(" ", p, flush=True)
    if show and paths:
        for p in paths:
            img = plt.imread(p)
            plt.figure(figsize=(10, 6))
            plt.imshow(img)
            plt.axis("off")
            plt.title(p.name)
        plt.show()


def _write_checkpoint(path: Path, df) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(path, index=False)
        print(f"Checkpoint: {path.resolve()}  ({len(df):,} filas)", flush=True)
    except ImportError as e:
        raise SystemExit(
            "Para checkpoints Parquet instala pyarrow: pip install pyarrow"
        ) from e


def _read_checkpoint(path: Path):
    import pandas as pd

    if not path.is_file():
        raise SystemExit(f"No existe el checkpoint: {path}")
    return pd.read_parquet(path)


def _print_sql_help(*, csv_path: Path) -> None:
    csv_abs = csv_path.resolve()
    print(
        "\n=== Siguiente paso: PostgreSQL / pgAdmin ===\n"
        "1) En pgAdmin, importa el CSV a la tabla public.mede_stg (UTF8, delimitador coma, cabecera).\n"
        f"   Archivo sugerido: {csv_abs}\n"
        "2) Ejecuta el script carga_mede_pgadmin.sql completo (es idempotente).\n"
        "   Requiere que el esquema base ya exista (docs/esquema_base_datos.sql o equivalente).\n",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    import pandas as pd

    parser = argparse.ArgumentParser(
        description="Pipeline Mede por pasos controlados (orquestador).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--list-steps",
        action="store_true",
        help="Lista pasos en orden y sale.",
    )
    parser.add_argument(
        "--steps",
        type=str,
        default=ALL_STEPS,
        help=f"Lista separada por comas o 'all'. Por defecto: todos. Orden: {ALL_STEPS}",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "Mede_Victimas_inci.xlsx",
        help="Ruta al .xlsx de entrada (paso load)",
    )
    parser.add_argument(
        "--start-from",
        type=Path,
        default=None,
        help="Parquet intermedio: salta load/analyze_raw/depurar y usa este DataFrame "
        "como 'tras depurar' (checkpoint_02_depurado.parquet recomendado).",
    )
    parser.add_argument(
        "--output-xlsx",
        type=Path,
        default=ROOT / "salida" / "Mede_Victimas_inci_depurado.xlsx",
        help="Salida del paso export_xlsx",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=ROOT / "salida" / "Mede_Victimas_inci_depurado.csv",
        help="Salida del paso export_csv (UTF-8-sig, Anio)",
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=ROOT / "salida" / "mede_eda_figuras",
        help="Carpeta PNG para el paso figures",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=None,
        help="Si se indica, escribe checkpoint_01_raw.parquet, checkpoint_02_depurado.parquet, "
        "checkpoint_03_filtrado.parquet al completar los pasos correspondientes.",
    )
    parser.add_argument(
        "--pause",
        action="store_true",
        help="Tras cada paso ejecutado, espera Enter antes de continuar.",
    )
    parser.add_argument(
        "--keep-rows-with-nulls",
        action="store_true",
        help="En paso filter: no eliminar filas con NA (como mede_eda_export --keep-rows-with-nulls).",
    )
    parser.add_argument(
        "--sin-tope-edad-67",
        action="store_true",
        help="En paso filter: no eliminar Edad > 67 (como mede_eda_export --sin-tope-edad-67).",
    )
    parser.add_argument(
        "--show-figures",
        action="store_true",
        help="Con paso figures: además de guardar PNG, abre ventanas matplotlib (TkAgg).",
    )
    args = parser.parse_args(argv)

    if args.list_steps:
        print("Pasos (orden recomendado):\n")
        for i, s in enumerate(STEP_ORDER, 1):
            print(f"  {i}. {s}")
        print("\nUso: --steps load,analyze_raw,...  o  --steps all")
        return 0

    raw_steps = args.steps.strip().lower()
    if raw_steps == "all":
        steps = list(STEP_ORDER)
    else:
        steps = [s.strip() for s in raw_steps.split(",") if s.strip()]
        unknown = [s for s in steps if s not in STEP_ORDER]
        if unknown:
            raise SystemExit(f"Pasos desconocidos: {unknown}. Usa --list-steps.")

    import mede_limpieza as mede

    df_raw: pd.DataFrame | None = None
    df_dep: pd.DataFrame | None = None
    df_final: pd.DataFrame | None = None

    if args.start_from is not None:
        sp = args.start_from.resolve()
        print(f"=== Reanudación desde Parquet ===\n{sp}", flush=True)
        df_dep = _read_checkpoint(sp)
        print(f"Filas cargadas: {len(df_dep):,} × {df_dep.shape[1]} columnas", flush=True)
        forbidden = {"load", "analyze_raw", "depurar"}
        bad = [s for s in steps if s in forbidden]
        if bad:
            raise SystemExit(
                f"Con --start-from no tiene sentido ejecutar: {bad}. "
                "Quita esos pasos de --steps."
            )

    ck = args.checkpoint_dir
    if ck is not None:
        ck = ck.resolve()
        print(f"Checkpoints en: {ck}", flush=True)

    for step in steps:
        print(f"\n{'=' * 60}\n>>> Paso: {step}\n{'=' * 60}", flush=True)

        if step == "load":
            if df_dep is not None and args.start_from is not None:
                print("(Omitido: datos vienen de --start-from)", flush=True)
                continue
            _ensure_openpyxl()
            inp = args.input.resolve()
            if not inp.is_file():
                print(f"No existe: {inp}", file=sys.stderr)
                return 1
            df_raw = mede.load_mede_xlsx(inp)
            print(f"Archivo: {inp}", flush=True)
            print(f"Dimensiones: {len(df_raw):,} × {df_raw.shape[1]}", flush=True)
            if ck is not None:
                _write_checkpoint(ck / "checkpoint_01_raw.parquet", df_raw)
            _pause("Revisa dimensiones. Siguiente: analyze_raw.", args.pause)

        elif step == "analyze_raw":
            if df_raw is None:
                if df_dep is not None:
                    print("analyze_raw requiere datos crudos; omite este paso o no uses --start-from.", file=sys.stderr)
                    return 1
                raise SystemExit("analyze_raw requiere el paso load antes.")
            print("--- analizar (crudo) ---", flush=True)
            mede.analizar(df_raw)
            print("\n--- imprimir_resumen_exploratorio (crudo) ---", flush=True)
            mede.imprimir_resumen_exploratorio(df_raw, top_k=10)
            _pause(
                "Revisa nulos y categorías. Ajusta política de filtros (--keep-rows-with-nulls, etc.) "
                "antes de depurar si hace falta.",
                args.pause,
            )

        elif step == "depurar":
            if df_dep is not None and args.start_from is not None:
                print("(Omitido: ya hay DataFrame desde --start-from)", flush=True)
                continue
            if df_raw is None:
                raise SystemExit("depurar requiere load antes (o usa --start-from).")
            print("--- depurar_mede ---", flush=True)
            df_dep = mede.depurar_mede(df_raw)
            print(f"Filas tras depurar_mede: {len(df_dep):,}", flush=True)
            if ck is not None:
                _write_checkpoint(ck / "checkpoint_02_depurado.parquet", df_dep)
            _pause(
                "Tras depurar. Puedes inspeccionar checkpoint_02_depurado.parquet, "
                "editar con cuidado (avanzado) y reanudar con --start-from.",
                args.pause,
            )

        elif step == "analyze_clean":
            if df_dep is None:
                raise SystemExit("analyze_clean requiere depurar o --start-from con checkpoint 02.")
            print("--- analizar (tras depurar_mede) ---", flush=True)
            mede.analizar(df_dep)
            print("\n--- imprimir_resumen_exploratorio (depurado) ---", flush=True)
            mede.imprimir_resumen_exploratorio(df_dep, top_k=10)
            _pause(
                "Decide si aplicas filter (dropna / tope edad) en el siguiente paso.",
                args.pause,
            )

        elif step == "validate_coords":
            if df_dep is None:
                raise SystemExit("validate_coords requiere depurar o --start-from con checkpoint 02.")
            mede.imprimir_resumen_coordenadas(df_dep)
            _pause(
                "Coordenadas fuera de rango no reciben ubicacion PostGIS; revisa antes de exportar.",
                args.pause,
            )

        elif step == "filter":
            if df_dep is None:
                raise SystemExit("filter requiere depurar o --start-from.")
            print("--- filtros post-depuración (estilo mede_eda_export) ---", flush=True)
            df_final = _apply_filter(
                df_dep,
                keep_rows_with_nulls=args.keep_rows_with_nulls,
                sin_tope_edad_67=args.sin_tope_edad_67,
            )
            print(f"Dimensiones listas para export: {len(df_final):,} × {df_final.shape[1]}", flush=True)
            if ck is not None:
                _write_checkpoint(ck / "checkpoint_03_filtrado.parquet", df_final)
            _pause("Listo para figuras y/o export.", args.pause)

        elif step == "figures":
            src = df_final if df_final is not None else df_dep
            if src is None:
                raise SystemExit("figures requiere filter o al menos depurar (o start-from + analyze).")
            _run_figures(src, args.figures_dir.resolve(), show=args.show_figures)
            _pause("Figuras generadas.", args.pause)

        elif step == "export_xlsx":
            src = df_final if df_final is not None else df_dep
            if src is None:
                raise SystemExit("export_xlsx requiere datos (filter, depurar o start-from).")
            out = args.output_xlsx.resolve()
            mede.guardar_mede(src, out)
            print(f"Guardado: {out}  ({len(src):,} filas)", flush=True)
            _pause("Puedes abrir el Excel para revisión manual.", args.pause)

        elif step == "export_csv":
            src = df_final if df_final is not None else df_dep
            if src is None:
                raise SystemExit("export_csv requiere datos.")
            out_csv = args.output_csv.resolve()
            out_csv.parent.mkdir(parents=True, exist_ok=True)
            df_csv = _rename_anio_for_sql(src.copy())
            df_csv.to_csv(out_csv, index=False, encoding="utf-8-sig")
            print(f"CSV UTF-8-sig: {out_csv}  ({len(df_csv):,} filas)", flush=True)
            _pause("CSV listo para importar a mede_stg.", args.pause)

        elif step == "sql_help":
            _print_sql_help(csv_path=args.output_csv.resolve())
            _pause("Fin del recordatorio SQL.", args.pause)

        else:
            raise SystemExit(f"Paso interno no manejado: {step}")

    print("\n=== Pipeline: pasos solicitados completados ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
