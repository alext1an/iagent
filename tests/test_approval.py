from __future__ import annotations

import asyncio

from pydantic_ai_harness.guardrails import GuardrailResult, ToolCallInfo

from iagent.approval import command_approval_guardrail


def _call(command: str = "python solution.py") -> ToolCallInfo:
    return ToolCallInfo(name="run_command", args={"command": command}, tool_call_id="t1")


async def _allow(_call: ToolCallInfo) -> GuardrailResult:
    return GuardrailResult.allow()


async def _deny(_call: ToolCallInfo) -> GuardrailResult:
    return GuardrailResult.block("no")


def test_injected_asker_can_allow() -> None:
    rail = command_approval_guardrail(ask=_allow)
    verdict = asyncio.run(rail.guard(_call()))
    assert verdict.action == "allow"


def test_injected_asker_can_block() -> None:
    rail = command_approval_guardrail(ask=_deny)
    verdict = asyncio.run(rail.guard(_call()))
    assert verdict.action == "block"
    assert verdict.message == "no"


def test_listed_command_skips_the_prompt() -> None:
    asked = False

    async def _ask(_call: ToolCallInfo) -> GuardrailResult:
        nonlocal asked
        asked = True
        return GuardrailResult.block("should not ask")

    rail = command_approval_guardrail(
        ask=_ask,
        auto_approve=["python workspace/upload_dataset.py"],
    )
    exact = asyncio.run(rail.guard(_call("python workspace/upload_dataset.py")))
    with_args = asyncio.run(rail.guard(_call("python workspace/upload_dataset.py --check")))
    other = asyncio.run(rail.guard(_call("python workspace/run_eval.py")))
    assert exact.action == "allow"
    assert with_args.action == "allow"
    assert other.action == "block"
    assert asked is True


def test_listed_command_does_not_match_a_longer_name() -> None:
    rail = command_approval_guardrail(ask=_deny, auto_approve=["ls"])
    verdict = asyncio.run(rail.guard(_call("lsof")))
    assert verdict.action == "block"


def test_default_tools_are_command_runners() -> None:
    rail = command_approval_guardrail(ask=_allow)
    assert list(rail.tools) == ["run_command", "start_command"]
