from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np

from app.config import Settings
from app.models import DetectionResult


COLOR_RANGES = {
    "red": [((0, 90, 60), (10, 255, 255)), ((170, 90, 60), (180, 255, 255))],
    "blue": [((95, 80, 50), (130, 255, 255))],
    "green": [((35, 60, 50), (85, 255, 255))],
    "yellow": [((20, 80, 70), (34, 255, 255))],
    "orange": [((10, 80, 70), (22, 255, 255))],
    "purple": [((130, 60, 50), (160, 255, 255))],
    "pink": [((145, 50, 70), (175, 255, 255))],
    "white": [((0, 0, 180), (180, 50, 255))],
    "black": [((0, 0, 0), (180, 255, 70))],
}


@dataclass
class DetectorOutput:
    detections: List[DetectionResult]
    latency_ms: float
    backend: str


class YOLOEObjectDetector:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = None
        self.backend = "mock-color"
        self._last_prompt_key = ""

    def load(self) -> None:
        if self.settings.yoloe_model_path.startswith("mock://"):
            return
        try:
            from ultralytics import YOLOE

            self.model = YOLOE(self.settings.yoloe_model_path)
            self.backend = "ultralytics-yoloe"
        except Exception:
            self.model = None
            self.backend = "mock-color"

    def detect(self, frame: np.ndarray, prompts: List[str], prompt_version: int) -> DetectorOutput:
        if self.model is None:
            self.load()
        started = time.perf_counter()
        if self.model is not None:
            detections = self._detect_yoloe(frame, prompts, prompt_version)
        else:
            detections = self._detect_mock_color(frame, prompts, prompt_version)
        return DetectorOutput(
            detections=detections,
            latency_ms=(time.perf_counter() - started) * 1000,
            backend=self.backend,
        )

    def _detect_yoloe(self, frame: np.ndarray, prompts: List[str], prompt_version: int) -> List[DetectionResult]:
        prompt_key = "|".join(prompts)
        if prompt_key != self._last_prompt_key:
            if hasattr(self.model, "set_classes") and hasattr(self.model, "get_text_pe"):
                self.model.set_classes(prompts, self.model.get_text_pe(prompts))
            elif hasattr(self.model, "set_classes"):
                self.model.set_classes(prompts)
            self._last_prompt_key = prompt_key

        results = self.model.predict(
            source=frame,
            conf=self.settings.detector_confidence,
            imgsz=self.settings.detector_imgsz,
            verbose=False,
        )
        detections: List[DetectionResult] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for index, box in enumerate(boxes):
                xyxy = box.xyxy[0].detach().cpu().tolist()
                confidence = float(box.conf[0].detach().cpu())
                label = prompts[0] if prompts else "object"
                detections.append(
                    DetectionResult(
                        detection_id=str(uuid.uuid4()),
                        label=label,
                        confidence=confidence,
                        bbox=[float(value) for value in xyxy],
                        mask=None,
                        prompt_version=prompt_version,
                    )
                )
        return detections

    def _detect_mock_color(self, frame: np.ndarray, prompts: List[str], prompt_version: int) -> List[DetectionResult]:
        if frame.size == 0:
            return []
        prompt = prompts[0] if prompts else "object"
        prompt_tokens = set(prompt.split())
        colors = [color for color in COLOR_RANGES if color in prompt_tokens]
        if not colors:
            return []

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detections: List[DetectionResult] = []
        min_area = max(160, frame.shape[0] * frame.shape[1] * 0.001)
        for color in colors:
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            for lower, upper in COLOR_RANGES[color]:
                mask = cv2.bitwise_or(mask, cv2.inRange(hsv, np.array(lower), np.array(upper)))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                detections.append(
                    DetectionResult(
                        detection_id=str(uuid.uuid4()),
                        label=prompt,
                        confidence=min(0.95, 0.45 + area / max(1, frame.shape[0] * frame.shape[1])),
                        bbox=[float(x), float(y), float(x + w), float(y + h)],
                        mask=None,
                        prompt_version=prompt_version,
                    )
                )
        detections.sort(key=lambda item: item.confidence, reverse=True)
        return detections


def decode_base64_jpeg(image_payload: str) -> np.ndarray:
    import base64

    if "," in image_payload:
        image_payload = image_payload.split(",", 1)[1]
    data = base64.b64decode(image_payload)
    array = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode JPEG frame")
    return frame
