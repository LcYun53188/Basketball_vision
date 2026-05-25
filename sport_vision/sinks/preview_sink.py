from __future__ import annotations

import cv2

from sport_vision.models import PoseComparisonResult, PoseFrameResult
from sport_vision.pose.render import draw_pose
from sport_vision.sinks.base import BaseSink


class PreviewSink(BaseSink):
    def __init__(self, draw_skeleton: bool = True) -> None:
        self._draw_skeleton = draw_skeleton
        self._window_name = "Pose Preview"

    def handle(self, packet, pose: PoseFrameResult, compare: PoseComparisonResult) -> bool:
        frame = packet.frame_bgr.copy()
        if self._draw_skeleton:
            draw_pose(frame, pose.keypoints, compare.comparisons)

        cv2.imshow(self._window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            return False
        return True

    def close(self) -> None:
        cv2.destroyAllWindows()
