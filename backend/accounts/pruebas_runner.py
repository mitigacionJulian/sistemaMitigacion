"""
Ejecución de pytest con salida Allure (JSON) para el panel de administración.

Los resultados en allure-results/ se leen en la UI y en el reporte imprimible.
No requiere Node.js ni Java.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings

_RUN_LOCK = threading.Lock()
_STATE_LOCK = threading.Lock()

ESTADO_IDLE = "idle"
ESTADO_RUNNING = "running"
ESTADO_DONE = "done"
ESTADO_ERROR = "error"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _backend_root() -> Path:
    return Path(settings.BASE_DIR)


def allure_results_dir() -> Path:
    return Path(getattr(settings, "ALLURE_RESULTS_DIR", _backend_root() / "allure-results"))


def state_file_path() -> Path:
    return Path(getattr(settings, "PRUEBAS_RUNNER_STATE_FILE", _backend_root() / ".pruebas_runner_state.json"))


def can_run_tests() -> bool:
    return bool(getattr(settings, "ALLOW_ADMIN_TEST_RUNNER", False))


def _default_state() -> dict[str, Any]:
    return {
        "estado": ESTADO_IDLE,
        "iniciado_en": None,
        "finalizado_en": None,
        "codigo_salida": None,
        "mensaje": None,
        "iniciado_por": None,
    }


def _read_state() -> dict[str, Any]:
    path = state_file_path()
    if not path.is_file():
        return _default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_state()
    merged = _default_state()
    merged.update({k: v for k, v in data.items() if k in merged})
    return merged


def _write_state(data: dict[str, Any]) -> None:
    path = state_file_path()
    with _STATE_LOCK:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _label_value(labels: list[dict[str, Any]] | None, name: str) -> str | None:
    if not labels:
        return None
    for item in labels:
        if item.get("name") == name:
            value = item.get("value")
            return str(value) if value is not None else None
    return None


def _parse_duration_ms(start: int | float | None, stop: int | float | None) -> int | None:
    if start is None or stop is None:
        return None
    try:
        return max(0, int(stop) - int(start))
    except (TypeError, ValueError):
        return None


def _empty_summary() -> dict[str, Any]:
    return {
        "hay_resultados": False,
        "total": 0,
        "pasaron": 0,
        "fallaron": 0,
        "rotos": 0,
        "omitidos": 0,
        "duracion_ms": 0,
        "por_epic": [],
        "fallos": [],
        "casos": [],
        "ultima_modificacion": None,
    }


def parse_allure_summary(results_dir: Path | None = None) -> dict[str, Any]:
    """Resume los archivos *-result.json generados por allure-pytest."""
    directory = results_dir or allure_results_dir()
    if not directory.is_dir():
        return _empty_summary()

    result_files = sorted(directory.glob("*-result.json"))
    if not result_files:
        return _empty_summary()

    counts = {"passed": 0, "failed": 0, "broken": 0, "skipped": 0}
    epic_stats: dict[str, dict[str, int]] = {}
    failures: list[dict[str, Any]] = []
    casos: list[dict[str, Any]] = []
    total_duration = 0
    latest_mtime: float | None = None

    for file_path in result_files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        mtime = file_path.stat().st_mtime
        if latest_mtime is None or mtime > latest_mtime:
            latest_mtime = mtime

        status = str(payload.get("status") or "unknown").lower()
        if status in counts:
            counts[status] += 1

        duration = _parse_duration_ms(payload.get("start"), payload.get("stop"))
        if duration is not None:
            total_duration += duration

        labels = payload.get("labels") or []
        epic = _label_value(labels, "epic") or _label_value(labels, "parentSuite") or "Sin módulo"
        feature = _label_value(labels, "feature") or _label_value(labels, "suite") or "—"
        categoria = _label_value(labels, "categoria") or "—"
        nombre = payload.get("name") or payload.get("fullName") or file_path.stem
        mensaje_error = (payload.get("statusDetails") or {}).get("message")

        bucket = epic_stats.setdefault(
            epic,
            {"epic": epic, "total": 0, "pasaron": 0, "fallaron": 0, "rotos": 0, "omitidos": 0},
        )
        bucket["total"] += 1
        if status == "passed":
            bucket["pasaron"] += 1
        elif status == "failed":
            bucket["fallaron"] += 1
        elif status == "broken":
            bucket["rotos"] += 1
        elif status == "skipped":
            bucket["omitidos"] += 1

        casos.append(
            {
                "nombre": nombre,
                "estado": status,
                "epic": epic,
                "feature": feature,
                "categoria": categoria,
                "duracion_ms": duration,
                "mensaje": mensaje_error if status in ("failed", "broken") else None,
            }
        )

        if status in ("failed", "broken"):
            failures.append(
                {
                    "nombre": nombre,
                    "estado": status,
                    "epic": epic,
                    "feature": feature,
                    "mensaje": mensaje_error,
                }
            )

    por_epic = sorted(epic_stats.values(), key=lambda row: (-row["total"], row["epic"]))
    failures.sort(key=lambda row: (row["epic"], row["feature"], row["nombre"]))
    casos.sort(key=lambda row: (row["epic"], row["feature"], row["nombre"]))

    ultima_modificacion = None
    if latest_mtime is not None:
        ultima_modificacion = datetime.fromtimestamp(latest_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()

    return {
        "hay_resultados": True,
        "total": sum(counts.values()),
        "pasaron": counts["passed"],
        "fallaron": counts["failed"],
        "rotos": counts["broken"],
        "omitidos": counts["skipped"],
        "duracion_ms": total_duration,
        "por_epic": por_epic,
        "fallos": failures,
        "casos": casos,
        "ultima_modificacion": ultima_modificacion,
    }


def _run_pytest_allure() -> None:
    results_dir = allure_results_dir()
    results_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        f"--alluredir={results_dir}",
        "--clean-alluredir",
        "-q",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=_backend_root(),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        exit_code = proc.returncode
        mensaje = proc.stderr.strip()[:500] if proc.stderr else None
    except subprocess.TimeoutExpired:
        exit_code = -1
        mensaje = "La ejecución de pytest superó el tiempo límite (10 min)."
    except OSError as exc:
        exit_code = -1
        mensaje = f"No se pudo ejecutar pytest: {exc}"

    state = _read_state()
    state.update(
        {
            "estado": ESTADO_DONE if exit_code == 0 else ESTADO_ERROR,
            "finalizado_en": _utc_now_iso(),
            "codigo_salida": exit_code,
            "mensaje": mensaje,
        }
    )
    _write_state(state)


def start_test_run(username: str | None = None) -> tuple[bool, str, dict[str, Any]]:
    """Inicia pytest en un hilo de fondo."""
    if not can_run_tests():
        return False, "La ejecución desde la UI está deshabilitada en este entorno.", _read_state()

    if not _RUN_LOCK.acquire(blocking=False):
        state = _read_state()
        return False, "Ya hay una ejecución de pruebas en curso.", state

    state = {
        **_default_state(),
        "estado": ESTADO_RUNNING,
        "iniciado_en": _utc_now_iso(),
        "iniciado_por": username,
    }
    _write_state(state)

    thread = threading.Thread(target=_run_pytest_worker, name="admin-pruebas-runner", daemon=True)
    thread.start()
    return True, "Ejecución iniciada.", state


def _run_pytest_worker() -> None:
    try:
        _run_pytest_allure()
    except Exception as exc:  # noqa: BLE001
        state = _read_state()
        state.update(
            {
                "estado": ESTADO_ERROR,
                "finalizado_en": _utc_now_iso(),
                "codigo_salida": -1,
                "mensaje": f"Error inesperado del runner: {exc}",
            }
        )
        _write_state(state)
    finally:
        _RUN_LOCK.release()


def build_status_payload() -> dict[str, Any]:
    state = _read_state()
    summary = parse_allure_summary()
    return {
        "puede_ejecutar": can_run_tests(),
        "ejecutando": state.get("estado") == ESTADO_RUNNING,
        "estado": state.get("estado"),
        "iniciado_en": state.get("iniciado_en"),
        "finalizado_en": state.get("finalizado_en"),
        "codigo_salida": state.get("codigo_salida"),
        "mensaje": state.get("mensaje"),
        "iniciado_por": state.get("iniciado_por"),
        "resumen": summary,
    }
