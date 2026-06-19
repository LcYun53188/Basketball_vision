from __future__ import annotations

import cv2
import numpy as np
from typing import Any

from sport_vision.vision.calibration.config import NBA_REFERENCE_POINTS, NBA_3D_POINTS

def calibrate_from_points(clicked_points: list[list[float]], image_shape: tuple[int, int]) -> dict[str, Any] | None:
    """
    根据前端 UI 收集或保存的 8 个点击像素坐标点，在后台解算单应性矩阵 H 以及相机位姿 (PnP)。
    clicked_points 必须包含正好 8 个像素点：
      1-4 点为地面点（底线左角、底线右角、左罚球点、右罚球点）
      5-8 点为篮板点（篮板左下、右下、右上、左上）
    """
    if len(clicked_points) != 8:
        return None

    src_pts = np.array(clicked_points, dtype=np.float32)
    dst_pts = np.array(NBA_REFERENCE_POINTS, dtype=np.float32)

    # 1. 求解单应性矩阵 H (使用前4个地面点)
    H, _ = cv2.findHomography(src_pts[:4], dst_pts)
    # 2. 使用相机模块中配置的相机内参 K 与畸变系数
    from sport_vision.vision.camera.config import CAMERA_INTRINSICS
    fx = CAMERA_INTRINSICS["fx"]
    fy = CAMERA_INTRINSICS["fy"]
    cx = CAMERA_INTRINSICS["cx"]
    cy = CAMERA_INTRINSICS["cy"]
    camera_matrix = np.array([
        [fx, 0.0, cx],
        [0.0, fy, cy],
        [0.0, 0.0, 1.0]
    ], dtype=np.float32)
    dist_coeffs = np.array(CAMERA_INTRINSICS["distortion"], dtype=np.float32)
    
    # 3. 求解 PnP (使用全部 8 个 3D 点)
    object_pts_3d = np.array(NBA_3D_POINTS, dtype=np.float32)
    success, rvec, tvec = cv2.solvePnP(object_pts_3d, src_pts, camera_matrix, dist_coeffs)
    
    if not success:
        return None

    return {
        "H": H.tolist(),
        "K": camera_matrix.tolist(),
        "rvec": rvec.tolist(),
        "tvec": tvec.tolist()
    }


def project_point_to_court(H: list[list[float]] | np.ndarray, x: float, y: float) -> tuple[float, float]:
    """使用单应性矩阵将像素点投射到物理世界三维球场表面 (Z=0)"""
    H_arr = np.array(H, dtype=np.float32) if isinstance(H, list) else H
    pt = np.array([[[x, y]]], dtype=np.float32)
    mapped = cv2.perspectiveTransform(pt, H_arr)
    return float(mapped[0][0][0]), float(mapped[0][0][1])


def interactive_calibrate_from_frame(frame: np.ndarray) -> dict[str, Any] | None:
    """
    交互式标定（原 court_mapper.calibration 逻辑备份，供 CLI 工具运行）
    """
    print("=== 开始球场交互标定 ===")
    print("请按照以下顺序点击画面上的点：")
    print("1. 底线左侧角点 (Left Baseline Corner)")
    print("2. 底线右侧角点 (Right Baseline Corner)")
    print("3. 左侧罚球线端点 (Left Free Throw Point)")
    print("4. 右侧罚球线端点 (Right Free Throw Point)")
    print("5. 篮板左下角 (Backboard Bottom Left)")
    print("6. 篮板右下角 (Backboard Bottom Right)")
    print("7. 篮板右上角 (Backboard Top Right)")
    print("8. 篮板左上角 (Backboard Top Left)")
    print(" -> 选满 8 个点后，按 'c' 确认标定。")
    print(" -> 按 'r' 清除重选，按 'q' 强行退出。")

    clicked_points = []
    window_name = "Calibration Tool - Press 'c' to confirm"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(clicked_points) < 8:
                clicked_points.append([x, y])
                print(f"记录点 {len(clicked_points)}: ({x}, {y})")

    cv2.setMouseCallback(window_name, mouse_callback)

    while True:
        display = frame.copy()
        for i, pt in enumerate(clicked_points):
            cv2.circle(display, tuple(pt), 5, (0, 0, 255), -1)
            cv2.putText(display, f"P{i+1}", (pt[0]+10, pt[1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
        cv2.imshow(window_name, display)
        key = cv2.waitKey(20) & 0xFF
        
        if key == ord('c') and len(clicked_points) == 8:
            break
        elif key == ord('r'):
            clicked_points.clear()
            print("已清除重选。")
        elif key == ord('q') or key == 27:
            cv2.destroyWindow(window_name)
            return None

    cv2.destroyWindow(window_name)
    return calibrate_from_points(clicked_points, frame.shape[:2])
