"""
Factory function for creating detector instances.
"""

from .yolo import YOLODetector
from .rfdetr import RFDETRDetector
from .ncnn import NCNNDetector
from .hailo import HailoDetector
from .motion import MotionDetector


def new_detector(model_type="yolo", model_path=None, **kwargs):
    """
    Factory function to create detector instances.

    Args:
        model_type: Type of detector ('yolo', 'rfdetr', 'hailo', 'ncnn', 'motion')
        model_path: Path to model file
        **kwargs: Additional arguments passed to detector constructor

    Returns:
        Instance of a detector class inheriting from BaseDetector

    Raises:
        ValueError: If model_type is not recognized
    """
    if model_type.lower() == "yolo":
        path = model_path if model_path else "yolov8n.pt"
        return YOLODetector(path)
    elif model_type.lower() == "rfdetr":
        return RFDETRDetector()
    elif model_type.lower() == "hailo":
        path = model_path if model_path else "yolov8n.hef"
        return HailoDetector(path)
    elif model_type.lower() == "ncnn":
        use_vulkan = kwargs.get("use_vulkan", False)
        return NCNNDetector(model_path, use_vulkan=use_vulkan)
    elif model_type.lower() in ["motion"]:
        return MotionDetector()
    else:
        raise ValueError(f"Unknown model type: {model_type}")
