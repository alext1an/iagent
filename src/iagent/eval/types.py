"""Shared eval types. The platform only ever sees these three.

Neutrality rule: nothing here mentions cells, sheets, or formulas. Anything that
does belongs in a loader outside ``src/iagent``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class EvaluationRule(BaseModel):
    """A single scoring rule with its provenance.

    ``source_type`` is one of:
      - ``explicit``  -- from the user instruction or official benchmark docs
      - ``inferred``  -- derived from the dataset, golden sample, or vendor code
      - ``generated`` -- proposed by the agent itself

    User-specified rules outrank everything; on conflict the loader must report
    it, never silently override.
    """

    rule: str
    source_type: str
    source_file: str | None = None
    confidence: float = 1.0
    evidence: list[str] = Field(default_factory=list)


class Example(BaseModel):
    """One evaluation case.

    ``files`` are copied into the isolated work dir and are visible to the agent.
    ``judge_input`` holds the answer and is opaque to the platform; it is NEVER
    copied into the work dir.
    """

    id: str
    instruction: str
    files: list[Path] = Field(default_factory=list)
    judge_input: dict = Field(default_factory=dict)


class Verdict(BaseModel):
    """Produced by the loader's ``judge``, never by model prose."""

    example_id: str
    passed: bool
    failures: list[str] = Field(default_factory=list)
    explanation: str = ""
    rules_applied: list[EvaluationRule] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)
