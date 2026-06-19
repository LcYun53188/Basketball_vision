from __future__ import annotations

# 运动员模块本地配置与阈值定义
ATHLETE_NAME_MAX_LENGTH = 50

# 默认的技术指标推荐区间设置（可根据年龄和位置进行微调）
DEFAULT_RECOMMENDATION_RULES = {
    "youth": {
        "guard": {
            "elbow_angle_deg": {"min": 75.0, "max": 155.0, "target": 115.0},
            "knee_angle_deg": {"min": 85.0, "max": 165.0, "target": 125.0},
            "torso_lean_deg": {"min": 2.0, "max": 18.0, "target": 10.0},
            "shoulder_tilt_deg": {"min": 0.0, "max": 10.0, "target": 4.0},
            "wrist_height_ratio": {"min": 0.25, "max": 0.75, "target": 0.50},
            "stance_width_ratio": {"min": 0.25, "max": 0.55, "target": 0.40},
        },
        "forward_center": {
            "elbow_angle_deg": {"min": 70.0, "max": 160.0, "target": 110.0},
            "knee_angle_deg": {"min": 80.0, "max": 170.0, "target": 130.0},
            "torso_lean_deg": {"min": 0.0, "max": 20.0, "target": 8.0},
            "shoulder_tilt_deg": {"min": 0.0, "max": 12.0, "target": 5.0},
            "wrist_height_ratio": {"min": 0.20, "max": 0.80, "target": 0.55},
            "stance_width_ratio": {"min": 0.20, "max": 0.60, "target": 0.45},
        }
    },
    "adult": {
        "guard": {
            "elbow_angle_deg": {"min": 70.0, "max": 160.0, "target": 112.0},
            "knee_angle_deg": {"min": 80.0, "max": 170.0, "target": 120.0},
            "torso_lean_deg": {"min": 0.0, "max": 20.0, "target": 8.2},
            "shoulder_tilt_deg": {"min": 0.0, "max": 12.0, "target": 3.5},
            "wrist_height_ratio": {"min": 0.20, "max": 0.80, "target": 0.62},
            "stance_width_ratio": {"min": 0.20, "max": 0.60, "target": 0.35},
        },
        "forward_center": {
            "elbow_angle_deg": {"min": 65.0, "max": 165.0, "target": 108.0},
            "knee_angle_deg": {"min": 75.0, "max": 175.0, "target": 125.0},
            "torso_lean_deg": {"min": 0.0, "max": 22.0, "target": 7.5},
            "shoulder_tilt_deg": {"min": 0.0, "max": 15.0, "target": 4.5},
            "wrist_height_ratio": {"min": 0.18, "max": 0.85, "target": 0.60},
            "stance_width_ratio": {"min": 0.22, "max": 0.65, "target": 0.42},
        }
    }
}
