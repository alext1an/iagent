from __future__ import annotations

import os
from pathlib import Path

from pydantic_ai.models.test import TestModel

from iagent.runtime import load_agent
from iagent.tracing import load_env, setup_tracing

SPEC_PATH = Path(__file__).with_name("agent.yaml")


def main() -> None:
    load_env()
    setup_tracing()
    agent = load_agent(SPEC_PATH)
    result = agent.run_sync(
        "Websearch for the latest news on the stock market in the last 24 hours"
    )
    print(result.output)


if __name__ == "__main__":
    main()
