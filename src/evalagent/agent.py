from __future__ import annotations

from pathlib import Path

from pydantic_ai.workspaces import LocalWorkspaceBackend
from pydantic_ai_harness import FileSystem, Shell, Skills

from iagent.runtime import load_agent
from iagent.tracing import load_env, setup_tracing

SPEC_PATH = Path(__file__).with_name("agent.yaml")
REPO_ROOT = Path(__file__).resolve().parents[2]


def build_agent(**kwargs):
    """Construct the evalagent: reads a benchmark, writes a loader.

    FileSystem keeps dataset/ read-only and limits writes to workspace/.
    Shell can run python for the upload script and the experiment runner.
    dataset-upload and phoenix-runner live outside this agent's working
    directory. The spec says which step loads each skill.
    """
    extra = list(kwargs.pop("capabilities", None) or [])
    extra.append(
        Skills(
            "src/skills",
            include=["dataset-upload", "phoenix-runner"],
            workspace=LocalWorkspaceBackend(REPO_ROOT),
        )
    )
    return load_agent(
        SPEC_PATH,
        custom_capability_types=[FileSystem, Shell, Skills],
        capabilities=extra,
        **kwargs,
    )


def main() -> None:
    instruction = (
        "Onboard the benchmark under eval/dataset/toy. Inspect its layout, then "
        "write a loader at eval/loaders/toy/loader.py implementing load(root) and "
        "judge(work_dir, example). Report when it is ready for golden check and "
        "human approval. Do not pin it and do not run scoring."
    )
    load_env()
    setup_tracing(project_name="evalagent")
    agent = build_agent()
    result = agent.run_sync(instruction)
    print(result.output)


if __name__ == "__main__":
    main()
