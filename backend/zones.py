import yaml
import time
import cv2
import uuid
import numpy as np
import supervision as sv
from typing import List, Tuple, Optional, Set, Dict
from abc import ABC, abstractmethod
from .coco_classes import COCO_CLASSES

from shapely.geometry import LineString, Polygon, Point
from shapely.affinity import scale

from .events.event_manager import Event, EventManager, SpeedMeasurement
from .snapshot_saver import save_snapshot_with_metadata


def cross_product(a, b):
    """
    https://en.wikipedia.org/wiki/Cross_product
    """
    return a[0]*b[1] - a[1]*b[0]

class ZoneWrapper(ABC):
    def __init__(
        self,
        name: str,
        trigger_classes: Optional[List[str]] = None,
        store_picture: bool = False,
        id: Optional[str] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.trigger_classes = trigger_classes
        self.store_picture = store_picture
        self.counts = {"in": 0, "out": 0}  # Generic counters
        self.zone_manager = None  # Reference to parent ZoneManager

        # Shapely geometry object (normalized coordinates only)
        self.geometry_normalized = None  # Shapely object in normalized coords (0-1)

    def transform_to_pixels(self, frame_width: int, frame_height: int):
        """Transform normalized geometry to pixel coordinates using Shapely affine transformation."""
        # On-demand transformation - no caching
        return scale(
            self.geometry_normalized,
            xfact=frame_width,
            yfact=frame_height,
            origin=(0, 0)
        )

    @abstractmethod
    def update(
        self,
        detections: sv.Detections,
        event_manager: EventManager,
        original_frame: Optional[np.ndarray] = None
    ):
        pass

    @abstractmethod
    def annotate(self, frame: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    @abstractmethod
    def update_geometry(self, geometry):
        """Update the normalized geometry."""
        pass

    def save_snapshot(
        self,
        frame: np.ndarray,
        event_type: str,
        tracker_id: int,
        class_id: int,
        class_name: str,
        confidence: float,
        bounding_box: List[float],
        direction: Optional[str] = None,
        speed_measurement: Optional[SpeedMeasurement] = None,
    ):
        """
        Save a snapshot with thumbnail and YAML metadata when an event occurs.

        Saves to hierarchical directory: snapshots/YYYY/MM/DD/HH/zone_name/
        """
        if not self.store_picture or frame is None:
            return

        timestamp = time.time()

        # Get track data from zone_manager if available
        trajectory_points = None
        track_start_time = None
        if self.zone_manager:
            track_data = self.zone_manager.get_track_data(tracker_id)
            if track_data:
                trajectory_points = track_data.get('points')
                track_start_time = track_data.get('start_time')

        save_snapshot_with_metadata(
            frame=frame,
            timestamp=timestamp,
            zone_name=self.name,
            event_type=event_type,
            tracker_id=tracker_id,
            class_id=class_id,
            class_name=class_name,
            confidence=confidence,
            bounding_box=list(bounding_box),
            direction=direction,
            speed_measurement=speed_measurement,
            trajectory_points=trajectory_points,
            track_start_time=track_start_time,
        )


class LineZoneWrapper(ZoneWrapper):
    """
    Line zone wrapper with robust crossing detection.

    Uses segment intersection to detect crossings even at low frame rates.
    This works better on slow devices (like RPi) where objects might "jump"
    over the line between frames.
    """

    def __init__(
        self,
        name: str,
        start: Tuple[float, float],
        end: Tuple[float, float],
        trigger_classes: Optional[List[str]] = None,
        store_picture: bool = False,
        id: Optional[str] = None
    ):
        super().__init__(name, trigger_classes, store_picture, id)

        self.geometry_normalized = LineString([start, end])

        # Track previous positions for each tracker_id (as Shapely Points)
        self.tracker_positions: Dict[int, Point] = {}
        # Track which IDs have already crossed (to avoid duplicate events)
        self.crossed_ids: Set[int] = set()

    def _get_center(self, bbox: np.ndarray) -> Tuple[float, float]:
        """Get center point of bounding box [x1, y1, x2, y2]."""
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

    def update(
        self,
        detections: sv.Detections,
        event_manager: EventManager,
        original_frame: Optional[np.ndarray] = None
    ):
        if detections.tracker_id is None or len(detections) == 0:
            return

        # Get frame dimensions
        if original_frame is not None:
            frame_height, frame_width = original_frame.shape[:2]
        else:
            # Fallback to detection bbox max values (less reliable)
            frame_width = int(np.max(detections.xyxy[:, 2])) if len(detections) > 0 else 1280
            frame_height = int(np.max(detections.xyxy[:, 3])) if len(detections) > 0 else 720

        # Transform line to pixel coordinates using Shapely
        line_pixels = self.transform_to_pixels(frame_width, frame_height)

        timestamp = time.time()
        current_ids = set()

        for idx in range(len(detections)):
            tracker_id = int(detections.tracker_id[idx])
            current_ids.add(tracker_id)

            # Get current center position as Shapely Point
            bbox = detections.xyxy[idx]
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2
            current_pos = Point(center_x, center_y)

            # Check if we have a previous position
            if tracker_id in self.tracker_positions:
                prev_pos = self.tracker_positions[tracker_id]

                # Create movement path as LineString and check intersection with zone line
                movement_path = LineString([prev_pos, current_pos])

                if tracker_id not in self.crossed_ids:
                    if movement_path.intersects(line_pixels):
                        # Determine direction using cross product
                        # Get line vector
                        line_coords = list(line_pixels.coords)
                        line_vec = (
                            line_coords[1][0] - line_coords[0][0],
                            line_coords[1][1] - line_coords[0][1]
                        )
                        # Get movement vector
                        move_vec = (
                            current_pos.x - prev_pos.x,
                            current_pos.y - prev_pos.y
                        )

                        direction = "in" if cross_product(line_vec, move_vec) > 0 else "out"

                        class_id = int(detections.class_id[idx])
                        confidence = float(detections.confidence[idx])
                        class_name = COCO_CLASSES.get(class_id, "unknown")

                        # Check class filter
                        if self.trigger_classes and class_name not in self.trigger_classes:
                            pass  # Skip this detection
                        else:
                            # Update our internal counters
                            self.counts[direction] += 1

                            # Mark as crossed
                            self.crossed_ids.add(tracker_id)

                            # Get speed measurement if available
                            speed_measurement = self.zone_manager.get_speed_measurement(
                                tracker_id, frame_width, frame_height
                            )

                            # Save snapshot with metadata if enabled
                            self.save_snapshot(
                                frame=original_frame,
                                event_type="line_cross",
                                tracker_id=tracker_id,
                                class_id=class_id,
                                class_name=class_name,
                                confidence=confidence,
                                bounding_box=bbox,
                                direction=direction,
                                speed_measurement=speed_measurement,
                            )

                            # Create and queue event (dispatched when track completes)
                            event = Event(
                                timestamp=timestamp,
                                zone_name=self.name,
                                event_type="line_cross",
                                tracker_id=tracker_id,
                                class_id=class_id,
                                class_name=class_name,
                                confidence=confidence,
                                direction=direction,
                                speed_measurement=speed_measurement
                            )
                            event_manager.queue_event(event)

            # Store current position for next frame
            self.tracker_positions[tracker_id] = current_pos

        # Clean up old tracker IDs that are no longer detected
        stale_ids = set(self.tracker_positions.keys()) - current_ids
        for stale_id in stale_ids:
            del self.tracker_positions[stale_id]
            self.crossed_ids.discard(stale_id)

    def annotate(self, frame: np.ndarray) -> np.ndarray:
        # Get actual frame dimensions
        frame_height, frame_width = frame.shape[:2]

        # Transform line to pixel coordinates using Shapely
        line_pixels = self.transform_to_pixels(frame_width, frame_height)

        # Extract coordinates from Shapely LineString
        coords = list(line_pixels.coords)
        pt1 = (int(coords[0][0]), int(coords[0][1]))
        pt2 = (int(coords[1][0]), int(coords[1][1]))

        # Draw the line
        cv2.line(frame, pt1, pt2, color=(0, 255, 255), thickness=2)

        # Draw count text at midpoint
        mid_x = int((pt1[0] + pt2[0]) / 2)
        mid_y = int((pt1[1] + pt2[1]) / 2)
        text = f"In: {self.counts['in']} Out: {self.counts['out']}"
        cv2.putText(frame, text, (mid_x - 60, mid_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        return frame

    def to_dict(self) -> dict:
        # Return normalized coordinates (preserve float precision)
        return {
            'id': self.id,
            'name': self.name,
            'type': 'line',
            'geometry': [[p[0], p[1]] for p in self.geometry_normalized.coords],
            'trigger_classes': self.trigger_classes,
            'store_picture': self.store_picture
        }

    def update_geometry(self, geometry):
        """Update line geometry with new normalized coordinates."""
        if len(geometry) != 2:
            raise ValueError("Line geometry must have exactly 2 points")

        self.geometry_normalized = LineString([geometry[0], geometry[1]])


class PolygonZoneWrapper(ZoneWrapper):
    def __init__(
        self,
        name: str,
        polygon: List[Tuple[int, int]],
        trigger_classes: Optional[List[str]] = None,
        store_picture: bool = False,
        id: Optional[str] = None
    ):
        super().__init__(name, trigger_classes, store_picture, id)

        # Store normalized coordinates
        self.polygon_coords = [(float(p[0]), float(p[1])) for p in polygon]

        # Create Shapely Polygon in normalized coordinates
        self.geometry_normalized = Polygon(self.polygon_coords)

        # For supervision integration (will be updated with pixel coords)
        self.polygon_zone = None
        self.annotator = None
        self._last_frame_size = None  # Track when to recreate supervision zone
        self._setup_supervision_zone(width=1280, height=720)  # Default, will update on first frame

        self.current_tracker_ids: Set[int] = set()

    def _setup_supervision_zone(self, width: int, height: int):
        """Setup supervision polygon zone with pixel coordinates."""
        # Transform to pixels
        poly_pixels = self.transform_to_pixels(width, height)

        # Convert Shapely Polygon to numpy array for supervision
        coords_array = np.array(poly_pixels.exterior.coords[:-1], dtype=np.int32)

        # Create supervision PolygonZone
        self.polygon_zone = sv.PolygonZone(
            polygon=coords_array,
            triggering_anchors=[sv.Position.CENTER]
        )

        # Create annotator
        self.annotator = sv.PolygonZoneAnnotator(
            zone=self.polygon_zone,
            color=sv.Color.WHITE,
            thickness=2,
            text_thickness=2,
            text_scale=0.5
        )

    def update(
        self,
        detections: sv.Detections,
        event_manager: EventManager,
        original_frame: Optional[np.ndarray] = None
    ):
        # Get frame dimensions
        if original_frame is not None:
            frame_height, frame_width = original_frame.shape[:2]
        else:
            frame_width = int(np.max(detections.xyxy[:, 2])) if len(detections) > 0 else 1280
            frame_height = int(np.max(detections.xyxy[:, 3])) if len(detections) > 0 else 720

        # Update supervision zone if dimensions changed
        if self._last_frame_size != (frame_width, frame_height):
            self._setup_supervision_zone(frame_width, frame_height)
            self._last_frame_size = (frame_width, frame_height)

        # Trigger zone check
        is_in_zone = self.polygon_zone.trigger(detections)
        
        # Get currently present IDs
        present_indices = np.where(is_in_zone)[0]
        present_ids = set()
        
        timestamp = time.time()
        
        if detections.tracker_id is not None:
            for idx in present_indices:
                tracker_id = detections.tracker_id[idx]
                present_ids.add(tracker_id)
                
                # Check if this is a new entry
                if tracker_id not in self.current_tracker_ids:
                    class_id = detections.class_id[idx] if detections.class_id is not None else -1
                    class_name = COCO_CLASSES.get(class_id, "unknown")
                    
                    if self.trigger_classes and class_name not in self.trigger_classes:
                        continue

                    conf = detections.confidence[idx] if detections.confidence is not None else 0.0
                    bbox = detections.xyxy[idx]

                    # Get speed measurement if available
                    speed_measurement = self.zone_manager.get_speed_measurement(
                        int(tracker_id), frame_width, frame_height
                    )

                    # Save snapshot with metadata if enabled
                    self.save_snapshot(
                        frame=original_frame,
                        event_type="zone_enter",
                        tracker_id=int(tracker_id),
                        class_id=int(class_id),
                        class_name=class_name,
                        confidence=float(conf),
                        bounding_box=bbox,
                        speed_measurement=speed_measurement,
                    )

                    event = Event(
                        timestamp=timestamp,
                        zone_name=self.name,
                        event_type="zone_enter",
                        tracker_id=int(tracker_id),
                        class_id=int(class_id),
                        class_name=class_name,
                        confidence=float(conf),
                        speed_measurement=speed_measurement
                    )
                    event_manager.queue_event(event)
        
        # Check for exits (ids in current_tracker_ids but not in present_ids)
        # Note: This is tricky because an object might just be lost/occluded.
        # But for strictly "in zone" logic, if it's not detected in zone, it's out (or lost).
        # We'll rely on the detections passed in. If the tracker is lost, it won't be in detections.
        
        # To robustly handle exits, we might need to check if the tracker is still active globally.
        # For now, we'll keep it simple: if it was in, and now it's not in (but potentially still tracked elsewhere), it exited.
        # However, we don't have access to "elsewhere" easily here without full track state.
        # We will assume if it's not in the zone trigger, it exited.
        
        for tracker_id in self.current_tracker_ids:
            if tracker_id not in present_ids:
                # It left the zone (or track was lost)
                # We can't easily get class info here if it's gone from detections.
                # So we skip exit event for now or store metadata.
                pass
                
        self.current_tracker_ids = present_ids

    def annotate(self, frame: np.ndarray) -> np.ndarray:
        # Get frame dimensions
        frame_height, frame_width = frame.shape[:2]

        # Update supervision zone if dimensions changed
        if self._last_frame_size != (frame_width, frame_height):
            self._setup_supervision_zone(frame_width, frame_height)
            self._last_frame_size = (frame_width, frame_height)

        # Use supervision annotator
        return self.annotator.annotate(scene=frame)

    def to_dict(self) -> dict:
        # Return normalized coordinates (preserve float precision)
        return {
            'id': self.id,
            'name': self.name,
            'type': 'polygon',
            'geometry': [[p[0], p[1]] for p in self.polygon_coords],
            'trigger_classes': self.trigger_classes,
            'store_picture': self.store_picture
        }

    def update_geometry(self, geometry):
        """Update polygon geometry with new normalized coordinates."""
        if len(geometry) < 3:
            raise ValueError("Polygon geometry must have at least 3 points")

        self.polygon_coords = [(float(p[0]), float(p[1])) for p in geometry]

        # Recreate Shapely Polygon
        self.geometry_normalized = Polygon(self.polygon_coords)

        # Reset supervision zone (will be recreated on next update/annotate)
        self._last_frame_size = None
        self.polygon_zone = None
        self.annotator = None
