# iagent

Agent platform plus spreadsheet workflow: pull versioned specs from Arize Phoenix, run agents with observability, and (planned) evaluate them against arbitrary benchmarks. Pydantic AI and the harness provide the model loop; this repo adds pinning, tracing, human approval, spreadsheet tooling, and an eval operator agent.

## Architecture (target)

| Layer | Role |
| --- | --- |
| **Platform (`iagent`)** | Pin hashes, load specs, Phoenix traces, eval runner, shared types (`Example`, `Verdict`). Does not import workflow agents. |
| **Sheet workflow (`sheetagent`)** | Spreadsheet agent: skills, shell for `solution.py`, custom **Spreadsheet** capability (map, script policy, diff, commit). |
| **Eval operator (`evalagent`)** | Pulls datasets, inspects folder layout, writes a loader, monitors **`run_runner`**, reports quoted verdicts from the run record. |

Dependency direction: `sheetagent` and `evalagent` import `iagent`; `iagent` does not import them.

**Neutrality rule:** all benchmark-specific knowledge (file layout, test cases, answer comparison, recalculation) lives in a pinned, human-approved **loader + judge** kept outside `src/iagent`. The platform only sees `Example` and `Verdict`.

## Setup

```bash
uv sync --group dev
cp .env.example .env
```

Set `OPENROUTER_API_KEY` in `.env` for a real model. Phoenix collector:

```
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
PHOENIX_PROJECT=chat-agent
```

## Commands (today)

```bash
uv run px-pull
uv run sheetagent
uv run myagent
uv run pytest
```

## Development roadmap

Work below is not fully implemented yet; use this list to track the design we are building toward.

### Platform (`iagent`)

- [ ] **Pins** — After `px-pull`, record SHA-256 of pulled spec, skill, and (later) dataset + loader in `src/pins.json`; refuse runs when on-disk files do not match.
- [ ] **Run record** — Per run: `runs/<run_id>/record.json` with `run_id`, task/example id, spec/skill hashes, trace project, verdicts, child trace ids. Consider Phoenix **experiments** (dataset + task + evaluators) as the system of record for scores and trace links instead of duplicating them locally.
- [ ] **Tracing** — Keep Phoenix OTEL; add parent span `iagent.eval` and child span `iagent.run` with shared `iagent.run_id` attribute.
- [ ] **Eval types** — Shared `Example` (`id`, `instruction`, `files` visible to the agent, `judge_input` hidden and opaque to the platform) and `Verdict` (`passed`, `failures`, `explanation`, optional free-form `details` for judge-defined data such as per-case results).
- [ ] **`pull_dataset`** — Tool/function: fetch rows from a Phoenix dataset and/or place the dataset files on disk; update pins; return path only (no fixed schema). Phoenix datasets hold JSON rows only, so binary files stay on disk under the pinned root.
- [ ] **`run_runner`** — Import loader module; require `load(root) -> list[Example]` and `judge(work_dir, example) -> Verdict`; for each example copy only `files` into an isolated work dir, run configured agent entry point (e.g. `sheetagent.agent:build_agent`), call `judge`, append verdict to record (verdicts come from loader/judge, not from model prose). `judge_input` is never copied into the work dir.
- [ ] **Loader pin** — Store hash of loader script next to the dataset pin (Phoenix dataset version id plus file manifest hash); reuse pinned loader for reproducible scores. A new or changed loader hash requires human approval (via the existing approval mechanism) before it is pinned; the agent rewrites the loader only when the dataset or pin is new.
- [ ] **Eval capability** — Harness capability exposing platform eval tools (`pull_dataset`, filesystem inspect, `run_runner`) for use by eval agent spec.

### Spreadsheet workflow (`sheetagent` + `iagent` sheet tools)

- [ ] **`Spreadsheet` capability** — YAML-configured capability (like `Shell` / `Coder`): `inspect_workbook` (existing summarize/read + workbook map: headers, formulas, cross-sheet refs).
- [ ] **Script policy** — `check_script(path)`: AST rules (allowed imports, no `to_excel` on formula workbooks, paths under task root).
- [ ] **`prepare_run`** — Execute vetted `solution.py`, build cell diff, structural errors; no human gate yet.
- [ ] **`commit_run`** — Publish output workbook; **ToolGuardrail** approval on diff (second gate alongside shell command approval).
- [ ] **Spec** — Add `Spreadsheet:` block to `sheetagent/agent.yaml`; register capability in `build_agent`.
- [ ] **Examples** — Toy + one real task under `examples/` with instructions and checks (or pointer to external benchmark layout).
- [ ] **Judge dependencies** — Benchmark judges that read formula results need a recalculation step (e.g. LibreOffice 7.5+) before comparing cells; document this next to the loader, not in platform setup.

### Eval operator (`evalagent`)

- [ ] **Phoenix spec** — `spec-evalagent` pulled to `src/evalagent/agent.yaml` (no `Shell` / `Spreadsheet`; uses Eval capability + workspace).
- [ ] **Onboarding loop** — Agent uses `pull_dataset`, lists/reads dataset folder (JSON, README, vendor match scripts), writes loader implementing `load` / `judge` (e.g. delegate to a vendor match script when present). The loader is proposed to a human for approval before it is pinned or used for scoring.
- [ ] **Monitor role** — Agent calls `run_runner`, reads tool-returned verdict rows from record; on loader/runner failure, fix loader and retry; final report quotes record only (does not invent pass/fail).
- [ ] **CLI** — `uv run evalagent` (or similar) entry point mirroring `sheetagent`.

### Quality and docs

- [ ] **Tests** — Pin mismatch; script policy; diff/prepare_run; guardrail block on commit; runner + toy loader verdict; `judge_input` never present in work dir; unapproved loader hash rejected; eval record integrity.
- [ ] **`.env.example`** — Keep it in sync with required env vars.
- [ ] **README results** — After first benchmark run: table of task, pass/fail, loader hash, trace link; one Phoenix screenshot of sheet run + eval run.
- [ ] **Cleanup** — Remove or demote `myagent` demo; stop treating repo-root `solution.py` / generated runs as source; gitignore ephemeral `runs/` outputs where appropriate.

### Explicit non-goals (for scope)

- No fixed dataset adapter types in platform code (format discovery stays with eval agent + loader script).
- No second domain capability beyond Spreadsheet for the CV story.
- Platform does not embed SpreadsheetBench-specific paths, test-case structure, or comparison logic; the loader/judge owns them and calls vendor scripts from the pulled tree.
- Platform never interprets `judge_input` or `Verdict.details`.
