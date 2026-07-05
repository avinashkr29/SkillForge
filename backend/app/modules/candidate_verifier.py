from __future__ import annotations

import base64
import json
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

from app.config import Settings
from app.models import CandidateScore, DetectionResult, VerificationDecision


COLOR_HSV_RANGES = {
    "red": [((0, 80, 50), (10, 255, 255)), ((170, 80, 50), (180, 255, 255))],
    "blue": [((95, 55, 40), (130, 255, 255))],
    "green": [((35, 45, 35), (85, 255, 255))],
    "yellow": [((20, 60, 60), (34, 255, 255))],
    "orange": [((10, 70, 60), (22, 255, 255))],
    "purple": [((130, 45, 35), (160, 255, 255))],
    "pink": [((145, 35, 55), (175, 255, 255))],
    "white": [((0, 0, 175), (180, 70, 255))],
    "black": [((0, 0, 0), (180, 255, 80))],
}

PHONE_WORDS = {"phone", "smartphone", "mobile", "cellphone", "iphone", "android"}
BOTTLE_WORDS = {"bottle", "water", "flask"}
RECTANGLE_WORDS = {"card", "remote", "book", "box", "tablet", "screen", "phone", "smartphone", "mobile"}


class CandidateVerifier:
    OPENAI_MIN_INTERVAL_SEC = 0.2  # ~5 calls/sec max (4-6 fps)

    def __init__(self, settings: Settings):
        self.settings = settings
        self._openai_client = None
        self._last_openai_call_time: float = 0.0

    def verify(
        self,
        frame: np.ndarray,
        object_phrase: str,
        candidates: List[DetectionResult],
    ) -> Tuple[VerificationDecision, float]:
        started = time.perf_counter()
        if not candidates:
            decision = VerificationDecision(
                selected_detection_id=None,
                score=0,
                margin=1,
                mode="no-candidates",
                reason="No detector candidates were present.",
                scores=[],
            )
            return decision, (time.perf_counter() - started) * 1000

        decision = self._verify_with_openai(frame, object_phrase, candidates)
        if decision is None:
            decision = self._verify_with_local_context(frame, object_phrase, candidates)
        return decision, (time.perf_counter() - started) * 1000

    def _verify_with_local_context(
        self,
        frame: np.ndarray,
        object_phrase: str,
        candidates: List[DetectionResult],
    ) -> VerificationDecision:
        tokens = set(object_phrase.lower().replace("-", " ").split())
        scored = [self._score_candidate(frame, tokens, candidate) for candidate in candidates]
        scored.sort(key=lambda score: score.score, reverse=True)
        best = scored[0]
        second = scored[1].score if len(scored) > 1 else 0
        margin = best.score - second
        selected = None
        reason = "Context verifier was not confident enough; trainer selection is still required."
        if best.score >= self.settings.context_auto_lock_min_score and margin >= self.settings.context_auto_lock_margin:
            selected = best.detection_id
            reason = "Local visual context isolated one dominant object candidate."
        return VerificationDecision(
            selected_detection_id=selected,
            score=best.score,
            margin=margin,
            mode="local-context",
            reason=reason,
            scores=scored,
        )

    def _score_candidate(self, frame: np.ndarray, tokens: set[str], candidate: DetectionResult) -> CandidateScore:
        crop, clipped = crop_bbox(frame, candidate.bbox, margin=0.04)
        reasons: List[str] = []
        if crop.size == 0:
            return CandidateScore(detection_id=candidate.detection_id, score=0, reasons=["empty crop"])

        h, w = crop.shape[:2]
        frame_h, frame_w = frame.shape[:2]
        area_ratio = (w * h) / max(1, frame_w * frame_h)
        aspect = w / max(1, h)
        touches_edge = clipped[0] <= 2 or clipped[1] <= 2 or clipped[2] >= frame_w - 2 or clipped[3] >= frame_h - 2

        score = candidate.confidence * 0.22
        if 0.003 <= area_ratio <= 0.25:
            score += 0.12
            reasons.append("usable object scale")
        if not touches_edge:
            score += 0.08
            reasons.append("not a frame-edge artifact")
        else:
            score -= 0.18
            reasons.append("touches frame edge")

        color_score, color_reason = self._color_score(crop, tokens)
        score += color_score
        if color_reason:
            reasons.append(color_reason)

        rect_score, rect_reason = self._rectangle_score(crop, aspect)
        if RECTANGLE_WORDS.intersection(tokens):
            score += rect_score
            reasons.append(rect_reason)

        if PHONE_WORDS.intersection(tokens):
            phone_score, phone_reasons = self._phone_score(crop, aspect, area_ratio, touches_edge)
            score += phone_score
            reasons.extend(phone_reasons)

        if BOTTLE_WORDS.intersection(tokens):
            bottle_score, bottle_reasons = self._bottle_score(crop, aspect, area_ratio, touches_edge)
            score += bottle_score
            reasons.extend(bottle_reasons)

        texture_score = min(0.08, edge_density(crop) * 0.45)
        score += texture_score
        if texture_score > 0.025:
            reasons.append("has object edge detail")

        return CandidateScore(
            detection_id=candidate.detection_id,
            score=max(0, min(1, score)),
            reasons=reasons[:5],
        )

    def _color_score(self, crop: np.ndarray, tokens: set[str]) -> Tuple[float, str]:
        color_tokens = [color for color in COLOR_HSV_RANGES if color in tokens]
        if not color_tokens:
            return 0, ""
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        best_ratio = 0.0
        best_color = ""
        for color in color_tokens:
            mask = np.zeros(crop.shape[:2], dtype=np.uint8)
            for lower, upper in COLOR_HSV_RANGES[color]:
                mask = cv2.bitwise_or(mask, cv2.inRange(hsv, np.array(lower), np.array(upper)))
            ratio = cv2.countNonZero(mask) / max(1, mask.size)
            if ratio > best_ratio:
                best_ratio = ratio
                best_color = color
        if best_color == "black" and best_ratio >= 0.42:
            return 0.08, "strong black match"
        if best_color == "black" and best_ratio >= 0.20:
            return 0.04, "partial black match"
        if best_ratio >= 0.42:
            return 0.18, f"strong {best_color} match"
        if best_ratio >= 0.20:
            return 0.10, f"partial {best_color} match"
        return -0.05, f"weak {best_color or color_tokens[0]} match"

    def _rectangle_score(self, crop: np.ndarray, aspect: float) -> Tuple[float, str]:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0, "no rectangular contour"
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        x, y, w, h = cv2.boundingRect(largest)
        extent = area / max(1, w * h)
        if 0.55 <= extent <= 1.05 and 0.55 <= aspect <= 4.4:
            return 0.12, "rectangular object geometry"
        if 0.45 <= extent <= 1.1:
            return 0.06, "some rectangular geometry"
        return 0, "weak rectangular geometry"

    def _phone_score(self, crop: np.ndarray, aspect: float, area_ratio: float, touches_edge: bool) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        score = 0.0
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        dark_ratio = float(np.mean(gray < 85))
        very_dark_ratio = float(np.mean(gray < 45))

        if 1.15 <= aspect <= 3.7:
            score += 0.14
            reasons.append("phone-like aspect ratio")
        elif 0.55 <= aspect <= 0.95:
            score += 0.08
            reasons.append("portrait phone-like aspect ratio")
        else:
            score -= 0.08
            reasons.append("not phone-like aspect ratio")

        if dark_ratio >= 0.34:
            score += 0.12
            reasons.append("dark screen/body region")
        if very_dark_ratio >= 0.18:
            score += 0.04
            reasons.append("black screen pixels")
        if 0.045 <= area_ratio <= 0.18:
            score += 0.14
            reasons.append("substantial phone-like frame size")
        elif area_ratio < 0.035:
            score -= 0.14
            reasons.append("too small for confident phone lock")
        elif area_ratio <= 0.22:
            score += 0.04
            reasons.append("possible phone-like frame size")
        if touches_edge:
            score -= 0.22
            reasons.append("edge artifact penalty")
        return score, reasons

    def _bottle_score(self, crop: np.ndarray, aspect: float, area_ratio: float, touches_edge: bool) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        score = 0.0
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 45, 135)
        edge_ratio = cv2.countNonZero(edges) / max(1, edges.size)
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        low_saturation_ratio = float(np.mean(hsv[:, :, 1] < 75))

        if 0.25 <= aspect <= 1.05:
            score += 0.18
            reasons.append("bottle-like vertical shape")
        elif 1.05 < aspect <= 1.6:
            score += 0.08
            reasons.append("possible angled bottle shape")
        else:
            score -= 0.08
            reasons.append("not bottle-like aspect ratio")

        if 0.012 <= area_ratio <= 0.28:
            score += 0.12
            reasons.append("bottle-like frame size")
        if edge_ratio >= 0.035:
            score += 0.06
            reasons.append("bottle edge detail")
        if low_saturation_ratio >= 0.35:
            score += 0.05
            reasons.append("transparent/light bottle region")
        if touches_edge:
            score -= 0.12
            reasons.append("edge artifact penalty")
        return score, reasons

    def _verify_with_openai(
        self,
        frame: np.ndarray,
        object_phrase: str,
        candidates: List[DetectionResult],
    ) -> Optional[VerificationDecision]:
        if not self.settings.visual_context_verifier or not self.settings.openai_api_key:
            return None

        now = time.perf_counter()
        if now - self._last_openai_call_time < self.OPENAI_MIN_INTERVAL_SEC:
            return None  # Throttled — fall back to local verification

        try:
            from openai import OpenAI
        except Exception:
            return None
        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=self.settings.openai_api_key)

        self._last_openai_call_time = now

        annotated = draw_candidate_numbers(frame, candidates)
        ok, encoded = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        if not ok:
            return None
        image_url = "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
        choices = [
            {"number": index + 1, "detection_id": candidate.detection_id, "bbox": candidate.bbox}
            for index, candidate in enumerate(candidates)
        ]
        prompt = (
            "You are verifying an object tracker target. The image has numbered yellow candidate boxes. "
            f"The trainer asked to track exactly one object: '{object_phrase}'. "
            "Choose the one candidate box that best contains that object, ignoring background, body parts, glare, "
            "screen edges, and unrelated dark or similarly colored regions. If no candidate clearly contains the requested object, return null."
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
                        "name": "candidate_choice",
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "selected_number": {"type": ["integer", "null"]},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "reason": {"type": "string"},
                            },
                            "required": ["selected_number", "confidence", "reason"],
                        },
                        "strict": True,
                    }
                },
            )
            payload = json.loads(getattr(response, "output_text", "") or "{}")
            selected_number = payload.get("selected_number")
            confidence = float(payload.get("confidence") or 0)
            if selected_number is None or confidence < self.settings.context_auto_lock_min_score:
                return VerificationDecision(
                    selected_detection_id=None,
                    score=confidence,
                    margin=0,
                    mode="openai-vision",
                    reason=payload.get("reason") or "OpenAI vision verifier was not confident.",
                    scores=[],
                )
            index = int(selected_number) - 1
            if index < 0 or index >= len(candidates):
                return None
            return VerificationDecision(
                selected_detection_id=candidates[index].detection_id,
                score=confidence,
                margin=confidence,
                mode="openai-vision",
                reason=payload.get("reason") or "OpenAI vision verifier selected the target.",
                scores=[],
            )
        except Exception:
            return None


