from __future__ import annotations

# 相机内参及畸变系数 (数据源自 标定与校准方案.md)
CAMERA_INTRINSICS = {
    "fx": 1180.5,
    "fy": 1182.1,
    "cx": 960.0,
    "cy": 540.0,
    "distortion": [0.01, -0.03, 0.0, 0.0, 0.0]
}

# 相机外参（旋转矩阵、平移向量）
CAMERA_EXTRINSICS = {
    "rotation": [
        [0.99, 0.02, 0.04],
        [-0.01, 0.99, -0.03],
        [-0.04, 0.03, 0.99]
    ],
    "translation": [1.2, 3.8, 2.6]
}
