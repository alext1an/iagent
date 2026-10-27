from __future__ import annotations

from pathlib import Path

from iagent.spec_io import spec_parse, skill_parse

SRC_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    out = spec_parse("spec-sheetagent", root=SRC_ROOT)
    print(f"Wrote spec {out}")
    out = skill_parse("skill-spreadsheet", root=SRC_ROOT)
    print(f"Wrote skill {out}")

if __name__ == "__main__":
    main()
