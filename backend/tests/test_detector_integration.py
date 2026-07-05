from pathlib import Path

import cv2
import numpy as np

from app.config import Settings
from app.modules.detector import YOLOEObjectDetector
from app.modules.video_source import read_video_frames


def make_test_video(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 8, (320, 240))
    for index in range(12):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.rectangle(frame, (40 + index * 3, 80), (110 + index * 3, 170), (0, 0, 255), -1)
        writer.write(frame)
    writer.release()


def test_mock_detector_finds_red_object_in_sample_mp4(tmp_path):
    video_path = tmp_path / "one_red_bottle.mp4"
    make_test_video(video_path)
    frames = read_video_frames(video_path)

    detector = YOLOEObjectDetector(Settings(OPENAI_API_KEY=None, YOLOE_MODEL_PATH="mock://color"))
    output = detector.detect(frames[0], ["red bottle"], prompt_version=1)

    assert output.backend == "mock-color"
    assert len(output.detections) == 1
    assert output.detections[0].label == "red bottle"
