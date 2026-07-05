"""LEGO AR assembly guide — color detection + step-by-step overlay."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

from lego_ar.ar_overlay import AROverlay
from lego_ar.block_detector import BlockDetector
from lego_ar.instruction_parser import load_instructions
from lego_ar.step_verifier import StepVerifier

DEFAULT_INSTRUCTIONS = Path(__file__).resolve().parent.parent / "instructions.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LEGO block AR assembly guide with OpenCV color detection",
    )
    parser.add_argument(
        "--instructions",
        type=Path,
        default=DEFAULT_INSTRUCTIONS,
        help="Path to plain-text assembly instructions",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera device index (default: 0)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Camera capture width",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Camera capture height",
    )
    return parser.parse_args()


def _required_colors(steps: list) -> set[str]:
    colors: set[str] = set()
    for step in steps:
        colors.add(step.source_color)
        colors.add(step.target_color)
    return colors


def run() -> int:
    args = parse_args()

    try:
        steps = load_instructions(args.instructions)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Error: Could not open camera {args.camera}", file=sys.stderr)
        return 1

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    detector = BlockDetector()
    verifier = StepVerifier()
    overlay = AROverlay()
    colors = _required_colors(steps)

    current_step_index = 0
    task_complete = False
    completion_started_at: float | None = None

    print("LEGO AR Assembly Guide")
    print(f"Loaded {len(steps)} step(s) from {args.instructions}")
    for step in steps:
        print(f"  Step {step.number}: {step.instruction}")
    print("Press 'q' to quit, 'r' to reset progress")

    window_name = "SkillForge LEGO AR"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Error: Failed to read camera frame", file=sys.stderr)
            break

        frame = cv2.flip(frame, 1)

        if task_complete:
            display = overlay.draw_completion(frame, len(steps))
        else:
            step = steps[current_step_index]
            detections = detector.detect(frame, colors)
            verification = verifier.verify(step, detections)

            if verification.is_complete:
                if current_step_index < len(steps) - 1:
                    current_step_index += 1
                    verifier.reset()
                    print(f"Step {step.number} complete -> advancing to step {current_step_index + 1}")
                else:
                    task_complete = True
                    completion_started_at = time.time()
                    print("All steps complete — task finished!")
                    verification = verifier.verify(step, detections)

            display = overlay.draw_step_guidance(
                frame,
                step,
                detections,
                verification,
                len(steps),
            )

        cv2.imshow(window_name, display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        if key == ord("r"):
            current_step_index = 0
            task_complete = False
            completion_started_at = None
            verifier.reset()
            print("Progress reset")

        if task_complete and completion_started_at and time.time() - completion_started_at > 8:
            current_step_index = 0
            task_complete = False
            completion_started_at = None
            verifier.reset()
            print("Restarting from step 1")

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())