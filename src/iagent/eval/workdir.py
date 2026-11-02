"""Build an isolated work dir for one example.

Safety invariant: only ``example.files`` are copied in; ``judge_input`` never
lands in the work dir, so the agent under test cannot read the answer.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from iagent.eval.types import Example


class WorkDirViolation(Exception):
    """A referenced file resolves outside the dataset root."""


def prepare_work_dir(base: Path, example: Example, dataset_root: Path) -> Path:
    """Create ``base/<example.id>`` and copy only the agent-visible files into it.

    Each file is validated to live under ``dataset_root`` to block path escapes.
    ``judge_input`` is intentionally untouched here -- that is the isolation.
    """
    base = Path(base)
    dataset_root = Path(dataset_root).resolve()

    work = base / example.id
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    for rel in example.files:
        src = (dataset_root / rel).resolve()
        if src != dataset_root and dataset_root not in src.parents:
            raise WorkDirViolation(f"{src} escapes dataset root {dataset_root}")
        if not src.is_file():
            raise WorkDirViolation(f"file not found: {src}")
        shutil.copy2(src, work / Path(rel).name)

    return work
