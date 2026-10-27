from __future__ import annotations

import sys
from pathlib import Path

from pydantic_ai_harness import Skills, Shell

from iagent.approval import command_approval_guardrail
from iagent.runtime import load_agent
from iagent.tracing import load_env, setup_tracing
from iagent.tools.spreadsheet import read_xlsx, summarize_xlsx

SPEC_PATH = Path(__file__).with_name("agent.yaml")

TOOLS = [summarize_xlsx, read_xlsx]


def build_agent(*, approve_commands: bool = True, **kwargs):
    """Construct the sheetagent with its spreadsheet inspection tools attached.

    When ``approve_commands`` is True, each shell command the agent runs must be
    approved by a human at the terminal before it executes.
    """
    extra = list(kwargs.pop("capabilities", None) or [])
    if approve_commands:
        extra.append(command_approval_guardrail())
    return load_agent(
        SPEC_PATH,
        custom_capability_types=[Skills, Shell],
        tools=TOOLS,
        capabilities=extra,
        **kwargs,
    )


def main() -> None:
    instruction = "Complete the financial model based on the provided assumptions. Ensure that all formulas, references, and calculations are correct. Here is the spreadsheet path: runs/example/02_06_input.xlsx "
    load_env()
    setup_tracing()
    agent = build_agent()
    result = agent.run_sync(instruction)
    print(result.output)


if __name__ == "__main__":
    main()
