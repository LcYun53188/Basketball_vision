from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from sport_vision.models import PoseComparisonResult, PoseFrameResult
from sport_vision.sinks.base import BaseSink


class JsonSink(BaseSink):
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._output_dir / "pose_metrics.jsonl"
        self._file = self._path.open("w", encoding="utf-8")

    def handle(self, packet, pose: PoseFrameResult, compare: PoseComparisonResult) -> bool:
        record = {
            "frame_index": pose.frame_index,
            "timestamp_ms": pose.timestamp_ms,
            "metrics": None if pose.metrics is None else asdict(pose.metrics),
            "comparisons": [asdict(cmp) for cmp in compare.comparisons],
        }
        self._file.write(json.dumps(record) + "\n")
        return True

    def close(self) -> None:
        self._file.close()
