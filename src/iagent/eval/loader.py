"""Load and verify a benchmark loader module.

Safety invariant: a loader runs only if its on-disk SHA-256 matches an approved
pin. A new or changed loader hash must be human-approved (pin updated) first.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Protocol, runtime_checkable

from iagent.eval.types import Example, Verdict


class LoaderNotApproved(Exception):
    """No approved pin exists for this loader key."""


class LoaderHashMismatch(Exception):
    """On-disk loader does not match the approved pin."""


class InvalidLoader(Exception):
    """Loader module is missing load() or judge()."""


@runtime_checkable
class LoaderModule(Protocol):
    def load(self, root: Path) -> list[Example]: ...
    def judge(self, work_dir: Path, example: Example) -> Verdict: ...


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_loader_pin(pins_path: Path, key: str) -> str | None:
    """Return the approved loader hash for ``key``, or None if unpinned.

    MVP: pin storage lives here. Split into a pins module once dataset pins also
    need managing (pull writes, runner reads, approval updates -- three callers).
    """
    pins_path = Path(pins_path)
    if not pins_path.exists():
        return None
    data = json.loads(pins_path.read_text(encoding="utf-8"))
    return data.get("loaders", {}).get(key)


def load_loader_module(loader_path: Path, pins_path: Path, key: str) -> LoaderModule:
    """Verify the pin, then import the loader module.

    Raises before importing if the loader is unapproved or altered, so untrusted
    loader code never executes.
    """
    loader_path = Path(loader_path)
    pinned = read_loader_pin(pins_path, key)
    if pinned is None:
        raise LoaderNotApproved(f"loader {key!r} has no approved pin in {pins_path}")
    actual = sha256_file(loader_path)
    if actual != pinned:
        raise LoaderHashMismatch(
            f"loader {key!r}: expected {pinned[:12]}..., got {actual[:12]}..."
        )

    spec = importlib.util.spec_from_file_location(f"iagent_loader_{key}", loader_path)
    if spec is None or spec.loader is None:
        raise InvalidLoader(f"cannot import loader at {loader_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not (hasattr(module, "load") and hasattr(module, "judge")):
        raise InvalidLoader("loader must define load(root) and judge(work_dir, example)")
    return module  # type: ignore[return-value]
