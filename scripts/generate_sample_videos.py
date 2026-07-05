from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sample_videos"
SIZE = (640, 360)
FPS = 12
FRAMES = 72


def writer(name: str) -> cv2.VideoWriter:
    OUT.mkdir(exist_ok=True)
    return cv2.VideoWriter(str(OUT / name), cv2.VideoWriter_fourcc(*"mp4v"), FPS, SIZE)


def base_frame() -> np.ndarray:
    frame = np.full((SIZE[1], SIZE[0], 3), 238, dtype=np.uint8)
    cv2.line(frame, (0, 280), (SIZE[0], 280), (205, 210, 205), 2)
    return frame


def draw_bottle(frame: np.ndarray, x: int, y: int, color: tuple[int, int, int], label: str = "") -> None:
    cv2.rectangle(frame, (x, y + 36), (x + 62, y + 142), color, -1)
    cv2.rectangle(frame, (x + 18, y), (x + 44, y + 42), color, -1)
    cv2.rectangle(frame, (x + 16, y), (x + 46, y + 10), (40, 40, 40), -1)
    if label:
        cv2.putText(frame, label, (x, y + 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (35, 35, 35), 2)


def one_red_bottle() -> None:
    out = writer("one_red_bottle.mp4")
    for i in range(FRAMES):
        frame = base_frame()
        draw_bottle(frame, 180 + i // 3, 100, (0, 0, 255), "red")
        out.write(frame)
    out.release()


def two_similar_bottles() -> None:
    out = writer("two_similar_bottles.mp4")
    for i in range(FRAMES):
        frame = base_frame()
        draw_bottle(frame, 150 + i // 4, 100, (0, 0, 255), "A")
        draw_bottle(frame, 360 - i // 5, 100, (0, 0, 235), "B")
        out.write(frame)
    out.release()


def target_temporarily_occluded() -> None:
    out = writer("target_temporarily_occluded.mp4")
    for i in range(FRAMES):
        frame = base_frame()
        draw_bottle(frame, 210 + i // 4, 100, (0, 0, 255), "red")
        if 28 <= i <= 42:
            cv2.rectangle(frame, (250, 60), (370, 285), (75, 78, 78), -1)
        out.write(frame)
    out.release()


def target_leaves_and_returns() -> None:
    out = writer("target_leaves_and_returns.mp4")
    for i in range(FRAMES):
        frame = base_frame()
        x = 80 + i * 8
        if i > 46:
            x = 420 - (i - 46) * 7
        draw_bottle(frame, x, 100, (0, 0, 255), "red")
        out.write(frame)
    out.release()


def no_matching_object() -> None:
    out = writer("no_matching_object.mp4")
    for i in range(FRAMES):
        frame = base_frame()
        draw_bottle(frame, 220 + i // 5, 100, (255, 0, 0), "blue")
        out.write(frame)
    out.release()


def wrong_spoken_object_name() -> None:
    out = writer("wrong_spoken_object_name.mp4")
    for i in range(FRAMES):
        frame = base_frame()
        draw_bottle(frame, 220 + i // 5, 100, (0, 255, 0), "green")
        out.write(frame)
    out.release()


def main() -> None:
    one_red_bottle()
    two_similar_bottles()
    target_temporarily_occluded()
    target_leaves_and_returns()
    no_matching_object()
    wrong_spoken_object_name()
    print(f"Wrote sample videos to {OUT}")


if __name__ == "__main__":
    main()
