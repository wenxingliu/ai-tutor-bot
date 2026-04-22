from __future__ import annotations

import logging

from opentelemetry import trace

from app.config import settings


LOGGER = logging.getLogger(__name__)
TRACER = trace.get_tracer("ai_tutor_bot")
_TRACING_INITIALIZED = False


def configure_tracing() -> None:
    global _TRACING_INITIALIZED

    if _TRACING_INITIALIZED or not settings.phoenix_enable_tracing:
        return
    if not settings.phoenix_collector_endpoint:
        LOGGER.warning("Phoenix tracing requested but PHOENIX_COLLECTOR_ENDPOINT is not set; tracing disabled.")
        return

    from phoenix.otel import register

    register(
        project_name=settings.phoenix_project_name,
        endpoint=settings.phoenix_collector_endpoint,
        auto_instrument=True,
    )
    _TRACING_INITIALIZED = True
    LOGGER.info(
        "Phoenix tracing enabled for project=%s endpoint=%s",
        settings.phoenix_project_name,
        settings.phoenix_collector_endpoint,
    )
