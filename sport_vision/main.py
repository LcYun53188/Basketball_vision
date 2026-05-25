from __future__ import annotations

import argparse
from pathlib import Path

from sport_vision.config import AppConfig, OutputConfig, SourceConfig
from sport_vision.io.video_source import CameraSource, VideoFileSource, list_available_cameras
from sport_vision.pipeline.runner import Pipeline
from sport_vision.pose.analyzer import PoseAnalyzer
from sport_vision.pose.comparator import PoseComparator
from sport_vision.pose.reference import load_reference
from sport_vision.sinks.json_sink import JsonSink
from sport_vision.sinks.preview_sink import PreviewSink


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pose parsing pipeline")
    parser.add_argument("--video", type=str, help="Path to a video file")
    parser.add_argument("--camera", type=int, help="Camera index, e.g. 0")
    parser.add_argument(
        "--list-cameras",
        action="store_true",
        help="List available cameras and exit",
    )
    parser.add_argument(
        "--select-camera",
        action="store_true",
        help="Interactively select a camera index",
    )
    parser.add_argument(
        "--camera-scan-max",
        type=int,
        default=5,
        help="Max camera index to probe when listing/selecting",
    )
    parser.add_argument("--reference", type=str, help="Reference JSON path")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--no-preview", action="store_true", help="Disable preview window")
    parser.add_argument("--no-json", action="store_true", help="Disable JSONL output")
    parser.add_argument("--max-frames", type=int, help="Stop after N frames")
    return parser.parse_args()


def _print_available_cameras(max_index: int) -> None:
    cameras = list_available_cameras(max_index)
    if cameras:
        print("Available cameras: " + ", ".join(str(idx) for idx in cameras))
    else:
        print("No cameras found.")


def _select_camera_index(max_index: int) -> int:
    cameras = list_available_cameras(max_index)
    if not cameras:
        raise SystemExit("No cameras found.")

    print("Available cameras: " + ", ".join(str(idx) for idx in cameras))
    while True:
        raw = input("Select camera index: ").strip()
        try:
            index = int(raw)
        except ValueError:
            print("Please enter a number.")
            continue
        if index in cameras:
            return index
        print(f"Camera index {index} is not available.")


def build_config(args: argparse.Namespace) -> AppConfig:
    if args.video and args.camera is not None:
        raise SystemExit("Choose either --video or --camera, not both.")
    if not args.video and args.camera is None:
        raise SystemExit("Provide --video or --camera.")

    if args.video:
        source = SourceConfig(kind="video", video_path=Path(args.video))
    else:
        source = SourceConfig(kind="camera", camera_index=int(args.camera))

    output = OutputConfig(
        output_dir=Path(args.output) if args.output else Path("outputs"),
        save_json=not args.no_json,
        preview=not args.no_preview,
        max_frames=args.max_frames,
    )

    config = AppConfig(source=source, output=output)
    if args.reference:
        config.reference_path = Path(args.reference)
    return config


def main() -> None:
    args = parse_args()
    if args.list_cameras:
        _print_available_cameras(args.camera_scan_max)
        return
    if args.select_camera:
        if args.camera is not None:
            raise SystemExit("Use --select-camera without --camera.")
        if args.video:
            raise SystemExit("Cannot use --select-camera with --video.")
        args.camera = _select_camera_index(args.camera_scan_max)
    config = build_config(args)

    reference = load_reference(config.reference_path)
    comparator = PoseComparator(reference)
    analyzer = PoseAnalyzer(config.pose)

    if config.source.kind == "video":
        source = VideoFileSource(config.source.video_path)
    else:
        source = CameraSource(config.source.camera_index)

    sinks = []
    if config.output.save_json:
        sinks.append(JsonSink(config.output.output_dir))
    if config.output.preview:
        sinks.append(PreviewSink(draw_skeleton=config.output.draw_skeleton))

    pipeline = Pipeline(
        source=source,
        analyzer=analyzer,
        comparator=comparator,
        sinks=sinks,
        max_frames=config.output.max_frames,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
