---
name: dataset-upload
description: Write a Python script that uploads a local benchmark to Phoenix as JSON examples. Use when asked to upload, publish, or register a dataset.
---

# Upload a dataset to Phoenix

Follow this skill only when the agent instructions tell you to load `dataset-upload`. This file is the upload script, not the experiment runner.

The shell working directory is `eval/`. Write `workspace/upload_dataset.py` with paths relative to that directory (`dataset/...`, not `eval/dataset/...`). Do not modify anything under `dataset/`.

Stop after writing the script and ask for approval. Do not run it before the human approves. After approval, run:

```bash
python workspace/upload_dataset.py
```

Report the printed dataset id, name, version id, and both example counts. Do not claim the upload succeeded before that run.

Phoenix stores JSON rows only. Keep spreadsheets and other binary files on disk, and put their paths in the row. Do not read those files into the payload and do not base64-encode them.

## What goes in each example

Read `dataset.json` (or the JSON file the benchmark actually uses) before choosing keys. One JSON object is one Phoenix example.

- `input` is what the agent under test may see: the task id, the instruction, and the relative paths of files it should receive.
- `output` is the hidden answer: golden paths, expected values, and scoring criteria. Never move those fields into `input`.
- `metadata` records where the row came from: the repo-relative dataset directory and any category label.
- `id` is the stable id already in the row (`task_id` when present, otherwise `id`). Re-uploading the same id updates that example instead of creating a second one.

Path strings inside the JSON are relative to the directory that contains that JSON file. Store them unchanged.

## Script

Set `DATASET_ROOT` to the benchmark directory as seen from the repository root, for example `eval/dataset/Visualization`. Change the input and output keys to match the file you read. This template matches the Visualization `dataset.json`; other benchmarks will name their fields differently.

```python
"""Upload one on-disk benchmark to Phoenix. The shell working directory is eval/."""

import json
from pathlib import Path

from phoenix.client import Client

DATASET_ROOT = Path("dataset/Visualization")
PHOENIX_NAME = "visualization"


def examples_from(root: Path) -> list[dict]:
    rows = json.loads((root / "dataset.json").read_text(encoding="utf-8"))
    examples = []
    for row in rows:
        files = [row[key] for key in ("spreadsheet_path",) if row.get(key)]
        examples.append(
            {
                "id": str(row.get("task_id") or row["id"]),
                "input": {
                    "id": row["id"],
                    "instruction": row["instruction"],
                    "files": files,
                },
                "output": {
                    "golden_response_path": row.get("golden_response_path"),
                    "criteria": row.get("criteria", []),
                },
                "metadata": {
                    "category": row.get("category"),
                    "dataset_root": root.as_posix(),
                },
            }
        )
    return examples


def main() -> None:
    examples = examples_from(DATASET_ROOT)
    dataset = Client().datasets.create_dataset(
        name=PHOENIX_NAME,
        dataset_description=f"Rows from {DATASET_ROOT.as_posix()}",
        examples=examples,
    )
    print(dataset.id, dataset.name, dataset.version_id, len(examples), dataset.example_count)


if __name__ == "__main__":
    main()
```

`Client()` reads `PHOENIX_ENDPOINT` or `PHOENIX_COLLECTOR_ENDPOINT`, and `PHOENIX_API_KEY` when the server requires one. Do not write keys, tokens, or `.env` contents into the script.

`create_dataset` replaces the examples of that Phoenix name with the list in the script. To add rows without replacing the existing ones, call `client.datasets.add_examples_to_dataset(dataset=PHOENIX_NAME, examples=examples)` instead.

After the person runs the script, the last line is the dataset id, name, version id, number of rows sent, and number of examples Phoenix stored. Those two counts must match. Report that line. Do not claim the upload succeeded before the script has been run.
