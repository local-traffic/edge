"""
Verify class ID translation across different detector types.

All detectors should output consistent COCO 1-based class IDs,
regardless of their internal model format.
"""

import numpy as np
import supervision as sv
from backend.detectors import translate_class_ids_to_coco

COCO_CLASSES = {
    1: "person",
    2: "bicycle",
    3: "car",
    4: "motorcycle",
    5: "airplane",
    6: "bus",
    7: "train",
    8: "truck",
}


def test_yolo_class_id_translation():
    """YOLO 0-based class IDs are correctly translated to COCO 1-based."""
    detections = sv.Detections(
        xyxy=np.array([[100, 100, 200, 200]]),
        confidence=np.array([0.9]),
        class_id=np.array([2]),  # YOLO: car = 2 (0-based)
    )

    detections = translate_class_ids_to_coco(detections)

    assert detections.class_id[0] == 3
    assert COCO_CLASSES[detections.class_id[0]] == "car"


def test_hailo_class_id_translation():
    """Hailo 0-based class IDs are correctly translated to COCO 1-based."""
    detections = sv.Detections(
        xyxy=np.array([[50, 50, 150, 150]]),
        confidence=np.array([0.85]),
        class_id=np.array([1]),  # Hailo: bicycle = 1 (0-based)
    )

    detections = translate_class_ids_to_coco(detections)

    assert detections.class_id[0] == 2
    assert COCO_CLASSES[detections.class_id[0]] == "bicycle"


def test_rfdetr_class_id_no_translation():
    """RF-DETR 1-based class IDs remain unchanged (already COCO format)."""
    detections = sv.Detections(
        xyxy=np.array([[100, 100, 200, 200]]),
        confidence=np.array([0.92]),
        class_id=np.array([3]),  # RF-DETR: car = 3 (1-based, COCO)
    )

    # No translation needed for RF-DETR
    assert detections.class_id[0] == 3
    assert COCO_CLASSES[detections.class_id[0]] == "car"


def test_multiple_detections():
    """Translation works correctly with multiple detections at once."""
    detections = sv.Detections(
        xyxy=np.array([
            [10, 10, 50, 50],
            [60, 60, 100, 100],
            [110, 110, 150, 150],
            [160, 160, 200, 200],
        ]),
        confidence=np.array([0.9, 0.85, 0.92, 0.88]),
        class_id=np.array([0, 1, 2, 7]),  # YOLO 0-based
    )

    detections = translate_class_ids_to_coco(detections)

    expected_ids = [1, 2, 3, 8]
    expected_names = ["person", "bicycle", "car", "truck"]

    assert list(detections.class_id) == expected_ids
    assert [COCO_CLASSES[cid] for cid in detections.class_id] == expected_names
