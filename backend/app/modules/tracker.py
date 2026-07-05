from __future__ import annotations

import itertools
from datetime import datetime, timezone
from typing import List, Optional

from app.models import DetectionResult, TargetState, TargetStatus


def bbox_iou(a: List[float], b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    a_area = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    b_area = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = a_area + b_area - intersection
    return intersection / union if union else 0


def center_distance(a: List[float], b: List[float]) -> float:
    acx = (a[0] + a[2]) / 2
    acy = (a[1] + a[3]) / 2
    bcx = (b[0] + b[2]) / 2
    bcy = (b[1] + b[3]) / 2
    return ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5


class TargetTracker:
    def __init__(self, lost_frame_buffer: int = 12):
        self.lost_frame_buffer = lost_frame_buffer
        self._target_counter = itertools.count(1)
        self._tracker_counter = itertools.count(17)
        self.target: Optional[TargetState] = None
        self.id_switches = 0
        self.lost_and_reacquired_count = 0

    def reset(self) -> None:
        self.target = None

    def lock(self, detection: DetectionResult) -> TargetState:
        target_num = next(self._target_counter)
        self.target = TargetState(
            target_id=f"target-{target_num:03d}",
            tracker_id=next(self._tracker_counter),
            label=detection.label,
            bbox=detection.bbox,
            confidence=detection.confidence,
            status=TargetStatus.LOCKED,
            last_seen_ts=datetime.now(timezone.utc),
            lost_frames=0,
        )
        return self.target

    def update(self, detections: List[DetectionResult]) -> Optional[TargetState]:
        if self.target is None:
            return None

        match = self._best_match(detections)
        was_lost = self.target.status in {TargetStatus.TEMPORARILY_LOST, TargetStatus.LOST}
        if match is not None:
            self.target.bbox = match.bbox
            self.target.confidence = match.confidence
            self.target.status = TargetStatus.TRACKING
            self.target.last_seen_ts = datetime.now(timezone.utc)
            self.target.lost_frames = 0
            if was_lost:
                self.lost_and_reacquired_count += 1
            return self.target

        self.target.lost_frames += 1
        if self.target.lost_frames <= self.lost_frame_buffer:
            self.target.status = TargetStatus.TEMPORARILY_LOST
        else:
            self.target.status = TargetStatus.LOST
        return self.target

    def _best_match(self, detections: List[DetectionResult]) -> Optional[DetectionResult]:
        if self.target is None:
            return None
        same_label = [detection for detection in detections if detection.label == self.target.label]
        scored = []
        for detection in same_label:
            iou = bbox_iou(self.target.bbox, detection.bbox)
            distance = center_distance(self.target.bbox, detection.bbox)
            max_dim = max(self.target.bbox[2] - self.target.bbox[0], self.target.bbox[3] - self.target.bbox[1], 1)
            if iou >= 0.15 or distance <= max_dim * 1.25:
                scored.append((iou, -distance, detection.confidence, detection))
        if not scored:
            return None
        scored.sort(reverse=True, key=lambda item: (item[0], item[1], item[2]))
        return scored[0][3]
