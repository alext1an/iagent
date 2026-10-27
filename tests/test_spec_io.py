from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic_ai import AgentSpec

from iagent.spec_io import (
    message_text,
    parse_spec,
    prompt_body,
    safe_name,
    skill_name_parse,
    skill_output_path,
    spec_output_path,
    write_skill,
    write_spec,
)

SPEC = {
    "name": "myagent",
    "model": "openai:gpt-4o",
    "instructions": "You are a helpful chat agent that can answer questions and help with tasks",
    "capabilities": ["Instrumentation"],
}


def test_message_text_from_string() -> None:
    assert message_text('{"name": "myagent"}') == '{"name": "myagent"}'


def test_message_text_from_phoenix_parts() -> None:
    parts = [
        {"type": "text", "text": '{"name":'},
        {"type": "text", "text": ' "myagent"}'},
    ]
    assert message_text(parts) == '{"name": "myagent"}'


def test_message_text_rejects_empty_and_unknown() -> None:
    with pytest.raises(ValueError, match="no text"):
        message_text([{"type": "image", "url": "x"}])
    with pytest.raises(TypeError, match="Unexpected"):
        message_text(123)


def test_parse_spec_json_requires_name() -> None:
    spec = parse_spec(json.dumps(SPEC), fmt="json")
    assert spec.name == "myagent"
    assert spec.model == "openai:gpt-4o"
    with pytest.raises(ValueError, match="missing name"):
        parse_spec(json.dumps({"model": "openai:gpt-4o"}), fmt="json")


def test_safe_name_rejects_path_segments() -> None:
    assert safe_name("myagent") == "myagent"
    with pytest.raises(ValueError, match="Unsafe"):
        safe_name("../secret")
    with pytest.raises(ValueError, match="Unsafe"):
        safe_name("a/b")


def test_write_spec_roundtrip(tmp_path: Path) -> None:
    spec = AgentSpec.model_validate(SPEC)
    out = spec_output_path(tmp_path, spec)
    write_spec(spec, out)
    loaded = AgentSpec.from_file(out)
    assert loaded.name == "myagent"
    assert loaded.model == "openai:gpt-4o"


class _FakePrompt:
    def __init__(self, content) -> None:
        self._content = content

    def _dumps(self) -> dict:
        return {"template": {"messages": [{"content": self._content}]}}


def test_prompt_body_reads_first_message() -> None:
    prompt = _FakePrompt([{"type": "text", "text": json.dumps(SPEC)}])
    body = prompt_body(prompt)
    assert json.loads(body)["name"] == "myagent"


def test_prompt_body_rejects_empty_messages() -> None:
    class _Empty:
        def _dumps(self) -> dict:
            return {"template": {"messages": []}}

    with pytest.raises(ValueError, match="no messages"):
        prompt_body(_Empty())


def test_skill_name_parse_strips_prefix_and_validates() -> None:
    assert skill_name_parse("skill-spreadsheet") == "spreadsheet"
    assert skill_name_parse("spreadsheet") == "spreadsheet"
    with pytest.raises(ValueError, match="Unsafe"):
        skill_name_parse("skill-../etc")


def test_skill_output_path_nests_under_skills_dir(tmp_path: Path) -> None:
    out = skill_output_path(tmp_path, "spreadsheet")
    assert out == tmp_path / "skills" / "spreadsheet" / "SKILL.md"


def test_write_skill_creates_parents_and_writes_text(tmp_path: Path) -> None:
    out = skill_output_path(tmp_path, "spreadsheet")
    returned = write_skill("# How to use spreadsheets\n", out)
    assert returned == out
    assert out.is_file()
    assert out.read_text(encoding="utf-8") == "# How to use spreadsheets\n"
