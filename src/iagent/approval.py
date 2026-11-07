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


def _is_listed(command: str, listed: Sequence[str]) -> bool:
    """True when ``command`` is a listed command or that command plus arguments."""
    text = command.strip()
    for entry in listed:
        item = entry.strip()
        if item and (text == item or text.startswith(item + " ")):
            return True
    return False


def command_approval_guardrail(
    *,
    tools: list[str] | None = None,
    ask: AskFn | None = None,
    auto_approve: Sequence[str] = (),
) -> ToolGuardrail:
    """A `ToolGuardrail` that asks a human to approve each shell command.

    Commands in ``auto_approve`` pass without a prompt. An entry matches the
    whole command, or the same command followed by a space and arguments.
    ``python workspace/upload_dataset.py`` matches that script with extra
    arguments. ``python`` matches every command that starts with ``python``.

    Args:
        ask: Async callback that returns allow/block. Defaults to a terminal prompt.
        tools: Tool names to gate. Defaults to `run_command` and `start_command`.
        auto_approve: Commands that skip the prompt. Empty by default.
    Returns:
        A `ToolGuardrail` to add to an agent's `capabilities`.
    """
    asker = ask or _ask_operator
    listed = tuple(auto_approve)

    async def guard(call: ToolCallInfo) -> GuardrailResult:
        if _is_listed(_command_text(call), listed):
            return GuardrailResult.allow()
        return await asker(call)

    return ToolGuardrail(guard=guard, tools=list(tools or COMMAND_TOOLS))
