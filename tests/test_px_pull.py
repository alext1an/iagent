from __future__ import annotations

import json
from pathlib import Path

from iagent.spec_io import spec_parse, skill_parse

SPEC = {
    "name": "pulled-agent",
    "model": "openai:gpt-4o",
    "instructions": "Be helpful.",
    "capabilities": ["Instrumentation"],
}

SKILL_TEXT = "# Spreadsheet skill\n\nUse openpyxl to edit workbooks.\n"


class _FakePrompt:
    def _dumps(self) -> dict:
        return {
            "template": {
                "messages": [
                    {"content": [{"type": "text", "text": json.dumps(SPEC)}]}
                ]
            }
        }


class _FakeClient:
    class prompts:
        @staticmethod
        def get(prompt_identifier: str, tag: str | None = None):
            assert prompt_identifier == "chat-agent"
            assert tag is None
            return _FakePrompt()


def test_spec_parse_writes_named_yaml(tmp_path: Path) -> None:
    out = spec_parse("chat-agent", root=tmp_path, client=_FakeClient())
    assert out == tmp_path / "pulled-agent" / "agent.yaml"
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "name: pulled-agent" in text
    assert "model: openai:gpt-4o" in text


class _FakeSkillPrompt:
    def _dumps(self) -> dict:
        return {
            "template": {
                "messages": [
                    {"content": [{"type": "text", "text": SKILL_TEXT}]}
                ]
            }
        }


class _FakeSkillClient:
    class prompts:
        @staticmethod
        def get(prompt_identifier: str, tag: str | None = None):
            assert prompt_identifier == "skill-spreadsheet"
            assert tag is None
            return _FakeSkillPrompt()


def test_skill_parse_writes_named_skill(tmp_path: Path) -> None:
    out = skill_parse("skill-spreadsheet", root=tmp_path, client=_FakeSkillClient())
    assert out == tmp_path / "skills" / "spreadsheet" / "SKILL.md"
    assert out.is_file()
    assert out.read_text(encoding="utf-8") == SKILL_TEXT
