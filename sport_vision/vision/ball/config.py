from __future__ import annotations

# 篮球与篮筐识别本地配置
BALL_DETECTOR_CONF = 0.40
HOOP_DETECTOR_CONF = 0.50
MIN_TRACK_LEN = 10
RIM_MARGIN = 5  # 篮筐膨胀像素

# YOLO COCO 预训练模型中 sports ball 的类别名；模型文件可用环境变量覆盖。
YOLO_MODEL_PATH = "yolo11n.pt"
YOLO_SPORTS_BALL_CLASS_NAME = "sports ball"

# 标准篮球直径近似值：7 号球约 0.24m。用于单目 bbox 尺寸估深度。
BASKETBALL_DIAMETER_M = 0.24
