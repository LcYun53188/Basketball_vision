from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

from sport_vision.vision.ball.ball_detector import bbox_center
from sport_vision.vision.ball.config import BASKETBALL_DIAMETER_M
from sport_vision.vision.camera.config import CAMERA_INTRINSICS


def camera_matrix_from_calibration(calibration_data: dict[str, Any] | None) -> np.ndarray:
    """Return camera matrix K from session calibration or default camera config."""
    if calibration_data and calibration_data.get("K"):
        return np.array(calibration_data["K"], dtype=np.float32)

    return np.array(
        [
            [CAMERA_INTRINSICS["fx"], 0.0, CAMERA_INTRINSICS["cx"]],
            [0.0, CAMERA_INTRINSICS["fy"], CAMERA_INTRINSICS["cy"]],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )


def estimate_ball_world_from_bbox(
    bbox: list[int] | None,
    calibration_data: dict[str, Any] | None,
    ball_diameter_m: float = BASKETBALL_DIAMETER_M,
) -> list[float] | None:
    """
    Estimate basketball center in court/world coordinates from one monocular bbox.

    Assumptions:
    - calibration_data contains PnP output rvec/tvec mapping world -> camera.
    - bbox pixel diameter approximates the projected basketball diameter.
    - ball_diameter_m is known. This is an engineering estimate, not multi-view 3D.
    """
    center = bbox_center(bbox)
    if not center or not calibration_data:
        return None
    if not calibration_data.get("rvec") or not calibration_data.get("tvec"):
        return None

    pixel_diameter = max(float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1]))
    if pixel_diameter <= 1.0:
        return None

    K = camera_matrix_from_calibration(calibration_data)
    fx = float(K[0, 0])
    fy = float(K[1, 1])
    cx = float(K[0, 2])
    cy = float(K[1, 2])
    focal_px = (fx + fy) / 2.0

    depth_cam = focal_px * ball_diameter_m / pixel_diameter
    if not math.isfinite(depth_cam) or depth_cam <= 0:
        return None

    u, v = center
    x_cam = (u - cx) * depth_cam / fx
    y_cam = (v - cy) * depth_cam / fy
    point_cam = np.array([[x_cam], [y_cam], [depth_cam]], dtype=np.float32)

    rvec = np.array(calibration_data["rvec"], dtype=np.float32).reshape(3, 1)
    tvec = np.array(calibration_data["tvec"], dtype=np.float32).reshape(3, 1)
    rotation, _ = cv2.Rodrigues(rvec)

    point_world = rotation.T @ (point_cam - tvec)
    return [
        float(point_world[0, 0]),
        float(point_world[1, 0]),
        float(point_world[2, 0]),
    ]
