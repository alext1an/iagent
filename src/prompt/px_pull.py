from __future__ import annotations

from pathlib import Path

from iagent.spec_io import spec_parse

SRC_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    out = spec_parse("chat-agent", root=SRC_ROOT)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
