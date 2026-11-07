---
name: phoenix-eval
description: Write a Phoenix evaluator that calls a provided evaluation script. Use after the human gives that script and the experiment runner exists.
---

# Write the Phoenix evaluator

Follow this skill only after the human has given the path of the provided evaluation script, and `workspace/run_eval.py` already exists. Do not load this skill while asking for that path. This file is not the upload script and not the experiment task.

The shell working directory is `eval/`. The provided script is read-only. Read it to learn the function name and the arguments it expects. Do not modify it, do not copy its scoring rules into new code, and do not add checks it does not perform. If the function name or the arguments are unclear, stop and ask. Do not guess.

Write `workspace/evaluate.py`. It loads the provided script from the path the human gave and defines one Phoenix evaluator. `run_experiment` binds that function by argument name:

- `output` is the value the task returned, the one the human named. Do not assume it is a file. When the provided script needs a file and the task did not return one, stop and ask.
- `expected` is the example's `output` field from the upload script (the hidden answer). Read golden paths from here.

Call the provided function with those values, shaped the way that function expects. When it needs two files, pass the task's returned path and the golden path stored in `expected`. Return the provided function's result unchanged when it is a `bool`, a `float`, or a `str`. Phoenix treats a `bool` as pass/fail, a `float` as a score, and a `str` as a label. When the result is a mapping, pass through only the score, label, and explanation it already contains.

```python
"""Phoenix evaluator. Calls the provided script and does not reimplement it.

The shell working directory is eval/.
"""

import importlib.util
from pathlib import Path

PROVIDED = Path("dataset/official/evaluate.py")  # path the human gave


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("provided_eval", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_provided = _load(PROVIDED)


def evaluate(output, expected):
    # Replace this call with the function read from the provided script.
    return _provided.evaluate_example(output, expected)
```

Replace `PROVIDED` and the function call with what you read. Keep every field name identical to `workspace/upload_dataset.py`.

Then attach it in `workspace/run_eval.py` without changing the task:

```python
from evaluate import evaluate

client.experiments.run_experiment(
    dataset=dataset,
    task=task,
    evaluators=[evaluate],
    experiment_name=f"{DATASET_NAME}-agent",
    dry_run=1,
    timeout=600,
    retries=0,
)
```

`python workspace/run_eval.py` puts `workspace/` on the import path, so `import evaluate` resolves to this file. Do not run the experiment before this attachment. The first run stays `dry_run=1`. Report the printed summary, including the evaluator count. Run again with `dry_run=False` only after the human asks to record the experiment.
