from __future__ import annotations

# 人体动作检测与比对本地配置
ACTION_WINDOW_SIZE = 30  # 时序识别滑动窗口大小 (帧数)

# 标准动作对比阈值设定（当 compare_with_reference=True 时起作用）
# 各项物理动作指标的“完美区间”以及偏差容忍值
STANDARD_SHOOTING_TEMPLATES = {
    "elbow_angle_deg": {"min": 70.0, "max": 160.0, "label": "出手肘关节夹角"},
    "knee_angle_deg": {"min": 80.0, "max": 170.0, "label": "起跳膝关节夹角"},
    "torso_lean_deg": {"min": 0.0, "max": 20.0, "label": "躯干前倾角度"},
    "shoulder_tilt_deg": {"min": 0.0, "max": 12.0, "label": "双肩倾斜角度"},
    "wrist_height_ratio": {"min": 0.20, "max": 0.80, "label": "手腕高度比例"},
    "stance_width_ratio": {"min": 0.20, "max": 0.60, "label": "双脚站姿宽度比例"}
}

# 动作类别定义
ACTION_CLASSES = [
    "shooting",       # 投篮
    "dribbling",      # 运球
    "passing",        # 传球
    "defense_stance", # 防守姿态
    "idle"            # 静态待机
]
