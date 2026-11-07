---
name: phoenix-runner
description: Write a Phoenix experiment script for an agent and a dataset that was already uploaded. Use after the human names the agent and confirms the dataset fields.
---

# Write the Phoenix experiment runner

Follow this skill only after the human has answered which agent to run and has confirmed the dataset name and fields. Those answers must match `workspace/upload_dataset.py`. Do not invent a second schema. Do not modify `dataset/`. This script is not the upload script.

The shell working directory is `eval/`. Write `workspace/run_eval.py` and stop. Do not run it. The evaluator is attached by a later step.

`Client()` reads `PHOENIX_ENDPOINT` or `PHOENIX_COLLECTOR_ENDPOINT`, and `PHOENIX_API_KEY` when the server requires one. Do not write keys into the script.

`get_dataset(dataset=...)` takes the same Phoenix name the upload script used. `run_experiment` calls `task` once per example. A one-argument `task` receives that example's `input`. The task must not read `expected`; `expected` is the hidden answer stored in the example's `output` field.

The task copies only `input["files"]` into `workspace/runs/<id>/`. Paths are relative to `metadata["dataset_root"]`, the same value the upload script stored. It then calls the agent the human named, with `input["instruction"]` and that work directory. Return only the task output the human named. Do not default the return to the work directory, to a file inside it, or to any other path. If the human did not name the return value, stop and ask before writing it.

Import that agent through the `build_agent` the human gave you, for example `sheetagent.agent`. Construct it once. A Phoenix experiment has no terminal, so pass `approve_commands=False`. The default asks `approve? [y/N]` on stdin and the run dies with `EOFError`.

Pass `timeout=600` and `retries=0`. Phoenix's default timeout is 60 seconds and then it retries the task; one agent run does not finish in 60 seconds. Leave `dry_run=1`. Do not add `evaluators` here.

```python
"""Phoenix experiment for one uploaded dataset. The shell working directory is eval/."""

from pathlib import Path

from phoenix.client import Client
from sheetagent.agent import build_agent

DATASET_NAME = "visualization"  # same name as workspace/upload_dataset.py
RUNS = Path("workspace/runs")
agent = build_agent(approve_commands=False)


def task(input, metadata):
    root = Path(metadata["dataset_root"])
    work = RUNS / str(input["id"])
    work.mkdir(parents=True, exist_ok=True)
    for rel in input.get("files", []):
        src = root / rel
        (work / Path(rel).name).write_bytes(src.read_bytes())
    result = agent.run_sync(
        f"{input['instruction']}\nThe task files are in {work.as_posix()}."
    )
    return result  # replace with the task output the human named


def main() -> None:
    client = Client()
    dataset = client.datasets.get_dataset(dataset=DATASET_NAME)
    client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        experiment_name=f"{DATASET_NAME}-agent",
        dry_run=1,
        timeout=600,
        retries=0,
    )


if __name__ == "__main__":
    main()
```

Replace `sheetagent.agent` and `DATASET_NAME` with the human's answers. Keep every input and output field name identical to the upload script.
