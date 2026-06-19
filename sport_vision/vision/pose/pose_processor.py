from __future__ import annotations

import os
import urllib.request
from typing import Dict, Any
import cv2
import mediapipe as mp
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

from sport_vision.vision.pose.config import (
    MODEL_ASSET_PATH,
    MIN_DETECTION_CONFIDENCE,
    MIN_TRACKING_CONFIDENCE,
)

LANDMARK_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner",
    "right_eye", "right_eye_outer", "left_ear", "right_ear", "mouth_left",
    "mouth_right", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky", "left_index",
    "right_index", "left_thumb", "right_thumb", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle", "left_heel",
    "right_heel", "left_foot_index", "right_foot_index"
]

class PoseProcessor:
    def __init__(self) -> None:
        # 如果本地没有模型权重文件，自动下载
        if not os.path.exists(MODEL_ASSET_PATH):
            print(f"下载 MediaPipe 姿态模型权重至 {MODEL_ASSET_PATH}...")
            url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
            urllib.request.urlretrieve(url, MODEL_ASSET_PATH)

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_ASSET_PATH),
            running_mode=VisionTaskRunningMode.VIDEO,
            min_pose_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
        )
        self._pose = PoseLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1

    def process_frame(self, frame_bgr: cv2.Mat, timestamp_ms: int) -> dict[str, Any]:
        """
        处理单帧图像，提取关键点并返回骨骼数据和足底中心点像素坐标
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        # 确保时间戳严格单调递增
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        result = self._pose.detect_for_video(mp_image, timestamp_ms)

        keypoints = []
        world_keypoints = []
        feet_pixel_midpoint = None

        if result.pose_landmarks and len(result.pose_landmarks) > 0:
            landmarks = result.pose_landmarks[0]
            for idx, lm in enumerate(landmarks):
                name = LANDMARK_NAMES[idx]
                keypoints.append({
                    "name": name,
                    "x": float(lm.x),
                    "y": float(lm.y),
                    "z": float(lm.z),
                    "visibility": float(lm.visibility if hasattr(lm, 'visibility') else getattr(lm, 'presence', 1.0))
                })

            # 提取 3D 物理空间关键点 (单位：米)
            if result.pose_world_landmarks and len(result.pose_world_landmarks) > 0:
                world_landmarks = result.pose_world_landmarks[0]
                for idx, lm in enumerate(world_landmarks):
                    name = LANDMARK_NAMES[idx]
                    world_keypoints.append({
                        "name": name,
                        "x": float(lm.x),
                        "y": float(lm.y),
                        "z": float(lm.z),
                        "visibility": float(lm.visibility if hasattr(lm, 'visibility') else getattr(lm, 'presence', 1.0))
                    })

            # 假设人物在球场上的触地点为左脚跟 (29) 和右脚跟 (30) 的像素中点
            h, w, _ = frame_bgr.shape
            left_heel = landmarks[29]
            right_heel = landmarks[30]
            
            lx, ly = left_heel.x * w, left_heel.y * h
            rx, ry = right_heel.x * w, right_heel.y * h
            
            feet_pixel_midpoint = (float((lx + rx) / 2), float((ly + ry) / 2))

        return {
            "keypoints": keypoints,
            "world_keypoints": world_keypoints,
            "feet_pixel_midpoint": feet_pixel_midpoint
        }

    def close(self) -> None:
        if self._pose:
            self._pose.close()
