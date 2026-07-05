from lego_ar.block_detector import DetectedBlock
from lego_ar.instruction_parser import AssemblyStep
from lego_ar.step_verifier import StepVerifier


def _block(color: str, x: int, y: int, w: int = 80, h: int = 60) -> DetectedBlock:
    return DetectedBlock(
        color=color,
        center=(x + w // 2, y + h // 2),
        bbox=(x, y, w, h),
        area=w * h,
        confidence=0.9,
    )


def test_stacked_blocks_complete_after_stable_frames():
    step = AssemblyStep(1, "red", "white", "step one")
    verifier = StepVerifier(stable_frames_required=3)
    stacked = [
        _block("red", 200, 120),
        _block("white", 195, 200),
    ]

    for _ in range(2):
        result = verifier.verify(step, stacked)
        assert not result.is_complete

    result = verifier.verify(step, stacked)
    assert result.is_complete


def test_separate_blocks_not_complete():
    step = AssemblyStep(1, "red", "white", "step one")
    verifier = StepVerifier(stable_frames_required=3)
    separate = [
        _block("red", 100, 200),
        _block("white", 400, 200),
    ]

    for _ in range(5):
        result = verifier.verify(step, separate)
        assert not result.is_complete