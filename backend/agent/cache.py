"""Caché de respuestas del asistente (Django LocMem)."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from django.conf import settings
from django.core.cache import cache


def normalize_question(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def agent_response_cache_key(question: str, *, is_analista: bool = False) -> str:
    norm = normalize_question(question)
    scope = "analyst" if is_analista else "public"
    digest = hashlib.sha256(f"{scope}|{norm}".encode("utf-8")).hexdigest()[:32]
    return f"agent:resp:{scope}:{digest}"


def get_cached_agent_response(question: str, *, is_analista: bool = False) -> dict[str, Any] | None:
    ttl = int(getattr(settings, "AGENT_CACHE_TTL", 0))
    if ttl <= 0:
        return None
    return cache.get(agent_response_cache_key(question, is_analista=is_analista))


def set_cached_agent_response(
    question: str, payload: dict[str, Any], *, is_analista: bool = False
) -> None:
    ttl = int(getattr(settings, "AGENT_CACHE_TTL", 0))
    if ttl <= 0:
        return
    cache.set(agent_response_cache_key(question, is_analista=is_analista), payload, ttl)


def _client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def check_daily_ip_limit(request) -> tuple[bool, int, int]:
    """Devuelve (permitido, usado, límite)."""
    limit = int(getattr(settings, "AGENT_DAILY_LIMIT_PER_IP", 0))
    if limit <= 0:
        return True, 0, 0
    ip = _client_ip(request)
    from datetime import date

    key = f"agent:ip:{ip}:{date.today().isoformat()}"
    used = int(cache.get(key) or 0)
    return used < limit, used, limit


def increment_daily_ip_limit(request) -> None:
    limit = int(getattr(settings, "AGENT_DAILY_LIMIT_PER_IP", 0))
    if limit <= 0:
        return
    ip = _client_ip(request)
    from datetime import date

    key = f"agent:ip:{ip}:{date.today().isoformat()}"
    used = int(cache.get(key) or 0)
    cache.set(key, used + 1, 60 * 60 * 26)
