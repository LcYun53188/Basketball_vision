from __future__ import annotations

from typing import List, Optional

from sport_vision.models import MetricComparison, PoseComparisonResult, PoseMetrics
from sport_vision.pose.reference import PoseReference


class PoseComparator:
    def __init__(self, reference: PoseReference) -> None:
        self._reference = reference

    def compare(self, metrics: Optional[PoseMetrics]) -> PoseComparisonResult:
        comparisons: List[MetricComparison] = []
        for name, metric_range in self._reference.ranges.items():
            value = None if metrics is None else getattr(metrics, name, None)
            status = "missing"
            if value is not None:
                if value < metric_range.min_value:
                    status = "low"
                elif value > metric_range.max_value:
                    status = "high"
                else:
                    status = "ok"

            comparisons.append(
                MetricComparison(
                    name=name,
                    value=value,
                    status=status,
                    min_value=metric_range.min_value,
                    max_value=metric_range.max_value,
                )
            )
        return PoseComparisonResult(comparisons=comparisons)
