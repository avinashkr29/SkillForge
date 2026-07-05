from __future__ import annotations

from typing import List, Optional

from app.models import CandidateResolution, DetectionResult, ResolverStatus
from app.modules.coordinates import Point, point_in_bbox


class CandidateResolver:
    def __init__(self, confidence_threshold: float = 0.35):
        self.confidence_threshold = confidence_threshold

    def resolve(self, detections: List[DetectionResult]) -> CandidateResolution:
        candidates = [detection for detection in detections if detection.confidence >= self.confidence_threshold]
        if not candidates:
            return CandidateResolution(status=ResolverStatus.OBJECT_NOT_FOUND, candidates=[])
        if len(candidates) == 1:
            return CandidateResolution(
                status=ResolverStatus.AUTO_LOCKED,
                selected_detection_id=candidates[0].detection_id,
                candidates=candidates,
            )
        return CandidateResolution(status=ResolverStatus.NEEDS_SELECTION, candidates=candidates)

    def select_by_point(self, candidates: List[DetectionResult], point: Point) -> Optional[DetectionResult]:
        containing = [candidate for candidate in candidates if point_in_bbox(point, candidate.bbox)]
        if not containing:
            return None
        return max(containing, key=lambda candidate: candidate.confidence)
