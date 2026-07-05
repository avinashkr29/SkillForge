"""Color-based LEGO block detection using OpenCV."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class DetectedBlock:
    color: str
    center: tuple[int, int]
    bbox: tuple[int, int, int, int]  # x, y, w, h
    area: float
    confidence: float


COLOR_RANGES: dict[str, list[tuple[tuple[int, int, int], tuple[int, int, int]]]] = {
    "red": [
        ((0, 120, 70), (10, 255, 255)),
        ((170, 120, 70), (180, 255, 255)),
    ],
    "yellow": [
        ((20, 100, 100), (35, 255, 255)),
    ],
    "white": [
        ((0, 0, 180), (180, 40, 255)),
    ],
    "blue": [
        ((100, 120, 70), (130, 255, 255)),
    ],
    "green": [
        ((40, 80, 70), (85, 255, 255)),
    ],
    "orange": [
        ((10, 120, 100), (20, 255, 255)),
    ],
}

COLOR_BGR: dict[str, tuple[int, int, int]] = {
    "red": (0, 0, 255),
    "yellow": (0, 255, 255),
    "white": (255, 255, 255),
    "blue": (255, 0, 0),
    "green": (0, 255, 0),
    "orange": (0, 140, 255),
}


class BlockDetector:
    def __init__(
        self,
        min_area: int = 800,
        max_area: int = 80_000,
        min_confidence: float = 0.35,
    ) -> None:
        self.min_area = min_area
        self.max_area = max_area
        self.min_confidence = min_confidence

    def detect(self, frame: np.ndarray, colors: set[str] | None = None) -> list[DetectedBlock]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        active_colors = colors or set(COLOR_RANGES.keys())
        detections: list[DetectedBlock] = []

        for color in active_colors:
            if color not in COLOR_RANGES:
                continue
            detections.extend(self._detect_color(hsv, color))

        return self._deduplicate(detections)

    def _detect_color(self, hsv: np.ndarray, color: str) -> list[DetectedBlock]:
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lower, upper in COLOR_RANGES[color]:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, np.array(lower), np.array(upper)))

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        blocks: list[DetectedBlock] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area or area > self.max_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / max(h, 1)
            if aspect_ratio < 0.35 or aspect_ratio > 3.0:
                continue

            hull_area = max(cv2.contourArea(cv2.convexHull(contour)), 1.0)
            solidity = area / hull_area
            if solidity < 0.55:
                continue

            center = (x + w // 2, y + h // 2)
            confidence = min(1.0, solidity * (area / self.min_area) * 0.15)
            if confidence < self.min_confidence:
                continue

            blocks.append(
                DetectedBlock(
                    color=color,
                    center=center,
                    bbox=(x, y, w, h),
                    area=area,
                    confidence=confidence,
                )
            )

        return sorted(blocks, key=lambda block: block.confidence, reverse=True)

    def _deduplicate(self, detections: list[DetectedBlock]) -> list[DetectedBlock]:
        kept: list[DetectedBlock] = []
        for candidate in sorted(detections, key=lambda block: block.confidence, reverse=True):
            if all(self._centers_far_enough(candidate, existing) for existing in kept):
                kept.append(candidate)
        return kept

    @staticmethod
    def _centers_far_enough(a: DetectedBlock, b: DetectedBlock) -> bool:
        if a.color != b.color:
            return True
        distance = np.hypot(a.center[0] - b.center[0], a.center[1] - b.center[1])
        return distance > 40