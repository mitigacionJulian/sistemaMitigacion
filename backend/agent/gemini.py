"""Cliente mínimo para Gemini API (generateContent + function calling)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings


class GeminiRateLimitError(Exception):
    def __init__(self, model: str, detail: str = ""):
        self.model = model
        super().__init__(detail or f"Límite de cuota alcanzado para {model}")


class GeminiError(Exception):
    pass


def _api_key() -> str:
    key = getattr(settings, "GEMINI_API_KEY", "") or ""
    if not key:
        raise GeminiError(
            "GEMINI_API_KEY no configurada. Defínala en el archivo .env de la raíz del proyecto."
        )
    return key


def model_id(preference: str) -> str:
    pref = (preference or "flash").strip().lower()
    if pref in ("flash-lite", "lite", "flash_lite"):
        return getattr(settings, "AGENT_MODEL_FLASH_LITE", "gemini-2.5-flash-lite")
    return getattr(settings, "AGENT_MODEL_FLASH", "gemini-2.5-flash")


def alternate_model_id(preference: str) -> str:
    pref = (preference or "flash").strip().lower()
    if pref in ("flash-lite", "lite", "flash_lite"):
        return getattr(settings, "AGENT_MODEL_FLASH", "gemini-2.5-flash")
    return getattr(settings, "AGENT_MODEL_FLASH_LITE", "gemini-2.5-flash-lite")


def generate_content(
    *,
    model: str,
    contents: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    system_instruction: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"contents": contents}
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if tools:
        body["tools"] = [{"functionDeclarations": tools}]
        body["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={_api_key()}"
    )
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429:
            raise GeminiRateLimitError(model, detail) from exc
        raise GeminiError(f"Gemini HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise GeminiError(f"No se pudo contactar Gemini: {exc}") from exc


def extract_text(response: dict[str, Any]) -> str | None:
    for cand in response.get("candidates") or []:
        content = cand.get("content") or {}
        parts = content.get("parts") or []
        texts = [p["text"] for p in parts if isinstance(p, dict) and p.get("text")]
        if texts:
            return "\n".join(texts)
    return None


def extract_function_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for cand in response.get("candidates") or []:
        content = cand.get("content") or {}
        for part in content.get("parts") or []:
            if isinstance(part, dict) and "functionCall" in part:
                fc = part["functionCall"]
                calls.append({"name": fc.get("name"), "args": fc.get("args") or {}})
    return calls


def model_response_part(response: dict[str, Any]) -> dict[str, Any] | None:
    for cand in response.get("candidates") or []:
        content = cand.get("content")
        if content:
            return content
    return None
