"""Terminal entry point for every agent in this repo.

Each agent is `package.agent:build_agent`. With no prompt, the command opens that
agent's interactive chat. With a prompt, it runs once and streams the reply,
including tool calls, in the terminal.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
from collections.abc import Callable
from typing import Any

from iagent.tracing import load_env, setup_tracing

AGENTS = ("evalagent", "myagent", "sheetagent")


def build_agent(name: str, **kwargs: Any):
    """Import `<name>.agent:build_agent` and call it."""
    if name not in AGENTS:
        known = ", ".join(AGENTS)
        raise SystemExit(f"Unknown agent {name!r}. Known agents: {known}")
    module = importlib.import_module(f"{name}.agent")
    factory: Callable[..., Any] = module.build_agent
    return factory(**kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cli",
        description="Run one of the project agents in the terminal.",
    )
    parser.add_argument("agent", nargs="?", choices=AGENTS, help="Which agent to run.")
    parser.add_argument(
        "message",
        nargs="*",
        help="Prompt to send once. Omit it to open an interactive chat.",
    )
    args = parser.parse_args(argv)
    if args.agent is None:
        print("Agents: " + ", ".join(AGENTS))
        print("Usage: cli <agent> [message...]")
        return 0

    load_env()
    setup_tracing(project_name=args.agent)
    agent = build_agent(args.agent)
    message = " ".join(args.message).strip()
    if not message:
        agent.to_cli_sync(prog_name=args.agent)
        return 0

    from rich.console import Console

    from pydantic_ai._cli import ask_agent

    asyncio.run(
        ask_agent(
            agent,
            message,
            stream=True,
            console=Console(),
            code_theme="monokai",
        )
    )
    return 0
