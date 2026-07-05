from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np


@dataclass
class VideoStatus:
    is_open: bool
    width: int
    height: int
    fps: float
    frame_id: int


class VideoSource:
    def __init__(self, source: Union[int, str] = 0):
        self.source = source
        self.capture: Optional[cv2.VideoCapture] = None
        self.frame_id = 0
        self._last_frame_ts = 0.0
        self._fps = 0.0

    def start(self) -> None:
        self.capture = cv2.VideoCapture(self.source)
        if not self.capture.isOpened():
            raise RuntimeError(f"Could not open video source {self.source}")

    def stop(self) -> None:
        if self.capture is not None:
            self.capture.release()
        self.capture = None

    def read_frame(self) -> Tuple[int, np.ndarray]:
        if self.capture is None:
            self.start()
        assert self.capture is not None
        ok, frame = self.capture.read()
        if not ok:
            raise RuntimeError("No frame available from video source")
        self.frame_id += 1
        now = time.perf_counter()
        if self._last_frame_ts:
            delta = now - self._last_frame_ts
            self._fps = 1 / delta if delta > 0 else 0
        self._last_frame_ts = now
        return self.frame_id, frame

    def status(self) -> VideoStatus:
        capture = self.capture
        is_open = bool(capture and capture.isOpened())
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) if capture else 0
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) if capture else 0
        native_fps = float(capture.get(cv2.CAP_PROP_FPS)) if capture else 0
        return VideoStatus(is_open=is_open, width=width, height=height, fps=self._fps or native_fps, frame_id=self.frame_id)


def read_video_frames(path: Path, max_frames: int = 120) -> list[np.ndarray]:
    capture = cv2.VideoCapture(str(path))
    frames: list[np.ndarray] = []
    try:
        while len(frames) < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            frames.append(frame)
    finally:
        capture.release()
    return frames
