from __future__ import annotations

import os

# 训练会话本地配置
UPLOAD_DIR = "outputs/uploads"
RECORD_DIR = "outputs/records"

# 自动创建目录
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RECORD_DIR, exist_ok=True)

# 录屏编码格式
RECORD_CODEC = "mp4v"  # H264 / mp4v 等
RECORD_FPS = 25
RECORD_RESOLUTION = (640, 480)
