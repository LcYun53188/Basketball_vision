from __future__ import annotations

import os
import urllib.request
from typing import Dict, List

import cv2
import mediapipe as mp
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

from sport_vision.config import PoseModelConfig
from sport_vision.models import Keypoint, PoseFrameResult
from sport_vision.pose.metrics import compute_pose_metrics

LANDMARK_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner",
    "right_eye", "right_eye_outer", "left_ear", "right_ear", "mouth_left",
    "mouth_right", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky", "left_index",
    "right_index", "left_thumb", "right_thumb", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle", "left_heel",
    "right_heel", "left_foot_index", "right_foot_index"
]


class PoseAnalyzer:
    def __init__(self, config: PoseModelConfig) -> None:
        if not os.path.exists(config.model_asset_path):
            print(f"Downloading {config.model_asset_path}...")
            url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
            urllib.request.urlretrieve(url, config.model_asset_path)

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=config.model_asset_path),
            running_mode=VisionTaskRunningMode.VIDEO,
            min_pose_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        self._pose = PoseLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1

    def analyze(self, packet) -> PoseFrameResult:
        rgb = cv2.cvtColor(packet.frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        timestamp_ms = int(packet.timestamp_ms)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        # MediaPipe Tasks API requires strictly monotonically increasing timestamps.
        result = self._pose.detect_for_video(mp_image, timestamp_ms)

        keypoints: List[Keypoint] = []
        if result.pose_landmarks and len(result.pose_landmarks) > 0:
            for idx, landmark in enumerate(result.pose_landmarks[0]):
                name = LANDMARK_NAMES[idx]
                keypoints.append(
                    Keypoint(
                        name=name,
                        x=float(landmark.x),
                        y=float(landmark.y),
                        z=float(landmark.z),
                        visibility=float(landmark.visibility if hasattr(landmark, 'visibility') else getattr(landmark, 'presence', 1.0)),
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
