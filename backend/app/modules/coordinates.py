from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Size:
    width: float
    height: float


@dataclass(frozen=True)
class Point:
    x: float
    y: float


def display_point_to_frame(point: Point, display: Size, frame: Size) -> Point:
    if display.width <= 0 or display.height <= 0:
        raise ValueError("display dimensions must be positive")
    return Point(x=point.x * frame.width / display.width, y=point.y * frame.height / display.height)


def frame_bbox_to_display(bbox: List[float], frame: Size, display: Size) -> List[float]:
    if frame.width <= 0 or frame.height <= 0:
        raise ValueError("frame dimensions must be positive")
    x_scale = display.width / frame.width
    y_scale = display.height / frame.height
    return [bbox[0] * x_scale, bbox[1] * y_scale, bbox[2] * x_scale, bbox[3] * y_scale]


def point_in_bbox(point: Point, bbox: List[float]) -> bool:
    x1, y1, x2, y2 = bbox
    return x1 <= point.x <= x2 and y1 <= point.y <= y2
