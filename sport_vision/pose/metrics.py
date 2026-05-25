from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from sport_vision.models import Keypoint, PoseMetrics


def _angle_deg(a: Keypoint, b: Keypoint, c: Keypoint) -> Optional[float]:
    ba = np.array([a.x - b.x, a.y - b.y], dtype=float)
    bc = np.array([c.x - b.x, c.y - b.y], dtype=float)
    if np.linalg.norm(ba) == 0.0 or np.linalg.norm(bc) == 0.0:
        return None
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    cos_angle = float(np.clip(cos_angle, -1.0, 1.0))
    return float(np.degrees(np.arccos(cos_angle)))


def _distance(a: Keypoint, b: Keypoint) -> float:
    return float(np.linalg.norm(np.array([a.x - b.x, a.y - b.y], dtype=float)))


def _midpoint(a: Keypoint, b: Keypoint) -> Keypoint:
    return Keypoint(
        name="mid",
        x=(a.x + b.x) / 2.0,
        y=(a.y + b.y) / 2.0,
        z=(a.z + b.z) / 2.0,
        visibility=min(a.visibility, b.visibility),
    )


def _choose_metric(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None and right is None:
        return None
    if left is None:
        return right
    if right is None:
        return left
    return (left + right) / 2.0


def compute_pose_metrics(landmarks: Dict[str, Keypoint]) -> PoseMetrics:
    left_shoulder = landmarks.get("left_shoulder")
    right_shoulder = landmarks.get("right_shoulder")
    left_elbow = landmarks.get("left_elbow")
    right_elbow = landmarks.get("right_elbow")
    left_wrist = landmarks.get("left_wrist")
    right_wrist = landmarks.get("right_wrist")
    left_hip = landmarks.get("left_hip")
    right_hip = landmarks.get("right_hip")
    left_knee = landmarks.get("left_knee")
    right_knee = landmarks.get("right_knee")
    left_ankle = landmarks.get("left_ankle")
    right_ankle = landmarks.get("right_ankle")

    left_elbow_angle = None
    if left_shoulder and left_elbow and left_wrist:
        left_elbow_angle = _angle_deg(left_shoulder, left_elbow, left_wrist)

    right_elbow_angle = None
    if right_shoulder and right_elbow and right_wrist:
        right_elbow_angle = _angle_deg(right_shoulder, right_elbow, right_wrist)

    left_knee_angle = None
    if left_hip and left_knee and left_ankle:
        left_knee_angle = _angle_deg(left_hip, left_knee, left_ankle)

    right_knee_angle = None
    if right_hip and right_knee and right_ankle:
        right_knee_angle = _angle_deg(right_hip, right_knee, right_ankle)

    elbow_angle = _choose_metric(left_elbow_angle, right_elbow_angle)
    knee_angle = _choose_metric(left_knee_angle, right_knee_angle)

    torso_lean = None
    shoulder_tilt = None
    wrist_height_ratio = None
    stance_width_ratio = None

    if left_shoulder and right_shoulder and left_hip and right_hip:
        shoulder_mid = _midpoint(left_shoulder, right_shoulder)
        hip_mid = _midpoint(left_hip, right_hip)
        torso_vec = np.array([shoulder_mid.x - hip_mid.x, shoulder_mid.y - hip_mid.y])
        if np.linalg.norm(torso_vec) > 0.0:
            vertical = np.array([0.0, -1.0])
            cos_angle = np.dot(torso_vec, vertical) / (
                np.linalg.norm(torso_vec) * np.linalg.norm(vertical)
            )
            cos_angle = float(np.clip(cos_angle, -1.0, 1.0))
            torso_lean = float(np.degrees(np.arccos(cos_angle)))

        shoulder_vec = np.array([
            right_shoulder.x - left_shoulder.x,
            right_shoulder.y - left_shoulder.y,
        ])
        if np.linalg.norm(shoulder_vec) > 0.0:
            horizontal = np.array([1.0, 0.0])
            cos_angle = np.dot(shoulder_vec, horizontal) / (
                np.linalg.norm(shoulder_vec) * np.linalg.norm(horizontal)
            )
            cos_angle = float(np.clip(cos_angle, -1.0, 1.0))
            shoulder_tilt = float(np.degrees(np.arccos(cos_angle)))

    if left_wrist and right_wrist and left_hip and right_hip and left_ankle and right_ankle:
        wrist = left_wrist if left_wrist.visibility >= right_wrist.visibility else right_wrist
        hip_mid = _midpoint(left_hip, right_hip)
        ankle_mid = _midpoint(left_ankle, right_ankle)
        body_height = _distance(hip_mid, ankle_mid)
        if body_height > 0.0:
            wrist_height_ratio = float((hip_mid.y - wrist.y) / body_height)
            stance_width_ratio = float(_distance(left_ankle, right_ankle) / body_height)

    return PoseMetrics(
        elbow_angle_deg=elbow_angle,
        knee_angle_deg=knee_angle,
        torso_lean_deg=torso_lean,
        shoulder_tilt_deg=shoulder_tilt,
        wrist_height_ratio=wrist_height_ratio,
        stance_width_ratio=stance_width_ratio,
    )
