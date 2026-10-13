"""Person detection with YOLOv8 (Ultralytics, AGPL-3.0) and a zone test."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Detection:
    box: tuple[int, int, int, int]  # x1, y1, x2, y2 in pixels
    score: float
    in_zone: bool


class PersonDetector:
    def __init__(self, weights: str, device: str, conf: float = 0.35):
        from ultralytics import YOLO

        self.model = YOLO(weights)
        self.device = device
        self.conf = conf
        self.name = weights.rsplit("/", 1)[-1].removesuffix(".pt")

    def __call__(self, frame: np.ndarray, zone: np.ndarray) -> list[Detection]:
        result = self.model.predict(
            frame, classes=[0], conf=self.conf, device=self.device, verbose=False
        )[0]
        out = []
        for (x1, y1, x2, y2), score in zip(
            result.boxes.xyxy.cpu().numpy(), result.boxes.conf.cpu().numpy()
        ):
            foot = ((x1 + x2) / 2.0, float(y2))  # bottom centre: where the person stands
            inside = cv2.pointPolygonTest(zone, foot, False) >= 0
            out.append(Detection((int(x1), int(y1), int(x2), int(y2)), float(score), inside))
        return out


def zone_pixels(zone_norm: list[list[float]], width: int, height: int) -> np.ndarray:
    """Zone polygon from normalised [x, y] pairs to an OpenCV contour."""
    pts = np.array([[x * width, y * height] for x, y in zone_norm], dtype=np.float32)
    return pts.reshape(-1, 1, 2)
