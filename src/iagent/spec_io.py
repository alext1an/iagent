from __future__ import annotations

from pathlib import Path
from typing import Any

from phoenix.client import Client
from pydantic_ai import AgentSpec

UNSAFE_NAME_CHARS = {"/", "\\"}


def message_text(content: Any) -> str:
    """Unwrap a Phoenix chat message body into a spec string."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    else:
        raise TypeError(f"Unexpected Phoenix message content: {type(content).__name__}")
    if not text.strip():
        raise ValueError("Phoenix prompt message has no text")
    return text


def prompt_body(prompt: Any) -> str:
    messages = prompt._dumps()["template"]["messages"]
    if not messages:
        raise ValueError("Phoenix prompt has no messages")
    return message_text(messages[0]["content"])


def parse_spec(text: str, *, fmt: str = "json") -> AgentSpec:
    spec = AgentSpec.from_text(text, fmt=fmt)  # type: ignore[arg-type]
    if not spec.name:
        raise ValueError("Spec is missing name; cannot build output path")
    return spec


def safe_agent_name(name: str) -> str:
    if not name or name in {".", ".."} or any(ch in name for ch in UNSAFE_NAME_CHARS):
        raise ValueError(f"Unsafe agent name: {name!r}")
    return name


def spec_output_path(root: Path, spec: AgentSpec) -> Path:
    return root / safe_agent_name(spec.name) / "agent.yaml"


def write_spec(spec: AgentSpec, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    spec.to_file(path, schema_path=None)
    return path


def spec_parse(
    prompt_identifier: str,
    tag: str | None = None,
    *,
    root: Path,
    client: Any = None,
    fmt: str = "json",
) -> Path:
    """Fetch a Phoenix prompt, parse it as an AgentSpec, and write `{root}/{name}/agent.yaml`."""
    px = client or Client()
    prompt = px.prompts.get(prompt_identifier=prompt_identifier, tag=tag)
    spec = parse_spec(prompt_body(prompt), fmt=fmt)
    out = spec_output_path(root, spec)
    return write_spec(spec, out)
