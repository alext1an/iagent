"""Tests for iagent.eval -- safety invariants first.

The four invariants that must stay red if broken:
  1. judge_input never present in the work dir
  2. unapproved / altered loader hash is rejected before import
  3. (loaders own script policy / commit guardrails -- covered elsewhere)
  4. verdict comes from judge, not model prose (structural: run_agent cannot
     produce a Verdict; only the loader's judge can)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from iagent.eval.loader import (
    LoaderHashMismatch,
    LoaderNotApproved,
    load_loader_module,
    sha256_file,
)
from iagent.eval.runner import run_runner
from iagent.eval.types import Example, Verdict
from iagent.eval.workdir import WorkDirViolation, prepare_work_dir

LOADER_SRC = '''
from pathlib import Path
from iagent.eval.types import Example, Verdict

def load(root):
    return [Example(id="c1", instruction="double B1 into C1",
                    files=[Path("input.xlsx")],
                    judge_input={"answer": "secret-42"})]

def judge(work_dir, example):
    from openpyxl import load_workbook
    ws = load_workbook(work_dir / "input.xlsx", data_only=True).active
    ok = ws["C1"].value == ws["B1"].value * 2
    return Verdict(example_id=example.id, passed=ok,
                   failures=[] if ok else ["C1 wrong"])
'''


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    root.mkdir()
    wb = Workbook()
    ws = wb.active
    ws["A1"], ws["B1"] = "value", 10
    wb.save(root / "input.xlsx")
    return root


@pytest.fixture
def pinned_loader(tmp_path: Path) -> tuple[Path, Path, str]:
    loader = tmp_path / "loader.py"
    loader.write_text(LOADER_SRC, encoding="utf-8")
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"loaders": {"toy": sha256_file(loader)}}), encoding="utf-8")
    return loader, pins, "toy"


def _good_agent(work_dir: Path, example: Example) -> None:
    wb = load_workbook(work_dir / "input.xlsx")
    ws = wb.active
    ws["C1"] = ws["B1"].value * 2
    wb.save(work_dir / "input.xlsx")


# ---- invariant 1: judge_input never reaches the work dir --------------------

def test_judge_input_never_in_work_dir(dataset: Path, tmp_path: Path) -> None:
    ex = Example(id="c1", instruction="x", files=[Path("input.xlsx")],
                 judge_input={"answer": "secret-42"})
    work = prepare_work_dir(tmp_path / "work", ex, dataset)
    names = [p.name for p in work.iterdir()]
    assert names == ["input.xlsx"]
    blob = b"".join(p.read_bytes() for p in work.iterdir())
    assert b"secret-42" not in blob


def test_workdir_rejects_path_escape(dataset: Path, tmp_path: Path) -> None:
    ex = Example(id="c1", instruction="x", files=[Path("../outside.xlsx")])
    with pytest.raises(WorkDirViolation):
        prepare_work_dir(tmp_path / "work", ex, dataset)


# ---- invariant 2: unapproved / altered loader rejected ----------------------

def test_unpinned_loader_rejected(tmp_path: Path) -> None:
    loader = tmp_path / "loader.py"
    loader.write_text(LOADER_SRC, encoding="utf-8")
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"loaders": {}}), encoding="utf-8")
    with pytest.raises(LoaderNotApproved):
        load_loader_module(loader, pins, "toy")


def test_altered_loader_rejected(pinned_loader: tuple[Path, Path, str]) -> None:
    loader, pins, key = pinned_loader
    loader.write_text(LOADER_SRC + "\n# tampered\n", encoding="utf-8")
    with pytest.raises(LoaderHashMismatch):
        load_loader_module(loader, pins, key)


# ---- invariant 4: verdict is a Verdict from judge, not agent output ----------

def test_verdict_comes_from_judge(dataset, pinned_loader, tmp_path) -> None:
    loader, pins, key = pinned_loader
    record_path = run_runner(
        key=key, dataset_root=dataset, loader_path=loader, pins_path=pins,
        run_agent=_good_agent, runs_dir=tmp_path / "runs",
    )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["loader_hash"] == sha256_file(loader)
    assert len(record["verdicts"]) == 1
    v = Verdict.model_validate(record["verdicts"][0])
    assert v.passed is True


def test_failing_agent_is_recorded_as_failure(dataset, pinned_loader, tmp_path) -> None:
    loader, pins, key = pinned_loader

    def _noop_agent(work_dir: Path, example: Example) -> None:
        pass  # leaves C1 empty -> judge should fail it

    record_path = run_runner(
        key=key, dataset_root=dataset, loader_path=loader, pins_path=pins,
        run_agent=_noop_agent, runs_dir=tmp_path / "runs",
    )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["verdicts"][0]["passed"] is False
