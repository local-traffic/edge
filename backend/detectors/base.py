"""
Base detector class and utilities for all detector implementations.
"""

from abc import ABC, abstractmethod
import supervision as sv
import numpy as np


def translate_class_ids_to_coco(detections):
    """
    Translate 0-based class IDs to COCO 1-based format by adding 1.

    Args:
        detections: supervision.Detections object with 0-based class IDs

    Returns:
        detections with class IDs incremented by 1 (modifies in place)

    Use this for models that output 0-based class IDs (YOLO, Hailo, NCNN).
    Don't call this for models already using COCO 1-based format (RF-DETR).

    Example:
        # YOLO detector outputs 0-based class IDs
        detections = model.predict(image)
        return translate_class_ids_to_coco(detections)  # Now COCO 1-based

        # RF-DETR already outputs COCO 1-based, no translation needed
        return model.predict(image)
    """
    if detections.class_id is not None:
        detections.class_id = detections.class_id + 1
    return detections


class BaseDetector(ABC):
    """
    Base detector class for all inference backends.

    All detectors should output class IDs in COCO 1-based format
    to ensure compatibility with COCO_CLASSES dictionary.

    Use translate_class_ids_to_coco() utility function to convert
    model-specific class IDs to the unified COCO format.
    """

    @abstractmethod
    def predict(self, image, conf_threshold=0.3):
        """
        Run inference on the image.
        Returns: supervision.Detections with COCO 1-based class IDs
        """
        pass
