from app.models import DetectionResult, TargetStatus
from app.modules.tracker import TargetTracker


def detection(bbox, label="red bottle", confidence=0.85):
    return DetectionResult(
        detection_id="det-1",
        label=label,
        confidence=confidence,
        bbox=bbox,
        prompt_version=1,
    )


def test_tracker_keeps_same_target_identity_when_object_moves():
    tracker = TargetTracker(lost_frame_buffer=2)
    target = tracker.lock(detection([10, 10, 90, 120]))

    updated = tracker.update([detection([25, 18, 105, 128])])

    assert updated is not None
    assert updated.target_id == target.target_id
    assert updated.tracker_id == target.tracker_id
    assert updated.status == TargetStatus.TRACKING


def test_tracker_marks_temporarily_lost_then_lost():
    tracker = TargetTracker(lost_frame_buffer=1)
    tracker.lock(detection([10, 10, 90, 120]))

    first = tracker.update([])
    first_status = first.status if first is not None else None
    second = tracker.update([])

    assert first is not None
    assert first_status == TargetStatus.TEMPORARILY_LOST
    assert second is not None
    assert second.status == TargetStatus.LOST


def test_tracker_does_not_switch_to_far_identical_object():
    tracker = TargetTracker(lost_frame_buffer=3)
    target = tracker.lock(detection([10, 10, 90, 120]))

    updated = tracker.update([detection([400, 300, 500, 430])])

    assert updated is not None
    assert updated.target_id == target.target_id
    assert updated.status == TargetStatus.TEMPORARILY_LOST
    assert updated.bbox == [10, 10, 90, 120]
