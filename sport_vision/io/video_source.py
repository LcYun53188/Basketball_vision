from __future__ import annotations

from abc import ABC, abstractmethod
import os
import threading
import time
from pathlib import Path
from typing import List, Optional

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


def list_available_cameras(max_index: int = 5) -> List[int]:
    available: List[int] = []
    if max_index < 0:
        return available

    for index in range(max_index + 1):
        if os.name == "nt":
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(index)

        if cap is not None and cap.isOpened():
            available.append(index)

        if cap is not None:
            cap.release()

    return available


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
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._latest_frame = None
        self._latest_timestamp_ms = 0.0
        self._frame_ready_event = threading.Event()

    def open(self) -> None:
        if os.name == "nt":
            self._cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        else:
            self._cap = cv2.VideoCapture(self._camera_index)
            
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open camera: {self._camera_index}")
            
        # Try to set buffer size to 1 to reduce latency (may not be supported on all drivers)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Start a background thread to continuously read frames
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        while not self._stop_event.is_set() and self._cap is not None:
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.01)
                continue
                
            timestamp_ms = time.time() * 1000.0  # Use system time for real-time camera
            with self._lock:
                self._latest_frame = frame
                self._latest_timestamp_ms = timestamp_ms
            self._frame_ready_event.set()

    def read(self) -> Optional[FramePacket]:
        if self._cap is None:
            raise RuntimeError("Camera source not opened")

        # Wait for a new frame
        if not self._frame_ready_event.wait(timeout=2.0):
            return None
            
        with self._lock:
            frame = self._latest_frame
            timestamp_ms = self._latest_timestamp_ms
            self._frame_ready_event.clear()
            
        if frame is None:
            return None

        packet = FramePacket(
            frame_index=self._frame_index,
            timestamp_ms=timestamp_ms,
            frame_bgr=frame.copy(),
        )
        self._frame_index += 1
        return packet

    def release(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            
        if self._cap is not None:
            self._cap.release()
            self._cap = None
