from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PoseModelConfig:
    model_complexity: int = 1
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    smooth_landmarks: bool = True


@dataclass
class SourceConfig:
    kind: str
    video_path: Optional<Path] = None
    camera_index: int = 0


@dataclass
class OutputConfig:
    output_dir: Path = Path("outputs")
    save_json: bool = True
    preview: bool = True
    draw_skeleton: bool = True
    max_frames: Optional[int] = None


@dataclass
class AppConfig:
    source: SourceConfig
    pose: PoseModelConfig = field(default_factory=PoseModelConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    reference_path: Path = Path("configs/reference_default.json")
