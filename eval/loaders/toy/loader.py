"""Toy loader -- smallest end-to-end proof of the eval chain.

Lives outside src/iagent on purpose: the platform stays neutral and only ever
sees Example / Verdict. This loader is the only place that knows the toy's
layout (input.xlsx with a value in B1, expected B1*2 in C1).
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from iagent.eval.types import EvaluationRule, Example, Verdict


def load(root: Path) -> list[Example]:
    return [
        Example(
            id="toy-001",
            instruction=(
                "The workbook has a numeric value in cell B1. Write double that "
                "value into cell C1 and save the workbook."
            ),
            files=[Path("input.xlsx")],
            judge_input={"source_cell": "B1", "target_cell": "C1", "factor": 2},
        )
    ]


def judge(work_dir: Path, example: Example) -> Verdict:
    ji = example.judge_input
    rule = EvaluationRule(
        rule=f"{ji['target_cell']} must equal {ji['source_cell']} * {ji['factor']}",
        source_type="explicit",
        source_file="toy instruction",
        confidence=1.0,
        evidence=["instruction: write double the value of B1 into C1"],
    )

    wb = load_workbook(work_dir / "input.xlsx", data_only=True)
    ws = wb.active
    src = ws[ji["source_cell"]].value
    got = ws[ji["target_cell"]].value
    expected = (src or 0) * ji["factor"]

    failures: list[str] = []
    if got != expected:
        failures.append(
            f"{ji['target_cell']} = {got!r}, expected {expected!r} "
            f"({ji['source_cell']}={src!r} * {ji['factor']})"
        )

    return Verdict(
        example_id=example.id,
        passed=not failures,
        failures=failures,
        explanation=f"toy check on {ji['target_cell']}",
        rules_applied=[rule],
    )
