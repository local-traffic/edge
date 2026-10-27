"""
YOLO detector implementation using Ultralytics.
"""

import supervision as sv
from .base import BaseDetector, translate_class_ids_to_coco


class YOLODetector(BaseDetector):
    def __init__(self, model_path="yolov8n.pt"):
        from ultralytics import YOLO
        print(f"Loading YOLO model: {model_path}...")
        self.model = YOLO(model_path)
        print("YOLO model loaded.")

    def predict(self, image, conf_threshold=0.3):
        # YOLO expects BGR usually, but handles RGB fine if consistent.
        # Ultralytics track() or predict()
        # We use predict() here since tracking is handled externally
        # by ByteTrack in main loop.
        # But wait, roboflow.py used model.track() with persist=True.
        # However, roboflow-rfdetr.py used external ByteTrack.
        # To unify, we should output Detections and let external ByteTrack
        # handle tracking.
        # This allows consistent tracking logic across models.

        results = self.model.predict(
            image, conf=conf_threshold, verbose=False
        )[0]
        detections = sv.Detections.from_ultralytics(results)
        # Translate YOLO 0-based class IDs to COCO 1-based format
        return translate_class_ids_to_coco(detections)
