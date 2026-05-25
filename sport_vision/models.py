from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np


@dataclass
class FramePacket:
    frame_index: int
    timestamp_ms: float
    frame_bgr: np.ndarray


@dataclass
class Keypoint:
    name: str
    x: float
    y: float
    z: float
    visibility: float


@dataclass
class PoseMetrics:
    elbow_angle_deg: Optional[float] = None
    knee_angle_deg: Optional[float] = None
    torso_lean_deg: Optional[float] = None
    shoulder_tilt_deg: Optional[float] = None
    wrist_height_ratio: Optional[float] = None
    stance_width_ratio: Optional[float] = None


@dataclass
class MetricComparison:
    name: str
    value: Optional[float]
    status: str
    min_value: Optional[float]
    max_value: Optional[float]


@dataclass
class PoseFrameResult:
    frame_index: int
    timestamp_ms: float
    keypoints: List[Keypoint]
    metrics: Optional[PoseMetrics]


@dataclass
class PoseComparisonResult:
    comparisons: List[MetricComparison]
