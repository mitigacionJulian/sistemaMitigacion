"""Normalización de teléfonos móviles Colombia (+57)."""
from __future__ import annotations

import re

from rest_framework.exceptions import ValidationError


def normalize_phone_co(raw: str) -> str:
    """
    Devuelve dígitos 57 + 10 dígitos (ej. 573001234567).
    Acepta 3001234567, +57 300..., 573001234567.
    """
    digits = re.sub(r"\D", "", (raw or "").strip())
    if not digits:
        raise ValidationError("Indique un número de celular.")
    if digits.startswith("57") and len(digits) >= 12:
        digits = digits[:12]
    elif len(digits) == 10 and digits[0] == "3":
        digits = "57" + digits
    elif len(digits) != 12 or not digits.startswith("57"):
        raise ValidationError(
            "Use un celular colombiano de 10 dígitos (ej. 300 123 4567)."
        )
    if digits[2] != "3":
        raise ValidationError("El celular debe comenzar por 3 después del +57.")
    return digits


def format_phone_display(normalized: str) -> str:
    if len(normalized) == 12 and normalized.startswith("57"):
        return f"+57 {normalized[2:5]} {normalized[5:8]} {normalized[8:]}"
    return f"+{normalized}"


def build_whatsapp_url(phone_normalized: str, message: str) -> str:
    from urllib.parse import quote

    return f"https://wa.me/{phone_normalized}?text={quote(message, safe='')}"
