from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import cv2

from sport_vision.models import Keypoint, MetricComparison


_CONNECTIONS: List[Tuple[str, str]] = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
]


def _to_pixel(kp: Keypoint, width: int, height: int) -> Tuple[int, int]:
    x_px = int(kp.x * width)
    y_px = int(kp.y * height)
    return x_px, y_px


def draw_pose(
    frame_bgr,
    keypoints: List[Keypoint],
    comparisons: Iterable[MetricComparison],
) -> None:
    height, width = frame_bgr.shape[:2]
    kp_map: Dict[str, Keypoint] = {kp.name: kp for kp in keypoints}

    for start, end in _CONNECTIONS:
        kp_start = kp_map.get(start)
        kp_end = kp_map.get(end)
        if kp_start is None or kp_end is None:
            continue
        x1, y1 = _to_pixel(kp_start, width, height)
        x2, y2 = _to_pixel(kp_end, width, height)
        cv2.line(frame_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)

    for kp in keypoints:
        x, y = _to_pixel(kp, width, height)
        cv2.circle(frame_bgr, (x, y), 3, (0, 255, 255), -1)

    y_offset = 20
    for cmp in comparisons:
        label = f"{cmp.name}: {cmp.status}"
        cv2.putText(
            frame_bgr,
            label,
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        y_offset += 18
