from __future__ import annotations

from pathlib import Path

from pydantic_ai_harness import FileSystem

from iagent.runtime import load_agent
from iagent.tracing import load_env, setup_tracing

SPEC_PATH = Path(__file__).with_name("agent.yaml")


def build_agent(**kwargs):
    """Construct the evalagent: reads a benchmark, writes a loader.

    It mounts FileSystem (bounded file access) but NOT Shell or Spreadsheet -- it
    never solves tasks and never executes scoring. The dataset tree is read-only;
    the loader is written to the approval area, then golden-checked and human
    approved before the deterministic runner ever imports it.
    """
    return load_agent(
        SPEC_PATH,
        custom_capability_types=[FileSystem],
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
