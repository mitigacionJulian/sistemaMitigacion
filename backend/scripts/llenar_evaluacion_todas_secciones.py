"""
Regenera todos los CSV de evaluación del módulo Predicciones.

Uso (desde backend/):
  .venv\\Scripts\\python scripts/llenar_evaluacion_todas_secciones.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "llenar_evaluacion_seccion1.py",
    "llenar_evaluacion_seccion2.py",
    "llenar_evaluacion_seccion3.py",
    "llenar_evaluacion_seccion4.py",
    "llenar_evaluacion_seccion5.py",
    "llenar_evaluacion_tres_sigma.py",
]

POST_SCRIPT = "generar_matriz_escenarios_md.py"


def main():
    py = sys.executable
    for name in SCRIPTS:
        path = BACKEND / "scripts" / name
        print(f"\n=== {name} ===")
        rc = subprocess.call([py, str(path)], cwd=str(BACKEND))
        if rc != 0:
            raise SystemExit(rc)
    print(f"\n=== {POST_SCRIPT} ===")
    rc = subprocess.call([py, str(BACKEND / "scripts" / POST_SCRIPT)], cwd=str(BACKEND))
    if rc != 0:
        raise SystemExit(rc)
    print("\nTodos los CSV de evaluación y la matriz MD fueron regenerados.")


if __name__ == "__main__":
    main()
