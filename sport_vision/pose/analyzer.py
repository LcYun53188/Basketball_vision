from __future__ import annotations

from typing import Dict, List

import cv2
import mediapipe as mp

from sport_vision.config import PoseModelConfig
from sport_vision.models import Keypoint, PoseFrameResult
from sport_vision.pose.metrics import compute_pose_metrics


class PoseAnalyzer:
    def __init__(self, config: PoseModelConfig) -> None:
        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            model_complexity=config.model_complexity,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
            smooth_landmarks=config.smooth_landmarks,
        )

    def analyze(self, packet) -> PoseFrameResult:
        rgb = cv2.cvtColor(packet.frame_bgr, cv2.COLOR_BGR2RGB)
        result = self._pose.process(rgb)

        keypoints: List[Keypoint] = []
        if result.pose_landmarks:
            for idx, landmark in enumerate(result.pose_landmarks.landmark):
                name = self._mp_pose.PoseLandmark(idx).name.lower()
                keypoints.append(
                    Keypoint(
                        name=name,
                        x=float(landmark.x),
                        y=float(landmark.y),
                        z=float(landmark.z),
                        visibility=float(landmark.visibility),
                    )
                )

        metrics = None
        if keypoints:
            landmark_map: Dict[str, Keypoint] = {kp.name: kp for kp in keypoints}
            metrics = compute_pose_metrics(landmark_map)

        return PoseFrameResult(
            frame_index=packet.frame_index,
            timestamp_ms=packet.timestamp_ms,
            keypoints=keypoints,
            metrics=metrics,
        )

    def close(self) -> None:
        self._pose.close()
