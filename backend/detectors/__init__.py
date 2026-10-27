"""
Detector package for traffic detection.
Supports YOLO, RF-DETR, NCNN, Hailo, and motion-based detection.
"""

from .base import BaseDetector, translate_class_ids_to_coco
from .yolo import YOLODetector
from .rfdetr import RFDETRDetector
from .ncnn import NCNNDetector
from .hailo import HailoDetector
from .motion import MotionDetector
from .factory import new_detector

__all__ = [
    'BaseDetector',
    'YOLODetector',
    'RFDETRDetector',
    'NCNNDetector',
    'HailoDetector',
    'MotionDetector',
    'new_detector',
    'translate_class_ids_to_coco',
]
