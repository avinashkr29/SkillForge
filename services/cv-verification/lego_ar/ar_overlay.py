"""Draw AR guidance overlays for LEGO assembly steps."""

from __future__ import annotations

import cv2
import numpy as np

from lego_ar.block_detector import COLOR_BGR, DetectedBlock
from lego_ar.instruction_parser import AssemblyStep
from lego_ar.step_verifier import StepVerification


class AROverlay:
    def __init__(self) -> None:
        self._font = cv2.FONT_HERSHEY_SIMPLEX

    def draw_step_guidance(
        self,
        frame: np.ndarray,
        step: AssemblyStep,
        detections: list[DetectedBlock],
        verification: StepVerification,
        total_steps: int,
    ) -> np.ndarray:
        overlay = frame.copy()
        source = self._find_block(detections, step.source_color)
        target = self._find_block(detections, step.target_color)

        self._draw_hud(overlay, step, verification, total_steps)

        if source is not None:
            self._draw_block_highlight(overlay, source, role="source")
        if target is not None:
            self._draw_block_highlight(overlay, target, role="target")

        if source is not None and target is not None and not verification.is_complete:
            self._draw_placement_arrow(overlay, source.center, target.center)

        return overlay

    def draw_completion(self, frame: np.ndarray, total_steps: int) -> np.ndarray:
        overlay = frame.copy()
        h, w = overlay.shape[:2]

        panel = np.zeros((140, w - 40, 3), dtype=np.uint8)
        panel[:] = (20, 120, 20)
        cv2.rectangle(panel, (0, 0), (panel.shape[1] - 1, panel.shape[0] - 1), (80, 220, 80), 2)
        cv2.putText(
            panel,
            "TASK COMPLETE",
            (20, 55),
            self._font,
            1.2,
            (255, 255, 255),
            3,
            cv2.LINE_AA,
        )
        cv2.putText(
            panel,
            f"All {total_steps} steps finished successfully",
            (20, 100),
            self._font,
            0.75,
            (220, 255, 220),
            2,
            cv2.LINE_AA,
        )
        overlay[20:20 + panel.shape[0], 20:20 + panel.shape[1]] = panel
        return overlay

    def _draw_hud(
        self,
        frame: np.ndarray,
        step: AssemblyStep,
        verification: StepVerification,
        total_steps: int,
    ) -> None:
        h, w = frame.shape[:2]
        panel_h = 130
        panel = np.zeros((panel_h, w - 30, 3), dtype=np.uint8)
        panel[:] = (30, 30, 30)

        status_color = (80, 220, 80) if verification.is_complete else (80, 180, 255)
        cv2.rectangle(panel, (0, 0), (panel.shape[1] - 1, panel.shape[0] - 1), status_color, 2)

        cv2.putText(
            panel,
            f"STEP {step.number} / {total_steps}",
            (16, 36),
            self._font,
            0.9,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            panel,
            step.instruction,
            (16, 72),
            self._font,
            0.62,
            (230, 230, 230),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            panel,
            verification.message,
            (16, 108),
            self._font,
            0.58,
            status_color,
            2,
            cv2.LINE_AA,
        )

        frame[15:15 + panel_h, 15:15 + panel.shape[1]] = panel

    def _draw_block_highlight(
        self,
        frame: np.ndarray,
        block: DetectedBlock,
        role: str,
    ) -> None:
        x, y, w, h = block.bbox
        color = COLOR_BGR.get(block.color, (255, 255, 255))
        thickness = 4 if role == "source" else 3

        cv2.rectangle(frame, (x - 4, y - 4), (x + w + 4, y + h + 4), color, thickness)

        label = f"{block.color.upper()}"
        if role == "source":
            label += " (MOVE)"
        elif role == "target":
            label += " (BASE)"

        cv2.putText(
            frame,
            label,
            (x, max(y - 10, 20)),
            self._font,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    def _draw_placement_arrow(
        self,
        frame: np.ndarray,
        source_center: tuple[int, int],
        target_center: tuple[int, int],
    ) -> None:
        start = (source_center[0], source_center[1] - 10)
        end = (target_center[0], target_center[1] - max(20, 0))

        cv2.arrowedLine(
            frame,
            start,
            end,
            (0, 255, 255),
            4,
            tipLength=0.25,
            line_type=cv2.LINE_AA,
        )

        mid_x = (start[0] + end[0]) // 2
        mid_y = (start[1] + end[1]) // 2
        cv2.putText(
            frame,
            "PLACE HERE",
            (mid_x - 70, mid_y - 12),
            self._font,
            0.55,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

    @staticmethod
    def _find_block(
        detections: list[DetectedBlock],
        color: str,
    ) -> DetectedBlock | None:
        matches = [block for block in detections if block.color == color]
        if not matches:
            return None
        return max(matches, key=lambda block: block.confidence)