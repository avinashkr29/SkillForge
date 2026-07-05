from app.models import DetectionResult, ResolverStatus
from app.modules.candidate_resolver import CandidateResolver
from app.modules.coordinates import Point, Size, display_point_to_frame, frame_bbox_to_display


def detection(detection_id: str, bbox, confidence=0.8):
    return DetectionResult(
        detection_id=detection_id,
        label="red bottle",
        confidence=confidence,
        bbox=bbox,
        prompt_version=1,
    )


def test_resolver_auto_locks_single_candidate():
    result = CandidateResolver().resolve([detection("a", [10, 10, 100, 100])])

    assert result.status == ResolverStatus.AUTO_LOCKED
    assert result.selected_detection_id == "a"


def test_resolver_requires_selection_for_multiple_candidates():
    result = CandidateResolver().resolve(
        [
            detection("a", [10, 10, 100, 100]),
            detection("b", [120, 10, 200, 100]),
        ]
    )

    assert result.status == ResolverStatus.NEEDS_SELECTION
    assert result.selected_detection_id is None


def test_click_selects_containing_candidate():
    candidates = [detection("a", [10, 10, 100, 100]), detection("b", [120, 10, 200, 100])]

    selected = CandidateResolver().select_by_point(candidates, Point(150, 50))

    assert selected is not None
    assert selected.detection_id == "b"


def test_display_point_to_frame_scales_coordinates():
    point = display_point_to_frame(Point(160, 90), Size(320, 180), Size(640, 360))

    assert point == Point(320, 180)


def test_frame_bbox_to_display_scales_box():
    bbox = frame_bbox_to_display([100, 50, 300, 150], Size(400, 200), Size(200, 100))

    assert bbox == [50, 25, 150, 75]
