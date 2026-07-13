from __future__ import annotations

import json
from pathlib import Path

from signalos.evaluation.offline import EvalRow, precision_recall_f1


def run_offline_eval(jsonl_path: str) -> dict:
    rows = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(EvalRow(**json.loads(line)))
    return precision_recall_f1(rows)
