from __future__ import annotations

import os

import pytest
from pydantic_ai.models.test import TestModel


def test_cli_lists_agents_when_called_without_one(capsys: pytest.CaptureFixture[str]) -> None:
    from cli import main

    assert main([]) == 0
    out = capsys.readouterr().out
    assert "evalagent" in out
    assert "sheetagent" in out
    assert "myagent" in out


def test_cli_rejects_an_unknown_agent() -> None:
    from cli import build_agent

    with pytest.raises(SystemExit, match="Unknown agent"):
        build_agent("missing")


@pytest.mark.skipif(
    os.name != "posix",
    reason="LocalWorkspace requires POSIX (use WSL/Linux for full agent load)",
)
def test_cli_one_shot_prints_the_reply(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    from cli import main

    monkeypatch.setattr("cli.load_env", lambda: None)
    monkeypatch.setattr("cli.setup_tracing", lambda **kwargs: None)
    monkeypatch.setattr(
        "cli.build_agent",
        lambda name, **kwargs: __import__("myagent.agent", fromlist=["build_agent"]).build_agent(
            model=TestModel(custom_output_text="from-the-cli", call_tools=[])
        ),
    )

    assert main(["myagent", "hello", "there"]) == 0
    assert "from-the-cli" in capsys.readouterr().out
