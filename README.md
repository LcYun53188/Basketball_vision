# Sport Vision Pose Module

This project implements the pose parsing module for a basketball coaching system.
It supports video files and USB cameras on Windows and is designed with high
cohesion and low coupling. Future modules are stubbed for goal detection and UI
reference overlays.

## Quick Start (Windows + venv)

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

### Video file

```bash
python -m sport_vision.main --video path\to\video.mp4
```

### USB camera

```bash
python -m sport_vision.main --camera 0
```

List and select cameras:

```bash
python -m sport_vision.main --list-cameras
python -m sport_vision.main --select-camera
```

## Options

- `--reference` Path to a JSON reference file.
- `--output` Output directory for JSONL results.
- `--no-preview` Disable preview window.
- `--no-json` Disable JSONL output.
- `--max-frames` Stop after N frames.
- `--list-cameras` List available cameras and exit.
- `--select-camera` Interactively select a camera index.
- `--camera-scan-max` Max index to probe when listing/selecting (default 5).

## Project Layout

- `sport_vision/io`: video sources (file, camera)
- `sport_vision/pose`: pose analyzer, metrics, comparison, rendering
- `sport_vision/pipeline`: pipeline runner
- `sport_vision/sinks`: output sinks (preview, JSONL)
- `sport_vision/future`: placeholders for goal detection and UI reference
- `configs/reference_default.json`: default metric ranges
