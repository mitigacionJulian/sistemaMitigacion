#!/usr/bin/env python
"""Wrapper: ejecuta manage.py cargar_poligonos_medellin desde la raiz del repo."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PY = BACKEND / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

cmd = [str(PY), str(BACKEND / "manage.py"), "cargar_poligonos_medellin", *sys.argv[1:]]
raise SystemExit(subprocess.call(cmd, cwd=str(BACKEND)))
