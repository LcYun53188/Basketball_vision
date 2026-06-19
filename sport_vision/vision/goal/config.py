from __future__ import annotations

# 进球判定状态机本地阈值配置
MIN_DOWNWARD_SPEED = 1.5      # 判定为下降状态的最小垂直速度 (像素/帧)
ENTRY_EXIT_GAP_MIN = 3        # 进入篮筐口到离开筐底的最短帧数
ENTRY_EXIT_GAP_MAX = 20       # 进入篮筐口到离开筐底的最大时间窗口 (帧数)
GOAL_CONFIDENCE_THRESHOLD = 0.50
