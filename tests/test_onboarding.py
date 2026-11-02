"""Tests for eval onboarding: golden check and approval-gated pinning."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from iagent.eval.loader import read_loader_pin, sha256_file
from iagent.eval.onboarding import (
    GoldenCase,
    approve_and_pin,
    golden_check,
)
from iagent.eval.types import Example

# A loader whose judge checks C1 == B1 * 2.
GOOD_LOADER = '''
from pathlib import Path
from iagent.eval.types import Example, Verdict

def load(root):
    return [Example(id="toy-001", instruction="double B1 into C1",
                    files=[Path("input.xlsx")], judge_input={})]

def judge(work_dir, example):
    from openpyxl import load_workbook
    ws = load_workbook(work_dir / "input.xlsx", data_only=True).active
    ok = ws["C1"].value == (ws["B1"].value or 0) * 2
    return Verdict(example_id=example.id, passed=ok,
                   failures=[] if ok else ["C1 wrong"])
'''

# A loader whose judge always passes -- must be caught by the golden check.
LENIENT_LOADER = '''
from pathlib import Path
from iagent.eval.types import Example, Verdict

def load(root):
    return [Example(id="toy-001", instruction="x", files=[Path("input.xlsx")], judge_input={})]

def judge(work_dir, example):
    return Verdict(example_id=example.id, passed=True)
'''


def _write_input(work: Path, c1=None) -> None:
    wb = Workbook()
    ws = wb.active
    ws["A1"], ws["B1"] = "value", 10
    if c1 is not None:
        ws["C1"] = c1
    wb.save(work / "input.xlsx")


def _cases() -> list[GoldenCase]:
    ex = Example(id="toy-001", instruction="double", files=[Path("input.xlsx")])
    return [
        GoldenCase(example=ex, apply=lambda w: _write_input(w, c1=20), should_pass=True),
        GoldenCase(example=ex, apply=lambda w: _write_input(w, c1=999), should_pass=False),
    ]


def test_golden_check_passes_for_correct_judge(tmp_path: Path) -> None:
    loader = tmp_path / "loader.py"
    loader.write_text(GOOD_LOADER, encoding="utf-8")
    report = golden_check(loader, _cases(), work_root=tmp_path / "gc")
    assert report.ok is True


def test_golden_check_catches_lenient_judge(tmp_path: Path) -> None:
    # A judge that always passes should FAIL the golden check on the wrong case.
    loader = tmp_path / "loader.py"
    loader.write_text(LENIENT_LOADER, encoding="utf-8")
    report = golden_check(loader, _cases(), work_root=tmp_path / "gc")
    assert report.ok is False
    bad = [r for r in report.results if not r["ok"]]
    assert bad and bad[0]["should_pass"] is False and bad[0]["actually_passed"] is True


def test_approve_and_pin_requires_golden_pass(tmp_path: Path) -> None:
    loader = tmp_path / "loader.py"
    loader.write_text(LENIENT_LOADER, encoding="utf-8")
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"loaders": {}}), encoding="utf-8")
    report = golden_check(loader, _cases(), work_root=tmp_path / "gc")

    async def _always_yes(_k, _e):  # human would say yes, but golden failed
        return True

    ok = asyncio.run(approve_and_pin(loader, pins, "toy", golden=report, ask=_always_yes))
    assert ok is False
    assert read_loader_pin(pins, "toy") is None


def test_approve_and_pin_requires_human_yes(tmp_path: Path) -> None:
    loader = tmp_path / "loader.py"
    loader.write_text(GOOD_LOADER, encoding="utf-8")
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"loaders": {}}), encoding="utf-8")
    report = golden_check(loader, _cases(), work_root=tmp_path / "gc")

    async def _no(_k, _e):
        return False

    ok = asyncio.run(approve_and_pin(loader, pins, "toy", golden=report, ask=_no))
    assert ok is False
    assert read_loader_pin(pins, "toy") is None


def test_approve_and_pin_writes_pin_on_both(tmp_path: Path) -> None:
    loader = tmp_path / "loader.py"
    loader.write_text(GOOD_LOADER, encoding="utf-8")
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"loaders": {}}), encoding="utf-8")
    report = golden_check(loader, _cases(), work_root=tmp_path / "gc")

    async def _yes(_k, _e):
        return True

    ok = asyncio.run(approve_and_pin(loader, pins, "toy", golden=report, ask=_yes))
    assert ok is True
    assert read_loader_pin(pins, "toy") == sha256_file(loader)


def test_evalagent_yaml_has_expected_shape() -> None:
    # Cross-platform: evalagent mounts FileSystem, NOT Shell or Spreadsheet,
    # and keeps the dataset tree read-only.
    from pathlib import Path as _P

    spec = _P(__file__).resolve().parents[1] / "src" / "evalagent" / "agent.yaml"
    text = spec.read_text(encoding="utf-8")
    assert "name: evalagent" in text
    assert "FileSystem:" in text
    assert "eval/dataset/**" in text
    assert "Shell:" not in text
    assert "Spreadsheet" not in text


@pytest.mark.skipif(
    __import__("os").name != "posix",
    reason="LocalWorkspace requires POSIX (use WSL/Linux for full agent load)",
)
def test_evalagent_builds() -> None:
    from pydantic_ai.models.test import TestModel

    from evalagent.agent import build_agent

    agent = build_agent(model=TestModel(call_tools=[]))
    result = agent.run_sync("hello")
    assert isinstance(result.output, str)
