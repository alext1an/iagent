"""iagent.eval -- neutral evaluation core.

The platform only knows ``Example`` and ``Verdict``. All benchmark-specific
knowledge (file layout, answer comparison, recalculation) lives in a pinned,
human-approved loader kept outside ``src/iagent``.
"""

from iagent.eval.types import EvaluationRule, Example, Verdict

__all__ = ["EvaluationRule", "Example", "Verdict"]
