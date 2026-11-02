"""Onboarding tools for the eval agent.

The eval agent reads a benchmark and writes a loader (load/judge). Before that
loader can score anything it must pass a golden check and be human-approved,
which pins its hash. These are the only platform actions the agent can trigger
during onboarding; it cannot pin a loader itself and it never runs scoring.

Split of trust:
  - agent writes the loader file (via FileSystem capability, outside this module)
  - golden_check() runs the loader on the benchmark's known samples -- a correct
    solution MUST pass and a deliberately-wrong one MUST fail
  - approve_and_pin() asks a human; only on approval is the hash written to pins
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from iagent.eval.loader import InvalidLoader, sha256_file
from iagent.eval.types import Example, Verdict


@dataclass
class GoldenCase:
    """A benchmark-provided sample with a known-correct outcome.

    ``apply`` mutates the work dir to the given solution (correct or wrong).
    The golden check asserts: correct -> judge passes, wrong -> judge fails.
    """

    example: Example
    apply: Callable[[Path], None]
    should_pass: bool


@dataclass
class GoldenReport:
    ok: bool
    results: list[dict]  # per case: {example_id, should_pass, actually_passed, ok}

    def summary(self) -> str:
        lines = [f"golden check: {'PASS' if self.ok else 'FAIL'}"]
        for r in self.results:
            mark = "ok" if r["ok"] else "MISMATCH"
            lines.append(
                f"  [{mark}] {r['example_id']}: expected "
                f"{'pass' if r['should_pass'] else 'fail'}, "
                f"got {'pass' if r['actually_passed'] else 'fail'}"
            )
        return "\n".join(lines)


def _import_unpinned(loader_path: Path):
    """Import a loader WITHOUT a pin check -- only for golden check pre-approval."""
    spec = importlib.util.spec_from_file_location("iagent_loader_golden", loader_path)
    if spec is None or spec.loader is None:
        raise InvalidLoader(f"cannot import loader at {loader_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not (hasattr(module, "load") and hasattr(module, "judge")):
        raise InvalidLoader("loader must define load(root) and judge(work_dir, example)")
    return module


def golden_check(
    loader_path: Path,
    cases: list[GoldenCase],
    *,
    work_root: Path,
) -> GoldenReport:
    """Run the loader's judge on known cases before anyone trusts it.

    A loader that cannot tell a correct solution from a wrong one is not safe to
    pin, even if it never raises. This is what makes the human approval see
    evidence rather than a blank file.
    """
    import shutil

    module = _import_unpinned(Path(loader_path))
    results: list[dict] = []
    for i, case in enumerate(cases):
        work = Path(work_root) / f"golden-{i}"
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        case.apply(work)
        verdict: Verdict = module.judge(work, case.example)
        actually = verdict.passed
        results.append({
            "example_id": case.example.id,
            "should_pass": case.should_pass,
            "actually_passed": actually,
            "ok": actually == case.should_pass,
        })
    return GoldenReport(ok=all(r["ok"] for r in results), results=results)


ApproveFn = Callable[[str, str], Awaitable[bool]]
"""Ask a human to approve pinning a loader. (loader_key, evidence) -> approved?"""


async def _ask_operator(loader_key: str, evidence: str) -> bool:
    import asyncio

    prompt = (
        f"\n--- loader approval requested ---"
        f"\n  key: {loader_key}"
        f"\n{evidence}"
        f"\n  approve and pin this loader? [y/N] "
    )
    answer = await asyncio.to_thread(input, prompt)
    return answer.strip().lower() in {"y", "yes"}


async def approve_and_pin(
    loader_path: Path,
    pins_path: Path,
    key: str,
    *,
    golden: GoldenReport,
    ask: ApproveFn | None = None,
) -> bool:
    """Gate pinning on golden-check success AND human approval.

    Returns True and writes the pin only if both hold. A loader that failed its
    golden check is never offered for approval -- the agent must fix it first.
    """
    if not golden.ok:
        return False
    ask_fn = ask or _ask_operator
    approved = await ask_fn(key, golden.summary())
    if not approved:
        return False

    pins_path = Path(pins_path)
    data = json.loads(pins_path.read_text(encoding="utf-8")) if pins_path.exists() else {}
    data.setdefault("loaders", {})[key] = sha256_file(loader_path)
    pins_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return True
