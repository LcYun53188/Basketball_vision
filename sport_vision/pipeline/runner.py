from __future__ import annotations

from typing import List, Optional

from sport_vision.io.video_source import BaseVideoSource
from sport_vision.models import PoseComparisonResult, PoseFrameResult
from sport_vision.pose.analyzer import PoseAnalyzer
from sport_vision.pose.comparator import PoseComparator
from sport_vision.sinks.base import BaseSink


class Pipeline:
    def __init__(
        self,
        source: BaseVideoSource,
        analyzer: PoseAnalyzer,
        comparator: PoseComparator,
        sinks: List[BaseSink],
        max_frames: Optional[int] = None,
    ) -> None:
        self._source = source
        self._analyzer = analyzer
        self._comparator = comparator
        self._sinks = sinks
        self._max_frames = max_frames

    def run(self) -> None:
        self._source.open()
        frame_count = 0
        try:
            while True:
                packet = self._source.read()
                if packet is None:
                    break

                pose_result = self._analyzer.analyze(packet)
                compare_result = self._comparator.compare(pose_result.metrics)

                if not self._dispatch(packet, pose_result, compare_result):
                    break

                frame_count += 1
                if self._max_frames is not None and frame_count >= self._max_frames:
                    break
        finally:
            self._analyzer.close()
            self._source.release()
            for sink in self._sinks:
                sink.close()

    def _dispatch(
        self,
        packet,
        pose_result: PoseFrameResult,
        compare_result: PoseComparisonResult,
    ) -> bool:
        keep_running = True
        for sink in self._sinks:
            if not sink.handle(packet, pose_result, compare_result):
                keep_running = False
        return keep_running
