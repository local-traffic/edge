import numpy as np
import supervision as sv

try:
    # Try importing OcSort (newer versions) or OCSORT (older versions)
    try:
        from boxmot import OcSort as OCSORT
    except ImportError:
        from boxmot import OCSORT
    BOXMOT_AVAILABLE = True
except ImportError:
    BOXMOT_AVAILABLE = False
    OCSORT = None

class BoxmotTrackerWrapper:
    """
    Wrapper for Boxmot trackers to make them compatible with Supervision based pipeline.
    """
    def __init__(self, tracker_type="ocsort", track_buffer=30, match_thresh=0.8, frame_rate=30):
        if not BOXMOT_AVAILABLE:
            raise ImportError("boxmot library not installed. Please install it using 'pip install boxmot'")
        
        self.tracker_type = tracker_type
        
        if tracker_type == "ocsort":
            # OCSORT configuration
            # max_age: corresponds to track_buffer (frames to keep lost tracks)
            self.tracker = OCSORT(
                max_age=track_buffer,
                det_thresh=0.0, # We filter before passing to tracker usually
            )
        else:
            raise ValueError(f"Unsupported tracker type: {tracker_type}")

    def update_with_detections(self, detections: sv.Detections, frame=None) -> sv.Detections:
        """
        Update tracker with detections and frame.
        
        Args:
            detections: supervision Detections object
            frame: numpy array of the current frame (required by Boxmot)
            
        Returns:
            supervision Detections object with tracker_id
        """
        if frame is None:
            # Boxmot usually requires frame. If None, it might fail or we should handle it.
            # We assume frame is provided.
            pass

        # Convert sv.Detections to boxmot format: [x1, y1, x2, y2, conf, cls]
        if len(detections) == 0:
            dets = np.empty((0, 6))
        else:
            xyxy = detections.xyxy
            conf = detections.confidence
            cls = detections.class_id
            
            # Ensure proper shapes
            if conf is None:
                conf = np.ones(len(xyxy))
            if cls is None:
                cls = np.zeros(len(xyxy))
                
            dets = np.column_stack((xyxy, conf, cls))

        # Update tracker
        # boxmot update expects (dets, img)
        tracks = self.tracker.update(dets, frame)
        
        # Convert result back to sv.Detections
        # tracks format: [x1, y1, x2, y2, id, conf, cls]
        
        if len(tracks) == 0:
            return sv.Detections.empty()
            
        # Boxmot output might vary slightly by version, but usually standard.
        # Ensure we have at least 7 columns
        if tracks.shape[1] >= 7:
            xyxy = tracks[:, 0:4]
            tracker_id = tracks[:, 4].astype(int)
            confidence = tracks[:, 5]
            class_id = tracks[:, 6].astype(int)
            
            return sv.Detections(
                xyxy=xyxy,
                confidence=confidence,
                class_id=class_id,
                tracker_id=tracker_id
            )
        else:
             print(f"Warning: Unexpected track format from boxmot: {tracks.shape}")
             return sv.Detections.empty()


class SupervisionTrackerWrapper:
    """
    Wrapper for Supervision trackers (like ByteTrack) to unify interface.
    """
    def __init__(self, tracker):
        self.tracker = tracker
        
    def update_with_detections(self, detections: sv.Detections, frame=None) -> sv.Detections:
        # Supervision trackers don't use frame
        return self.tracker.update_with_detections(detections)
