"""AI quiz generation mode: Celery (async) vs manual (admin-triggered sync)."""

from __future__ import annotations

from django.conf import settings

MODE_CELERY = "celery"
MODE_MANUAL = "manual"
VALID_MODES = frozenset({MODE_CELERY, MODE_MANUAL})


def get_ai_generation_mode() -> str:
    raw = str(getattr(settings, "AI_GENERATION_MODE", MODE_MANUAL)).strip().lower()
    return raw if raw in VALID_MODES else MODE_MANUAL


def is_celery_mode() -> bool:
    return get_ai_generation_mode() == MODE_CELERY


def is_manual_mode() -> bool:
    return get_ai_generation_mode() == MODE_MANUAL
