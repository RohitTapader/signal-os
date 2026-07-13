from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class EvalRow:
    item_id: str
    label: str
    prediction: str
    confidence: float


def precision_recall_f1(rows: list[EvalRow], positive_label: str = "NEW") -> dict[str, float]:
    tp = sum(1 for r in rows if r.label == positive_label and r.prediction == positive_label)
    fp = sum(1 for r in rows if r.label != positive_label and r.prediction == positive_label)
    fn = sum(1 for r in rows if r.label == positive_label and r.prediction != positive_label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def load_jsonl(path: str | Path) -> list[EvalRow]:
    rows: list[EvalRow] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            rows.append(EvalRow(**obj))
    return rows
