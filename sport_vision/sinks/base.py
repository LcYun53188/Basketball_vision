from __future__ import annotations

from abc import ABC, abstractmethod

from sport_vision.models import PoseComparisonResult, PoseFrameResult


class BaseSink(ABC):
    @abstractmethod
    def handle(self, packet, pose: PoseFrameResult, compare: PoseComparisonResult) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        return None
