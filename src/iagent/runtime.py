from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models import Model


def load_agent(
    spec_path: Path,
    *,
    model: Model | str | None = None,
) -> Agent:
    """Load any agent spec file. Callers choose the path; this package has no default agent."""
    return Agent.from_file(spec_path, model=model)
