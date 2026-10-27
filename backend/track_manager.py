from collections import deque
from typing import List, Optional
import time
import math
from .bbox_utils import calculate_centroid


class TrackManager:
    """
    Manages the history of tracks (both active and completed).
    Stores the last N tracks with their trajectories.
    """
    def __init__(self, history_length=100, max_missing_frames=30):
        self.history_length = history_length
        self.max_missing_frames = max_missing_frames

        # Active tracks: {id: {id, class_id, points: [], last_seen: frame_count, start_time, confidence}}
        self.active_tracks = {}

        # History: deque of track dicts
        self.history = deque(maxlen=history_length)

        self.frame_count = 0

        # Speed calculator (set externally when perspective calibration available)
        self.speed_calculator = None

    def update(self, detections) -> List[int]:
        """
        Update tracks with new detections.

        Args:
            detections: moving detections

        Returns:
            List of tracker_ids that completed this frame (not seen for max_missing_frames)
        """
        self.frame_count += 1
        current_ids = set()
        
        # Capture timestamp once for this frame update
        current_time = time.time()

        if len(detections) > 0 and detections.tracker_id is not None:
            tracker_ids = detections.tracker_id
            class_ids = detections.class_id
            confidences = detections.confidence
            boxes = detections.xyxy

            for i, tid in enumerate(tracker_ids):
                tid = int(tid)
                current_ids.add(tid)

                # Calculate centroid
                bbox = tuple(boxes[i])
                cx, cy = calculate_centroid(bbox)
                point = {'x': float(cx), 'y': float(cy), 'time': current_time}

                if tid not in self.active_tracks:
                    # New track
                    self.active_tracks[tid] = {
                        'id': tid,
                        'class_id': int(class_ids[i]) if class_ids is not None else 0,
                        'confidence': float(confidences[i]) if confidences is not None else 0.0,
                        'points': [point],
                        'start_time': current_time,
                        'last_seen': self.frame_count
                    }
                else:
                    # Update existing
                    self.active_tracks[tid]['points'].append(point)
                    self.active_tracks[tid]['last_seen'] = self.frame_count

        # Check for lost tracks and collect completed IDs
        completed_ids = []
        for tid in list(self.active_tracks.keys()):
            if tid not in current_ids:
                if self.frame_count - self.active_tracks[tid]['last_seen'] > self.max_missing_frames:
                    # Finalize track
                    track = self.active_tracks.pop(tid)
                    track['end_time'] = time.time()
                    self.history.append(track)
                    completed_ids.append(tid)

        return completed_ids
                    
    def get_tracks(self, min_distance=0, max_history=10):
        # Convert active tracks to list and combine with history
        all_tracks = list(self.active_tracks.values()) + list(self.history)

        filtered_tracks = []
        for t in all_tracks:
            if len(filtered_tracks) >= max_history:
                break
            if not t['points'] or len(t['points']) < 2:
                if min_distance > 0:
                    continue
                filtered_tracks.append(t)
                continue

            if min_distance > 0:
                p1 = t['points'][0]
                p2 = t['points'][-1]
                # Points are dicts {x, y}
                dist = math.sqrt((p2['x'] - p1['x'])**2 + (p2['y'] - p1['y'])**2)
                if dist < min_distance:
                    continue

            filtered_tracks.append(t)

        filtered_tracks.sort(key=lambda x: x['start_time'], reverse=True)
        return filtered_tracks

    def set_history_length(self, length):
        """Update the history length limit."""
        self.history_length = int(length)
        # Create new deque with new maxlen, preserving existing items
        self.history = deque(self.history, maxlen=self.history_length)

    def get_track_with_speed(
        self,
        tracker_id: int,
        frame_width: int,
        frame_height: int
    ) -> dict:
        """
        Get track data including speed measurement.

        Args:
            tracker_id: Track ID to look up
            frame_width: Current frame width in pixels
            frame_height: Current frame height in pixels

        Returns:
            Track dict with optional 'speed' field containing speed data
        """
        track = self.active_tracks.get(tracker_id)
        if not track:
            return None

        if not self.speed_calculator:
            return track

        speed = self.speed_calculator.calculate(
            track['points'], frame_width, frame_height
        )
        track['speed'] = speed
        return track

    def get_completed_track(self, tracker_id: int) -> Optional[dict]:
        """Get track data from history by ID."""
        for track in self.history:
            if track['id'] == tracker_id:
                return track
        return None
