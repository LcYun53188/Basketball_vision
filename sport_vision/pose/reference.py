from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass
class MetricRange:
    min_value: float
    max_value: float


@dataclass
class PoseReference:
    ranges: Dict[str, MetricRange]


def load_reference(path: Path) -> PoseReference:
    data = json.loads(path.read_text(encoding="utf-8"))
    ranges = {}
    for name, spec in data.get("metrics", {}).items():
        ranges[name] = MetricRange(
            min_value=float(spec["min"]),
            max_value=float(spec["max"]),
        )
    return PoseReference(ranges=ranges)
