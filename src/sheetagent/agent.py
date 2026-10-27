from __future__ import annotations

import sys
from pathlib import Path

from pydantic_ai_harness import Skills, Shell

from iagent.runtime import load_agent
from iagent.tracing import load_env, setup_tracing

SPEC_PATH = Path(__file__).with_name("agent.yaml")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: sheetagent <task description>", file=sys.stderr)
        raise SystemExit(2)

    load_env()
    setup_tracing()
    agent = load_agent(SPEC_PATH, custom_capability_types=[Skills, Shell])
    result = agent.run_sync(" ".join(sys.argv[1:]))
    print(result.output)


if __name__ == "__main__":
    main()