def crop_bbox(frame: np.ndarray, bbox: List[float], margin: float = 0.0) -> Tuple[np.ndarray, List[int]]:
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    pad_x = (x2 - x1) * margin
    pad_y = (y2 - y1) * margin
    clipped = [
        max(0, int(x1 - pad_x)),
        max(0, int(y1 - pad_y)),
        min(w, int(x2 + pad_x)),
        min(h, int(y2 + pad_y)),
    ]
    return frame[clipped[1] : clipped[3], clipped[0] : clipped[2]], clipped


def edge_density(crop: np.ndarray) -> float:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    return cv2.countNonZero(edges) / max(1, edges.size)


def draw_candidate_numbers(frame: np.ndarray, candidates: List[DetectionResult]) -> np.ndarray:
    annotated = frame.copy()
    for index, candidate in enumerate(candidates):
        x1, y1, x2, y2 = [int(value) for value in candidate.bbox]
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 210, 255), 3)
        cv2.rectangle(annotated, (x1, max(0, y1 - 28)), (x1 + 34, y1), (0, 210, 255), -1)
        cv2.putText(
            annotated,
            str(index + 1),
            (x1 + 8, max(18, y1 - 7)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (10, 10, 10),
            2,
            cv2.LINE_AA,
        )
    return annotated
