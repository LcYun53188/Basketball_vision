# 第一阶段项目文档

## 1. 阶段目标

第一阶段聚焦“人物姿态解析 + 指标计算 + 参考值对比”，形成可运行的最小闭环。

## 2. 范围与非范围

范围内：

- 视频文件与 USB 摄像头输入。
- MediaPipe 姿态解析。
- 关键指标计算（角度与比例类指标）。
- 与参考值范围对比并输出结果。
- 预览窗口展示（骨架与指标状态）。
- JSONL 结构化输出。
- 预留接口与模块占位（进球检测、UI 参考姿态、报告生成）。

范围外：

- 进球检测与球轨迹。
- 多人场景与复杂遮挡处理。
- 训练数据管理与模型训练。
- 前端可视化系统与账户管理。

## 3. 交付物

- 姿态解析模块：`sport_vision/pose`。
- 输入源适配：`sport_vision/io`。
- 指标比较：`sport_vision/pose/comparator.py`。
- 输出：预览与 JSONL（`sport_vision/sinks`）。
- 示例参考值：`configs/reference_default.json`。

## 4. 核心指标

- `elbow_angle_deg`
- `knee_angle_deg`
- `torso_lean_deg`
- `shoulder_tilt_deg`
- `wrist_height_ratio`
- `stance_width_ratio`

指标均基于 MediaPipe 关键点计算，参考值通过 JSON 文件配置。

## 5. 数据输出

JSONL 每帧一行，包含：

- 帧号与时间戳
- 计算后的指标值
- 与参考值的对比结果（low/ok/high/missing）

## 6. 验收标准

- Windows + venv 环境可运行。
- 视频与 USB 摄像头均可获取姿态结果。
- 预览窗口可显示骨架与指标状态。
- JSONL 输出结构完整且可解析。
- 预留模块占位不影响运行。

## 7. 风险与缓解

- 光照与遮挡影响关键点精度：建议固定机位与均匀光源。
- 相机帧率不稳定：允许降帧或限制输出帧数。
- 指标阈值需要调优：用小样本数据做逐项校准。

## 8. 下一阶段对接

- 进球检测模块：`sport_vision/future/goal_detection.py`
- UI 参考姿态模块：`sport_vision/future/ui_reference.py`
- 报告生成模块：`sport_vision/future/reporting.py`
