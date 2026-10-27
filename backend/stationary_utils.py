import numpy as np
from collections import deque, defaultdict
from .bbox_utils import calculate_bbox_displacement

class ObjectHistoryTracker:
    """
    Base class for tracking object history (bounding boxes).
    """
    def __init__(self, history_length=30):
        """
        Initialize the tracker.

        Args:
            history_length (int): The number of frames to keep in history.
        """
        self.history_length = history_length
        # Store history of bounding boxes: {tracker_id: deque([(x1, y1, x2, y2), ...])}
        self.history = defaultdict(lambda: deque(maxlen=history_length))

    def update(self, detections):
        """
        Update the history with new detections.

        Args:
            detections: A supervision.Detections object or any object with 'tracker_id' and 'xyxy' attributes.
        """
        if detections.tracker_id is None:
            return

        for tracker_id, box in zip(detections.tracker_id, detections.xyxy):
            self.history[tracker_id].append(tuple(box))


class MovingObjectDetector(ObjectHistoryTracker):
    """
    Detector for identifying moving objects based on total centroid displacement.
    """
    def is_moving(self, tracker_id, min_displacement=10.0):
        """
        Check if object has moved significantly from its initial position.
          """
        if tracker_id not in self.history:
            return False

        history = self.history[tracker_id]
        
        if len(history) < 2:
            return False

        # Get current and oldest bounding boxes
        curr_box = history[-1]
        old_box = history[0]

        # Calculate displacement between centroids
        displacement = calculate_bbox_displacement(old_box, curr_box)

        return displacement > min_displacement


# --- Test Cases ---
if __name__ == "__main__":
    print("Running test cases...")
    
    class MockDetections:
        def __init__(self, xyxy, tracker_id):
            self.xyxy = np.array(xyxy)
            self.tracker_id = np.array(tracker_id)

    # --- Moving Tests ---
    print("\n--- MovingObjectDetector Tests ---")
    mov_detector = MovingObjectDetector(history_length=5)

    # Test 1: Stationary (should not be moving)
    for _ in range(5):
        dets = MockDetections(xyxy=[[100, 100, 150, 150]], tracker_id=[1])
        mov_detector.update(dets)
    print(f"ID 1 Moving? {mov_detector.is_moving(1, min_displacement=5)} (Expected: False)")

    # Test 2: Moving (should be moving)
    # Moves 10px per frame -> total 40px displacement
    for i in range(5):
        off = i * 10
        dets = MockDetections(xyxy=[[100+off, 100+off, 150+off, 150+off]], tracker_id=[2])
        mov_detector.update(dets)
    print(f"ID 2 Moving? {mov_detector.is_moving(2, min_displacement=5)} (Expected: True)")
