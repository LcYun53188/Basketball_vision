# 使用方法

## 1. 环境准备（Windows + venv）

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. 运行方式

### 2.1 视频文件

```bash
python -m sport_vision.main --video path\to\video.mp4
```

### 2.2 USB 摄像头

```bash
python -m sport_vision.main --camera 0
```

如果需要选择摄像头：

```bash
python -m sport_vision.main --list-cameras
python -m sport_vision.main --select-camera
```

## 3. 常用参数

- `--reference` 指定参考值 JSON 文件路径。
- `--output` 输出目录（默认 `outputs`）。
- `--no-preview` 关闭预览窗口。
- `--no-json` 关闭 JSONL 输出。
- `--max-frames` 限制处理帧数。
- `--list-cameras` 列出可用摄像头并退出。
- `--select-camera` 交互式选择摄像头索引。
- `--camera-scan-max` 列出/选择时探测的最大索引（默认 5）。

示例：

```bash
python -m sport_vision.main --camera 0 --reference configs\reference_default.json --output outputs
```

## 4. 输出说明

- JSONL 输出文件：`outputs/pose_metrics.jsonl`
- 每行包含帧号、时间戳、指标与对比状态。

## 5. 参考值配置

参考值文件示例位于 `configs/reference_default.json`，可按项目需求修改范围。

## 6. 常见问题

- 无法打开摄像头：检查索引（0/1/2）并确保摄像头未被占用。
- 画面卡顿：关闭预览或降低分辨率后再试。
- 指标异常：确认关键点识别稳定后再做阈值调整。
