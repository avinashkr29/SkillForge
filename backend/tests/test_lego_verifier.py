import numpy as np

from app.config import Settings
from app.models import LegoBlockCandidate
from app.modules.lego_verifier import LegoBlockVerifier


def candidate(color, bbox):
    return LegoBlockCandidate(id=f"{color}-1", color=color, bbox=bbox, confidence=0.8)


def test_lego_verifier_local_gate_rejects_edge_background_regions():
    frame = np.full((360, 640, 3), 220, dtype=np.uint8)
    verifier = LegoBlockVerifier(Settings(OPENAI_API_KEY=None, VISUAL_CONTEXT_VERIFIER=False))

    result = verifier.verify(
        frame,
        [
            candidate("white", [0, 50, 60, 260]),
            candidate("red", [120, 300, 638, 358]),
        ],
    )

    assert result.mode == "local-fallback"
    assert result.verified_colors == []


def test_lego_verifier_local_gate_allows_compact_color_blocks():
    frame = np.full((360, 640, 3), 180, dtype=np.uint8)
    verifier = LegoBlockVerifier(Settings(OPENAI_API_KEY=None, VISUAL_CONTEXT_VERIFIER=False))

    result = verifier.verify(
        frame,
        [
            candidate("black", [70, 120, 110, 250]),
            candidate("white", [170, 120, 210, 250]),
            candidate("red", [270, 120, 310, 250]),
            candidate("blue", [370, 145, 420, 235]),
        ],
    )

    assert result.mode == "local-fallback"
    assert result.verified_colors == ["black", "white", "red", "blue"]
