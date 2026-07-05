from __future__ import annotations

import base64
import json
import time
from typing import List, Optional

import cv2
import numpy as np

from app.config import Settings
from app.models import LegoBlockCandidate, LegoVerificationResponse


class LegoBlockVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._openai_client = None

    def verify(self, frame: np.ndarray, candidates: List[LegoBlockCandidate]) -> LegoVerificationResponse:
        started = time.perf_counter()
        if not candidates:
            return LegoVerificationResponse(
                verified_colors=[],
                mode="no-candidates",
                reason="No local color block candidates were present.",
                latency_ms=(time.perf_counter() - started) * 1000,
            )

        result = self._verify_with_openai(frame, candidates)
        if result is not None:
            result.latency_ms = (time.perf_counter() - started) * 1000
            return result

        verified_colors = self._local_shape_gate(frame, candidates)
        return LegoVerificationResponse(
            verified_colors=verified_colors,
            mode="local-fallback",
            reason="OpenAI verifier unavailable; used strict local color and shape gate.",
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    def _verify_with_openai(
        self, frame: np.ndarray, candidates: List[LegoBlockCandidate]
    ) -> Optional[LegoVerificationResponse]:
        if not self.settings.visual_context_verifier or not self.settings.openai_api_key:
            return None
        try:
            from openai import OpenAI
        except Exception:
            return None

        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=self.settings.openai_api_key)

        annotated = draw_lego_candidate_numbers(frame, candidates)
        ok, encoded = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        if not ok:
            return None

        image_url = "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
        choices = [
            {
                "number": index + 1,
                "id": candidate.id,
                "color": candidate.color,
                "bbox": candidate.bbox,
            }
            for index, candidate in enumerate(candidates)
        ]
        prompt = (
            "You are verifying a tabletop Lego block AR demo. The image has numbered candidate boxes on a white tissue paper background. "
            "Only accept a candidate if the box clearly contains a physical Lego-style block/brick of the stated color. "
            "Reject human faces, hands, clothing, walls, ceiling fixtures, screen borders, shadows, reflections, and the white background. "
            "Expected colors: black, red, blue, yellow. There should be at most one of each color. "
            "Return only colors for candidates you are confident are real blocks visible in the image."
        )

        try:
            response = self._openai_client.responses.create(
                model=self.settings.openai_vision_model or self.settings.openai_language_model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt + "\nCandidates: " + json.dumps(choices)},
                            {"type": "input_image", "image_url": image_url},
                        ],
                    }
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "lego_block_verification",
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "verified_colors": {
                                    "type": "array",
                                    "items": {"type": "string", "enum": ["black", "red", "blue", "yellow"]},
                                },
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "reason": {"type": "string"},
                            },
                            "required": ["verified_colors", "confidence", "reason"],
                        },
                        "strict": True,
                    }
                },
            )
            payload = json.loads(getattr(response, "output_text", "") or "{}")
            confidence = float(payload.get("confidence") or 0)
            verified_colors = [
                color
                for color in payload.get("verified_colors", [])
                if color in {candidate.color for candidate in candidates}
            ]
            if confidence < 0.55:
                verified_colors = []
            return LegoVerificationResponse(
                verified_colors=list(dict.fromkeys(verified_colors)),
                mode="openai-vision",
                reason=payload.get("reason") or "OpenAI verifier completed.",
                latency_ms=0,
            )
        except Exception:
            return None

    def _local_shape_gate(self, frame: np.ndarray, candidates: List[LegoBlockCandidate]) -> List[str]:
        frame_h, frame_w = frame.shape[:2]
        verified = []
        for candidate in candidates:
            x1, y1, x2, y2 = [int(value) for value in candidate.bbox]
            width = max(1, x2 - x1)
            height = max(1, y2 - y1)
            area_ratio = (width * height) / max(1, frame_w * frame_h)
            aspect = max(width, height) / max(1, min(width, height))
            touches_edge = x1 <= 2 or y1 <= 2 or x2 >= frame_w - 3 or y2 >= frame_h - 3
            if 0.0015 <= area_ratio <= 0.07 and 1.1 <= aspect <= 5.4 and not touches_edge:
                verified.append(candidate.color)
        return list(dict.fromkeys(verified))


def draw_lego_candidate_numbers(frame: np.ndarray, candidates: List[LegoBlockCandidate]) -> np.ndarray:
    annotated = frame.copy()
    for index, candidate in enumerate(candidates):
        x1, y1, x2, y2 = [int(value) for value in candidate.bbox]
        color = (0, 210, 255)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
        cv2.rectangle(annotated, (x1, max(0, y1 - 30)), (x1 + 70, y1), color, -1)
        cv2.putText(
            annotated,
            f"{index + 1}:{candidate.color}",
            (x1 + 6, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (10, 10, 10),
            2,
            cv2.LINE_AA,
        )
    return annotated
