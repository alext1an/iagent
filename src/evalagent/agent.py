from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pydantic_ai.workspaces import LocalWorkspaceBackend
from pydantic_ai_harness import FileSystem, Shell, Skills

from iagent.approval import command_approval_guardrail
from iagent.runtime import load_agent

SPEC_PATH = Path(__file__).with_name("agent.yaml")
REPO_ROOT = Path(__file__).resolve().parents[2]


def build_agent(*, approve_commands: bool = True, auto_approve: Sequence[str] = (), **kwargs):
    """Construct the evalagent: reads a benchmark, writes a loader.

    FileSystem keeps dataset/ read-only and limits writes to workspace/.
    Shell can run python for the upload script and the experiment runner.
    When ``approve_commands`` is True, each of those commands must be approved
    at the terminal before it runs. Commands in ``auto_approve`` skip that
    prompt. dataset-upload, phoenix-runner, and
    phoenix-eval live outside this agent's working directory. The spec says
    which step loads each skill.
    """
    extra = list(kwargs.pop("capabilities", None) or [])
    extra.append(
        Skills(
            "src/skills",
            include=["dataset-upload", "phoenix-runner", "phoenix-eval"],
            workspace=LocalWorkspaceBackend(REPO_ROOT),
        )
    )
    if approve_commands:
        extra.append(command_approval_guardrail(auto_approve=auto_approve))
    return load_agent(
        SPEC_PATH,
        custom_capability_types=[FileSystem, Shell, Skills],
        capabilities=extra,
        **kwargs,
    )