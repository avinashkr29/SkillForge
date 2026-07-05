"""Verify whether LEGO blocks satisfy stacking instructions."""

from __future__ import annotations

from dataclasses import dataclass

from lego_ar.block_detector import DetectedBlock
from lego_ar.instruction_parser import AssemblyStep


@dataclass
class StepVerification:
    is_complete: bool
    source_found: bool
    target_found: bool
    message: str


class StepVerifier:
    def __init__(
        self,
        horizontal_overlap_ratio: float = 0.45,
        min_vertical_gap: int = 8,
        max_vertical_gap: int = 180,
        stable_frames_required: int = 20,
    ) -> None:
        self.horizontal_overlap_ratio = horizontal_overlap_ratio
        self.min_vertical_gap = min_vertical_gap
        self.max_vertical_gap = max_vertical_gap
        self.stable_frames_required = stable_frames_required
        self._stable_counter = 0

    def reset(self) -> None:
        self._stable_counter = 0

    def verify(
        self,
        step: AssemblyStep,
        detections: list[DetectedBlock],
    ) -> StepVerification:
        source = self._find_best_block(detections, step.source_color)
        target = self._find_best_block(detections, step.target_color)

        if source is None and target is None:
            return StepVerification(
                is_complete=False,
                source_found=False,
                target_found=False,
                message=f"Looking for {step.source_color} and {step.target_color} blocks",
            )

        if source is None:
            return StepVerification(
                is_complete=False,
                source_found=False,
                target_found=target is not None,
                message=f"Place the {step.source_color} block on the {step.target_color} block",
            )

        if target is None:
            return StepVerification(
                is_complete=False,
                source_found=True,
                target_found=False,
                message=f"Looking for the {step.target_color} block",
            )

        if self._is_stacked(source, target):
            self._stable_counter += 1
            if self._stable_counter >= self.stable_frames_required:
                return StepVerification(
                    is_complete=True,
                    source_found=True,
                    target_found=True,
                    message=f"Step {step.number} complete",
                )
            remaining = self.stable_frames_required - self._stable_counter
            return StepVerification(
                is_complete=False,
                source_found=True,
                target_found=True,
                message=f"Hold steady... ({remaining} frames)",
            )

        self._stable_counter = 0
        return StepVerification(
            is_complete=False,
            source_found=True,
            target_found=True,
            message=(
                f"Move {step.source_color} on top of {step.target_color} "
                f"(arrow shows direction)"
            ),
        )

    def _find_best_block(
        self,
        detections: list[DetectedBlock],
        color: str,
    ) -> DetectedBlock | None:
        matches = [block for block in detections if block.color == color]
        if not matches:
            return None
        return max(matches, key=lambda block: block.confidence)

    def _is_stacked(self, source: DetectedBlock, target: DetectedBlock) -> bool:
        sx, sy, sw, sh = source.bbox
        tx, ty, tw, th = target.bbox

        source_bottom = sy + sh
        target_top = ty
        # Distance from the moving block's bottom edge to the base block's top edge.
        vertical_gap = target_top - source_bottom

        # Source must sit above the target in the camera view.
        if source.center[1] >= target.center[1]:
            return False

        if vertical_gap < -self.min_vertical_gap or vertical_gap > self.max_vertical_gap:
            return False

        overlap = max(0, min(sx + sw, tx + tw) - max(sx, tx))
        min_width = min(sw, tw)
        if min_width <= 0:
            return False

        if overlap / min_width < self.horizontal_overlap_ratio:
            return False

        horizontal_offset = abs(source.center[0] - target.center[0])
        if horizontal_offset > max(sw, tw) * 0.65:
            return False

        return True