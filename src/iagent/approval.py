"""Human-in-the-loop approval for shell command execution.

Built on the harness `ToolGuardrail`. `command_approval_guardrail` returns a
`ToolGuardrail` scoped to the shell command tools; its async guard blocks the run
on `input()` and asks a human to approve each command before it runs. A denied
command returns a refusal to the model as the tool result (via `block`), so the
agent can adapt rather than the run aborting.

This is the in-process approval shape: the run stays open and the tool call
awaits the answer. It needs no `DeferredToolRequests` in the agent's output type
and no resume loop, which suits a CLI.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence

from pydantic_ai_harness.guardrails import GuardrailResult, ToolCallInfo, ToolGuardrail

# Harness Shell tools that execute a command (not check/stop a background job by id).
COMMAND_TOOLS: list[str] = ["run_command", "start_command"]
AskFn = Callable[[ToolCallInfo], Awaitable[GuardrailResult]]


def _command_text(call: ToolCallInfo) -> str:
    command = call.args.get("command", "")
    return command if isinstance(command, str) else str(command)


async def _ask_operator(call: ToolCallInfo) -> GuardrailResult:
    """Prompt on the terminal; allow on 'y', otherwise block with a message to the model."""
    prompt = (
        f"\n  tool: {call.name}"
        f"\n  command: {_command_text(call)}"
        f"\n  approve? [y/N] "
    )
    answer = await asyncio.to_thread(input, prompt)
    if answer.strip().lower() in {"y", "yes"}:
        return GuardrailResult.allow()
    return GuardrailResult.block("Command denied by the operator.")


def command_approval_guardrail(*,
                               tools: list[str] | None = None,
                               ask: AskFn | None = None
                               ) -> ToolGuardrail:
    """A `ToolGuardrail` that asks a human to approve each shell command.

    Args:
        ask: Async callback that returns allow/block. Defaults to a terminal prompt.
        tools: Tool names to gate. Defaults to `run_command` and `start_command`.
    Returns:
        A `ToolGuardrail` to add to an agent's `capabilities`.
    """
    return ToolGuardrail(guard=ask or _ask_operator, tools=list(tools or COMMAND_TOOLS))
