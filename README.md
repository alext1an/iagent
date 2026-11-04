# iagent

Agent platform for spreadsheet work and benchmark evaluation. Specs are versioned in Arize Phoenix. This repository will pin those specs, run them with tracing and human approval, and score them against datasets. Pydantic AI and the harness provide the model loop. This repo adds pinning, tracing, approval, spreadsheet tooling, and an eval operator.

`main` starts empty on purpose. The sections below are the system this repository is for.

## Architecture

| Layer | Role |
| --- | --- |
| **Platform (`iagent`)** | Pin hashes, load specs, Phoenix traces, eval runner, shared types (`Example`, `Verdict`). Does not import workflow agents. |
| **Sheet workflow (`sheetagent`)** | Spreadsheet agent: skills, a shell for `solution.py`, and a **Spreadsheet** capability (workbook map, script policy, diff, commit). |
| **Eval operator (`evalagent`)** | Pulls a dataset, inspects its layout, writes a loader, runs the runner, and reports verdicts quoted from the run record. |

`sheetagent` and `evalagent` import `iagent`. `iagent` does not import them.

**Neutrality:** everything specific to a benchmark — file layout, test cases, answer comparison, recalculation — lives in a pinned, human-approved loader and judge outside `src/iagent`. The platform only sees `Example` and `Verdict`. It does not interpret `judge_input` or `Verdict.details`.

## How a run is supposed to work

1. The agent spec is written in Phoenix.
2. `px-pull` writes `src/<agent>/agent.yaml` and records SHA-256 pins for the spec, skills, and later the dataset and loader. A run is refused when the files on disk do not match the pin.
3. `sheetagent` works the spreadsheet task: inspect the workbook, check `solution.py`, prepare a cell diff, and publish the output only after a human approves that diff.
4. `evalagent` onboards a dataset. It pulls the files, reads the folder (JSON, README, vendor match scripts), and proposes a loader with `load(root) -> list[Example]` and `judge(work_dir, example) -> Verdict`. A human approves that loader before it is pinned or used for scoring.
5. `run_runner` copies only the files the agent is allowed to see into an isolated work directory, runs the configured agent entry point (for example `sheetagent.agent:build_agent`), calls `judge`, and appends each verdict to `runs/<run_id>/record.json`. Pass and fail come from the judge, not from the model's own summary.

Phoenix datasets hold JSON rows. Binary files stay on disk under the pinned root. Tracing stays on Phoenix via OpenTelemetry: a parent span `iagent.eval` and a child span `iagent.run` share `iagent.run_id`.

## Planned setup

```bash
uv sync --group dev
cp .env.example .env
```

`OPENROUTER_API_KEY` is required for a real model. Phoenix collector:

```
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
PHOENIX_PROJECT=chat-agent
```

Planned commands:

```bash
uv run px-pull
uv run sheetagent
uv run evalagent
uv run pytest
```

Benchmark judges that need formula results should recalculate the workbook (for example with LibreOffice 7.5+) before comparing cells. That step belongs next to the loader, not in the platform setup.

## Roadmap

### Platform (`iagent`)

- [ ] **Pins** — After `px-pull`, record SHA-256 of the pulled spec, skill, and (later) dataset and loader. Refuse runs when on-disk files do not match.
- [ ] **Run record** — `runs/<run_id>/record.json` with `run_id`, task or example id, spec and skill hashes, trace project, verdicts, and child trace ids. Phoenix experiments (dataset, task, evaluators) can be the system of record for scores and trace links.
- [ ] **Tracing** — Phoenix OpenTelemetry, with parent span `iagent.eval` and child span `iagent.run`.
- [ ] **Eval types** — `Example` (`id`, `instruction`, `files` visible to the agent, `judge_input` hidden from the platform) and `Verdict` (`passed`, `failures`, `explanation`, optional `details`).
- [ ] **`pull_dataset`** — Fetch Phoenix dataset rows and place dataset files on disk. Update pins. Return a path only.
- [ ] **`run_runner`** — Load the pinned loader, isolate each example, run the agent, call `judge`, append the verdict. `judge_input` is never copied into the work directory.
- [ ] **Loader pin** — Hash the loader next to the dataset pin (Phoenix dataset version id plus file manifest hash). A new or changed loader hash needs human approval before it is pinned.
- [ ] **Eval capability** — Harness capability that exposes `pull_dataset`, filesystem inspection, and `run_runner` to the eval agent.

### Spreadsheet workflow (`sheetagent`)

- [ ] **`Spreadsheet` capability** — YAML-configured, same style as `Shell` and `Coder`. Includes `inspect_workbook` (summary, read, headers, formulas, cross-sheet refs).
- [ ] **Script policy** — `check_script(path)`: allowed imports, no `to_excel` on formula workbooks, paths stay under the task root.
- [ ] **`prepare_run`** — Run the vetted `solution.py`, build the cell diff and structural errors. No human gate yet.
- [ ] **`commit_run`** — Publish the output workbook. Approval on the diff sits beside shell-command approval.
- [ ] **Spec** — `Spreadsheet:` block in `sheetagent/agent.yaml`, registered in `build_agent`.
- [ ] **Examples** — A toy task and one real task, with instructions and checks.

### Eval operator (`evalagent`)

- [ ] **Phoenix spec** — Pulled to `src/evalagent/agent.yaml`. No `Shell` or `Spreadsheet`. Uses the Eval capability and a workspace.
- [ ] **Onboarding** — Pull the dataset, inspect it, write `load` / `judge` (delegating to a vendor match script when one is present). The loader is approved by a human before it is pinned.
- [ ] **Monitor** — Call `run_runner`, read verdict rows from the record, fix the loader on failure, and quote the record in the final report.
- [ ] **CLI** — `uv run evalagent`, matching `sheetagent`.

### Quality

- [ ] Tests for pin mismatch, script policy, diff and `prepare_run`, a blocked commit, runner plus toy loader, `judge_input` absent from the work directory, rejection of an unapproved loader hash, and eval record integrity.
- [ ] `.env.example` kept in sync with the required variables.
- [ ] After the first benchmark run: a results table (task, pass or fail, loader hash, trace link).

## Out of scope

- No fixed dataset adapter types in platform code. Format discovery stays with the eval agent and the loader.
- No second domain capability besides Spreadsheet.
- The platform does not embed a specific benchmark's paths, test-case shape, or comparison logic. The loader owns that and may call vendor scripts from the pulled tree.
- The platform does not interpret `judge_input` or `Verdict.details`.
