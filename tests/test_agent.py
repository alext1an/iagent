from __future__ import annotations

from pathlib import Path

from pydantic_ai.models.test import TestModel

from iagent.runtime import load_agent

SPEC = Path(__file__).resolve().parents[1] / "src" / "myagent" / "agent.yaml"


def test_load_agent_from_yaml_with_test_model() -> None:
    agent = load_agent(
        SPEC,
        model=TestModel(custom_output_text="ok", call_tools=[]),
    )
    result = agent.run_sync("hello")
    assert result.output == "ok"


def test_load_agent_requires_a_spec_path() -> None:
    import inspect

    params = inspect.signature(load_agent).parameters
    assert params["spec_path"].default is inspect.Parameter.empty


def test_agent_yaml_has_expected_fields() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "name: myagent" in text
    assert "model: openrouter:" in text
    assert "Instrumentation" in text
