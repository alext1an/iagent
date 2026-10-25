from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_env() -> None:
    load_dotenv(repo_root() / ".env")


def phoenix_otlp_endpoint(raw: str | None = None) -> str | None:
    """Return a full OTLP HTTP traces URL, or None to let phoenix.otel defaults apply."""
    value = (raw if raw is not None else os.getenv("PHOENIX_COLLECTOR_ENDPOINT")) or ""
    value = value.strip().rstrip("/")
    if not value:
        return None
    if not value.endswith("/v1/traces"):
        value = f"{value}/v1/traces"
    return value


def setup_tracing(*, project_name: str | None = None, batch: bool = False):
    """Register Phoenix OTEL export plus the Pydantic AI OpenInference reshaper."""
    from openinference.instrumentation.pydantic_ai import OpenInferenceSpanProcessor
    from phoenix.otel import register

    load_env()
    project = project_name or os.getenv("PHOENIX_PROJECT") or "default"
    tracer_provider = register(
        project_name=project,
        endpoint=phoenix_otlp_endpoint(),
        batch=batch,
    )
    tracer_provider.add_span_processor(
        OpenInferenceSpanProcessor(),
        replace_default_processor=False,
    )
    return tracer_provider
