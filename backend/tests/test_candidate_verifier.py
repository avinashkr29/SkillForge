import cv2
import numpy as np

from app.config import Settings
from app.models import DetectionResult
from app.modules.candidate_verifier import CandidateVerifier


def detection(detection_id, bbox, confidence=0.65):
    return DetectionResult(
        detection_id=detection_id,
        label="black smart phone",
        confidence=confidence,
        bbox=bbox,
        prompt_version=1,
    )


def test_context_verifier_auto_selects_phone_like_candidate():
    frame = np.full((360, 640, 3), 210, dtype=np.uint8)
    cv2.rectangle(frame, (0, 0), (120, 360), (8, 8, 8), -1)
    cv2.rectangle(frame, (285, 170), (410, 220), (25, 25, 25), -1)
    cv2.circle(frame, (325, 190), 20, (5, 5, 5), -1)
    cv2.rectangle(frame, (420, 60), (600, 145), (12, 12, 14), -1)
    cv2.circle(frame, (555, 82), 12, (60, 60, 65), -1)

    verifier = CandidateVerifier(
        Settings(
            OPENAI_API_KEY=None,
            YOLOE_MODEL_PATH="mock://color",
            CONTEXT_AUTO_LOCK_MIN_SCORE=0.55,
            CONTEXT_AUTO_LOCK_MARGIN=0.10,
        )
    )
    decision, latency_ms = verifier.verify(
        frame,
        "black smart phone",
        [
            detection("edge", [0, 0, 120, 360], confidence=0.9),
            detection("glasses", [285, 170, 410, 220], confidence=0.7),
            detection("phone", [420, 60, 600, 145], confidence=0.7),
        ],
    )

    assert latency_ms >= 0
    assert decision.selected_detection_id == "phone"
    assert decision.mode == "local-context"


def test_context_verifier_keeps_manual_selection_when_margin_is_small():
    frame = np.full((240, 320, 3), 210, dtype=np.uint8)
    cv2.rectangle(frame, (40, 60), (140, 115), (15, 15, 15), -1)
    cv2.rectangle(frame, (180, 60), (280, 115), (15, 15, 15), -1)

    verifier = CandidateVerifier(
        Settings(
            OPENAI_API_KEY=None,
            YOLOE_MODEL_PATH="mock://color",
            CONTEXT_AUTO_LOCK_MIN_SCORE=0.55,
            CONTEXT_AUTO_LOCK_MARGIN=0.25,
        )
    )
    decision, _ = verifier.verify(
        frame,
        "black smart phone",
        [
            detection("left", [40, 60, 140, 115]),
            detection("right", [180, 60, 280, 115]),
        ],
    )

    assert decision.selected_detection_id is None


def test_context_verifier_checks_single_bottle_candidate():
    frame = np.full((360, 640, 3), 210, dtype=np.uint8)
    cv2.rectangle(frame, (260, 80), (340, 300), (210, 230, 235), -1)
    cv2.rectangle(frame, (282, 45), (320, 95), (190, 220, 235), -1)
    cv2.line(frame, (275, 100), (330, 280), (120, 150, 165), 3)

    verifier = CandidateVerifier(
        Settings(
            OPENAI_API_KEY=None,
            YOLOE_MODEL_PATH="mock://color",
            CONTEXT_AUTO_LOCK_MIN_SCORE=0.55,
            CONTEXT_AUTO_LOCK_MARGIN=0.10,
        )
    )
    decision, latency_ms = verifier.verify(
        frame,
        "red bottle",
        [detection("bottle", [250, 40, 350, 305], confidence=0.9)],
    )

    assert latency_ms >= 0
    assert decision.selected_detection_id == "bottle"
    assert decision.mode == "local-context"
