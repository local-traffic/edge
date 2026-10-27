"""
Motion detector implementation using OpenCV background subtraction.
"""

import numpy as np
import supervision as sv
from .base import BaseDetector


class MotionDetector(BaseDetector):
    """
    Detector that uses OpenCV background subtraction to detect moving blobs.
    Often referred to as "Lizard Brain" or used in Norfair examples for fast motion tracking.
    """
    def __init__(self, history=500, varThreshold=25, detectShadows=True, min_area=800):
        import cv2
        self.backSub = cv2.createBackgroundSubtractorMOG2(
            history=history, varThreshold=varThreshold, detectShadows=detectShadows
        )
        self.min_area = min_area
        print(f"MotionDetector initialized with history={history}, varThreshold={varThreshold}, min_area={min_area}")

    def predict(self, image, conf_threshold=0.3):
        import cv2
        import numpy as np
        import supervision as sv

        # Apply background subtraction
        fgMask = self.backSub.apply(image)

        # Threshold to binarize (remove shadows if needed or keep them)
        # MOG2: shadows are gray (127), foreground is white (255)
        # We treat shadows as background (cutoff at 250)
        _, fgMask = cv2.threshold(fgMask, 250, 255, cv2.THRESH_BINARY)

        # Morphological operations to remove noise and fill gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel)

        # Dilate to merge close blobs
        dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        fgMask = cv2.dilate(fgMask, dilate_kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(fgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        xyxy = []
        confidences = []
        class_ids = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > self.min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                xyxy.append([x, y, x + w, y + h])
                # Assign confidence 1.0 as it is a hard detection
                confidences.append(1.0)
                # Class 0 for "moving object"
                class_ids.append(0)

        if not xyxy:
            return sv.Detections.empty()

        detections = sv.Detections(
            xyxy=np.array(xyxy),
            confidence=np.array(confidences),
            class_id=np.array(class_ids)
        )

        return detections
