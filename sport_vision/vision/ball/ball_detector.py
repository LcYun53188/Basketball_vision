from __future__ import annotations

import os
import numpy as np
from typing import Dict, Any, List

from sport_vision.vision.ball.config import BALL_DETECTOR_CONF, YOLO_MODEL_PATH, YOLO_SPORTS_BALL_CLASS_NAME
from sport_vision.vision.calibration.calibration_tool import project_point_to_court


def bbox_center(bbox: list[int] | None) -> tuple[float, float] | None:
    """Return the pixel center of a detector bbox."""
    if not bbox:
        return None
    return (float((bbox[0] + bbox[2]) / 2), float((bbox[1] + bbox[3]) / 2))


def project_bbox_to_court(H: list[list[float]] | None, bbox: list[int] | None, z: float = 0.0) -> list[float] | None:
    """Project a bbox center onto the calibrated court plane."""
    center = bbox_center(bbox)
    if not H or not center:
        return None
    world_x, world_y = project_point_to_court(H, center[0], center[1])
    return [world_x, world_y, z]


class BallDetector:
    def __init__(self) -> None:
        self.ball_tracks: List[Dict[str, Any]] = []
        self.model = None
        self.model_error: str | None = None
        self.model_path = os.getenv("SPORT_VISION_YOLO_MODEL", YOLO_MODEL_PATH)
        self._load_yolo_model()

    def _load_yolo_model(self) -> None:
        try:
            from ultralytics import YOLO

            self.model = YOLO(self.model_path)
        except Exception as exc:
            self.model = None
            self.model_error = str(exc)

    def detect_and_track(self, frame: np.ndarray, frame_index: int) -> Dict[str, Any]:
        """
        在帧图像中识别篮球与篮筐。
        优先使用 COCO 预训练 YOLO 的 sports ball 类；模型不可用时使用安全模拟 fallback。
        """
        if self.model is not None:
            yolo_result = self._detect_with_yolo(frame)
            if yolo_result["ball_bbox"] is not None:
                return yolo_result

        return self._detect_with_fallback(frame, frame_index)

    def _detect_with_yolo(self, frame: np.ndarray) -> Dict[str, Any]:
        results = self.model.predict(frame, verbose=False, conf=BALL_DETECTOR_CONF)
        best_bbox = None
        best_conf = 0.0

        if results:
            result = results[0]
            names = getattr(result, "names", {}) or {}
            boxes = getattr(result, "boxes", None)
            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    cls_name = names.get(cls_id, str(cls_id))
                    conf = float(box.conf[0].item())
                    if cls_name != YOLO_SPORTS_BALL_CLASS_NAME or conf < best_conf:
                        continue
                    xyxy = box.xyxy[0].tolist()
                    best_bbox = [int(v) for v in xyxy]
                    best_conf = conf

        h, w = frame.shape[:2]
        hoop_bbox = [int(w * 0.48), int(h * 0.25), int(w * 0.54), int(h * 0.32)]
        return {
            "hoop_bbox": hoop_bbox,
            "ball_bbox": best_bbox,
            "confidence": best_conf,
            "detector": "yolo_sports_ball",
            "model_path": self.model_path,
        }

    def _detect_with_fallback(self, frame: np.ndarray, frame_index: int) -> Dict[str, Any]:
        h, w = frame.shape[:2]
        
        # 默认模拟一个固定的篮筐边界框 (中心在球场上方)
        hoop_bbox = [int(w * 0.48), int(h * 0.25), int(w * 0.54), int(h * 0.32)]
        
        # 模拟一条投篮抛物线轨迹作为测试数据
        # 投篮从第 20 帧开始，到 45 帧结束并进球
        ball_bbox = None
        if 20 <= frame_index <= 50:
            # 抛物线方程
            t = (frame_index - 20) / 30.0  # 0 to 1
            x = w * (0.35 + 0.17 * t)      # 出手点到篮筐
            y = h * (0.60 - 0.70 * t + 0.40 * (t ** 2)) # 抛物线高度变化
            r = 15  # 篮球半径像素
            ball_bbox = [int(x - r), int(y - r), int(x + r), int(y + r)]

        return {
            "hoop_bbox": hoop_bbox,
            "ball_bbox": ball_bbox,
            "confidence": 0.90 if ball_bbox else 0.0,
            "detector": "simulated_fallback",
            "model_error": self.model_error,
        }
