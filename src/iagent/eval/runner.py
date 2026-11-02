"""run_runner -- the deterministic evaluation loop.

Fixed sequence, no DAG, no planner: verify pin -> load -> for each example copy
files into an isolated work dir -> run the agent -> judge -> append verdict to
the run record. Verdicts come from the loader's judge, never from model prose.

The agent under test is passed in as ``run_agent`` so this module never imports
sheetagent (or any domain agent) -- that keeps iagent neutral.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Callable

from opentelemetry import trace

from iagent.eval.loader import load_loader_module, sha256_file
from iagent.eval.types import Example, Verdict
from iagent.eval.workdir import prepare_work_dir

tracer = trace.get_tracer("iagent")

RunAgent = Callable[[Path, Example], None]
"""Run the agent under test inside ``work_dir`` for one example (mutates files)."""


def run_runner(
    *,
    key: str,
    dataset_root: Path,
    loader_path: Path,
    pins_path: Path,
    run_agent: RunAgent,
    runs_dir: Path,
) -> Path:
    """Evaluate every example in a loader's dataset; return the record.json path."""
    dataset_root = Path(dataset_root)
    runs_dir = Path(runs_dir)

    run_id = uuid.uuid4().hex[:12]
    loader_hash = sha256_file(loader_path)
    module = load_loader_module(loader_path, pins_path, key)  # raises if unpinned/altered
    examples = module.load(dataset_root)

    run_path = runs_dir / run_id
    (run_path / "work").mkdir(parents=True, exist_ok=True)
    record: dict = {
        "run_id": run_id,
        "loader_key": key,
        "loader_hash": loader_hash,
        "dataset_root": str(dataset_root),
        "verdicts": [],
    }

    with tracer.start_as_current_span("iagent.eval") as eval_span:
        eval_span.set_attribute("iagent.run_id", run_id)
        eval_span.set_attribute("iagent.loader_key", key)
        eval_span.set_attribute("iagent.example_count", len(examples))

        for example in examples:
            work = prepare_work_dir(run_path / "work", example, dataset_root)
            with tracer.start_as_current_span("iagent.run") as run_span:
                run_span.set_attribute("iagent.run_id", run_id)
                run_span.set_attribute("iagent.example_id", example.id)
                run_agent(work, example)
                verdict: Verdict = module.judge(work, example)
                run_span.set_attribute("iagent.passed", verdict.passed)
            record["verdicts"].append(verdict.model_dump(mode="json"))

    (run_path / "record.json").write_text(
        json.dumps(record, indent=2, default=str), encoding="utf-8"
    )
    return run_path / "record.json"
