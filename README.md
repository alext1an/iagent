# iagent

Pull a Pydantic AI agent spec from Arize Phoenix, run it, and send traces back to Phoenix.

## Setup

```powershell
uv sync --group dev
copy .env.example .env
```

Set `OPENROUTER_API_KEY ` in `.env` for a real model. Phoenix collector:

```
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
PHOENIX_PROJECT=chat-agent
```

## Commands

```powershell
uv run px-pull
uv run myagent
uv run pytest
```