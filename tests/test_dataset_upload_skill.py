from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel
from pydantic_ai.workspaces import LocalWorkspaceBackend
from pydantic_ai_harness import Skills

REPO = Path(__file__).resolve().parents[1]


def test_eval_skills_load() -> None:
    skills = Skills(
        "src/skills",
        include=["dataset-upload", "phoenix-runner"],
        workspace=LocalWorkspaceBackend(REPO),
    )
    catalog = asyncio.run(skills.load())
    by_name = {skill.name: skill for skill in catalog.skills}
    assert set(by_name) == {"dataset-upload", "phoenix-runner"}
    upload = by_name["dataset-upload"].render()
    runner = by_name["phoenix-runner"].render()
    assert "create_dataset" in upload
    assert "python workspace/upload_dataset.py" in upload
    assert "run_experiment" in runner
    assert "loader.py" not in runner
    assert catalog.skipped == ()


@pytest.mark.skipif(
    os.name != "posix",
    reason="LocalWorkspace requires POSIX (use WSL/Linux for full agent load)",
)
def test_evalagent_builds_with_both_skills() -> None:
    from evalagent.agent import build_agent

    agent = build_agent(model=TestModel(custom_output_text="ok", call_tools=[]))
    result = agent.run_sync("hello")
    assert result.output == "ok"
