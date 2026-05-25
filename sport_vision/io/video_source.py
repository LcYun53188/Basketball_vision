from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Optional

import cv2

from sport_vision.models import FramePacket


class BaseVideoSource(ABC):
    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self) -> Optional[FramePacket]:
        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        raise NotImplementedError


class VideoFileSource(BaseVideoSource):
    def __init__(self, video_path: Path) -> None:
        self._video_path = video_path
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_index = 0

    def open(self) -> None:
        self._cap = cv2.VideoCapture(str(self._video_path))
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video: {self._video_path}")

    def read(self) -> Optional[FramePacket]:
        if self._cap is None:
            raise RuntimeError("Video source not opened")

        ok, frame = self._cap.read()
        if not ok:
            return None

        timestamp_ms = float(self._cap.get(cv2.CAP_PROP_POS_MSEC))
        packet = FramePacket(
            frame_index=self._frame_index,
            timestamp_ms=timestamp_ms,
            frame_bgr=frame,
        )
        self._frame_index += 1
        return packet

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class CameraSource(BaseVideoSource):
    def __init__(self, camera_index: int = 0) -> None:
        self._camera_index = camera_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_index = 0

    def open(self) -> None:
        if os.name == "nt":
            self._cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        else:
            self._cap = cv2.VideoCapture(self._camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open camera: {self._camera_index}")

    def read(self) -> Optional[FramePacket]:
        if self._cap is None:
            raise RuntimeError("Camera source not opened")

        ok, frame = self._cap.read()
        if not ok:
            return None

        timestamp_ms = float(self._cap.get(cv2.CAP_PROP_POS_MSEC))
        packet = FramePacket(
            frame_index=self._frame_index,
            timestamp_ms=timestamp_ms,
            frame_bgr=frame,
        )
        self._frame_index += 1
        return packet

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
