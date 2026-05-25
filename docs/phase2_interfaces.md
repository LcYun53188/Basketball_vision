# 下一阶段接口说明

本文档用于描述第二阶段与后续模块的接口规范，确保第一阶段姿态解析模块可无缝对接。

## 1. 模块边界

- 姿态解析模块（已完成）：输出关键点与指标比较结果。
- 进球检测模块（待实现）：输入视频帧或球轨迹，输出进球事件与类型。
- UI 参考姿态模块（待实现）：提供标准姿态序列与对齐信息。
- 报告生成模块（待实现）：根据结构化结果生成报告文本。

## 2. 统一数据结构

### 2.1 帧级输入

```json
{
  "frame_index": 120,
  "timestamp_ms": 4020.5,
  "frame_bgr": "<ndarray>"
}
```

### 2.2 姿态解析输出（帧级）

```json
{
  "frame_index": 120,
  "timestamp_ms": 4020.5,
  "keypoints": [
    {"name": "left_shoulder", "x": 0.52, "y": 0.41, "z": -0.12, "visibility": 0.95}
  ],
  "metrics": {
    "elbow_angle_deg": 112.3,
    "knee_angle_deg": 144.0,
    "torso_lean_deg": 8.2,
    "shoulder_tilt_deg": 3.5,
    "wrist_height_ratio": 0.62,
    "stance_width_ratio": 0.35
  },
  "comparisons": [
    {"name": "elbow_angle_deg", "value": 112.3, "status": "ok", "min_value": 70, "max_value": 160}
  ]
}
```

## 3. 进球检测模块接口

### 3.1 输入

- 原始帧流或关键帧序列。
- 篮筐、篮球检测结果（可选）。
- 标定数据（篮筐位置与场地平面）。

### 3.2 输出

```json
{
  "event_id": "goal_00023",
  "frame_index": 1320,
  "timestamp_ms": 44050.0,
  "goal_type": "rim_in",
  "score_value": 2,
  "confidence": 0.82,
  "key_timestamps": {
    "release_ts": 43520.0,
    "rim_entry_ts": 43980.0,
    "rim_exit_ts": 44050.0
  }
}
```

## 4. UI 参考姿态模块接口

### 4.1 输入

- 运动项目与动作类型。
- 参考模板 ID 或训练阶段。

### 4.2 输出

```json
{
  "template_id": "shooting_basic_v1",
  "sequence": [
    {"t": 0.0, "keypoints": [{"name": "left_shoulder", "x": 0.5, "y": 0.4}]} 
  ],
  "alignment": {
    "anchor": "release",
    "duration_ms": 1200
  }
}
```

## 5. 报告生成模块接口

### 5.1 输入

- 训练会话 ID。
- 姿态指标统计与进球事件。
- 推荐值偏差与趋势数据。

### 5.2 输出

```json
{
  "session_id": "session_20260525_01",
  "summary": "本次训练出手角度稳定，命中率略低于目标区间...",
  "recommendations": ["提高出手高度", "强化下肢发力"]
}
```

## 6. 对接建议

- 统一时间戳与帧索引，确保跨模块对齐。
- JSON 结构尽量保持字段稳定，避免破坏兼容性。
- 对关键字段（如事件类型、动作类型）使用枚举或字典配置。
