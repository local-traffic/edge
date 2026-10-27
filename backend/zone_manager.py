import time
import cv2
import numpy as np
import supervision as sv
from typing import List, Tuple, Optional, Set, Dict
from abc import ABC, abstractmethod
from .coco_classes import COCO_CLASSES

# Shapely imports for geometry operations
from shapely.geometry import LineString, Polygon, Point
from shapely.affinity import scale

from .zones import ZoneWrapper, LineZoneWrapper, PolygonZoneWrapper
from .events.event_manager import Event, EventManager, SpeedMeasurement
from .app_config import save_yaml_config


class ZoneManager:
    def __init__(self, event_manager: EventManager, track_manager, config_data: dict, config_path: str, video_source=None):
        self.event_manager = event_manager
        self.zones: List[ZoneWrapper] = []
        self.video_source = video_source
        self.track_manager = track_manager
        self.config_path = config_path

        self.camera_settings = config_data.get('camera_settings', {})
        self.perspective_transform = config_data.get('perspective_transform', {})
        self.detection_settings = config_data.get('detection_settings', {})
        self.noise_measurement = config_data.get('noise_measurement', {})

        if self.video_source and hasattr(self.video_source, 'set_af_window'):
            af_window = self.camera_settings.get('af_window')
            if af_window:
                print(f"Applying saved AfWindow: {af_window}")
                self.video_source.set_af_window(tuple(af_window))

        for zone_cfg in config_data.get('zones', []):
            self.add_zone(zone_cfg, save=False)

    def get_speed_measurement(
        self,
        tracker_id: int,
        frame_width: int,
        frame_height: int
    ) -> SpeedMeasurement:
        """Get speed measurement for a tracker."""
        if not self.track_manager.speed_calculator:
            return SpeedMeasurement(is_valid=False, comment='no perspective calibration')

        track = self.track_manager.get_track_with_speed(
            tracker_id, frame_width, frame_height
        )
        if not track or 'speed' not in track:
            return SpeedMeasurement(is_valid=False, comment='track not found')

        return track['speed']

    def get_track_data(self, tracker_id: int) -> Optional[Dict]:
        """
        Get track data including trajectory points for snapshot metadata.

        Returns dict with 'points' (trajectory) and 'start_time', or None if not found.
        """
        track = self.track_manager.active_tracks.get(tracker_id)
        if track:
            return {
                'points': track.get('points', []),
                'start_time': track.get('start_time'),
            }
        return None

    def add_zone(self, zone_cfg, save=True):
        name = zone_cfg['name']
        z_type = zone_cfg['type']
        coords = zone_cfg.get('geometry')
        trigger_classes = zone_cfg.get('trigger_classes')
        store_picture = zone_cfg.get('store_picture', False)
        z_id = zone_cfg.get('id')

        zone = None
        if z_type == 'line':
            if len(coords) != 2:
                print(f"Warning: Line zone '{name}' must have exactly 2 points. Skipping.")
                return
            zone = LineZoneWrapper(name, coords[0], coords[1], trigger_classes, store_picture, z_id)
        elif z_type == 'polygon':
            zone = PolygonZoneWrapper(name, coords, trigger_classes, store_picture, z_id)
        else:
            print(f"Warning: Unknown zone type '{z_type}' for '{name}'. Skipping.")
            return

        zone.zone_manager = self
        self.zones.append(zone)

        if save:
            self.save_config()

    def delete_zone(self, name):
        self.zones = [z for z in self.zones if z.name != name]
        self.save_config()

    def update_zone(self, identifier, zone_config):
        target_zone = None

        # Try to find by ID first (if identifier looks like UUID or zone has ID)
        for z in self.zones:
            if hasattr(z, 'id') and str(z.id) == str(identifier):
                target_zone = z
                break

        # Fallback to name search
        if not target_zone:
            for z in self.zones:
                if z.name == identifier:
                    target_zone = z
                    break

        if target_zone:
            if target_zone.to_dict()['type'] == zone_config['type']:
                target_zone.name = zone_config.get('name', target_zone.name)
                target_zone.trigger_classes = zone_config.get(
                    'trigger_classes',
                    target_zone.trigger_classes
                )
                target_zone.store_picture = zone_config.get(
                    'store_picture',
                    target_zone.store_picture
                )
                if 'geometry' in zone_config:
                    target_zone.update_geometry(zone_config['geometry'])
                self.save_config()
                return
            else:
                # Type changed, recreate
                self.delete_zone(target_zone.name)
                self.add_zone(zone_config)
                return

    def get_zones_config(self):
        return [z.to_dict() for z in self.zones]

    def save_config(self):
        data = {'zones': self.get_zones_config()}

        if self.camera_settings:
            data['camera_settings'] = self.camera_settings

        if self.perspective_transform:
            data['perspective_transform'] = self.perspective_transform

        if self.detection_settings:
            data['detection_settings'] = self.detection_settings

        if self.noise_measurement:
            data['noise_measurement'] = self.noise_measurement

        save_yaml_config(self.config_path, data)

    def get_camera_settings(self) -> dict:
        """Get current camera settings."""
        settings = self.camera_settings.copy()

        # Add runtime info if available
        if self.video_source and hasattr(self.video_source, 'get_af_window'):
            settings['current_af_window'] = self.video_source.get_af_window()

        return settings

    def update_camera_settings(self, settings: dict) -> bool:
        """Update camera settings and apply to camera."""
        try:
            # Update in-memory settings
            self.camera_settings = settings

            # Apply to camera if PiCamera
            if self.video_source and hasattr(self.video_source, 'set_af_window'):
                af_window = settings.get('af_window')
                if af_window:
                    success = self.video_source.set_af_window(tuple(af_window))
                    if not success:
                        return False
                else:
                    # Reset to default autofocus
                    self.video_source.reset_af_window()

            # Save to file
            self.save_config()
            return True
        except Exception as e:
            print(f"Error updating camera settings: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_detection_settings(self) -> dict:
        """Get current detection settings (threshold etc)."""
        return self.detection_settings.copy()

    def update_detection_settings(self, settings: dict) -> bool:
        """Update detection settings and persist to config file."""
        try:
            self.detection_settings.update(settings)
            self.save_config()
            return True
        except Exception as e:
            print(f"Error updating detection settings: {e}")
            return False

    def update_noise_measurement(self, settings: dict) -> bool:
        try:
            self.noise_measurement.update(settings)
            self.save_config()
            return True
        except Exception as e:
            print(f"Error updating noise measurement settings: {e}")
            return False

    def update(
        self,
        detections: sv.Detections,
        original_frame: Optional[np.ndarray] = None
    ):
        for zone in self.zones:
            zone.update(detections, self.event_manager, original_frame)

    def annotate(self, frame: np.ndarray) -> np.ndarray:
        for zone in self.zones:
            frame = zone.annotate(frame)
        return frame

    def get_perspective_transform(self) -> Optional[dict]:
        """Get current perspective transform calibration."""
        return self.perspective_transform if self.perspective_transform else None

    def update_perspective_transform(self, config: dict) -> bool:
        """Update perspective transform calibration."""
        try:
            corners = config.get('corners', [])
            edge_lengths = config.get('edge_lengths', {})

            if len(corners) != 4:
                print("Error: Perspective transform requires exactly 4 corners")
                return False

            required_edges = ['top', 'left', 'bottom']
            if not all(k in edge_lengths for k in required_edges):
                print(f"Error: edge_lengths must have {required_edges}")
                return False

            self.perspective_transform = {
                'corners': corners,
                'edge_lengths': edge_lengths
            }
            self.save_config()
            return True
        except Exception as e:
            print(f"Error updating perspective transform: {e}")
            return False

    def delete_perspective_transform(self):
        """Remove perspective transform calibration."""
        self.perspective_transform = {}
        self.save_config()

    def getPerspectiveTransformation():
        if not self.perspective_transform:
            return None

    def transform_point_to_world(
        self,
        x: float,
        y: float,
        frame_width: int,
        frame_height: int
    ) -> Optional[Tuple[float, float]]:
        """Transform image point (normalized 0-1) to world coordinates (meters)."""
        if not self.perspective_transform:
            return None

        corners = self.perspective_transform.get('corners', [])
        edge_lengths = self.perspective_transform.get('edge_lengths', {})

        if len(corners) != 4:
            return None

        # Source points in pixel coordinates
        src_points = np.float32([
            [c[0] * frame_width, c[1] * frame_height] for c in corners
        ])

        # Destination points in world coordinates (meters)
        top = edge_lengths.get('top', 10.0)
        left = edge_lengths.get('left', 15.0)
        bottom = edge_lengths.get('bottom', 10.0)

        dst_points = np.float32([
            [0, 0],           # Top-left
            [top, 0],         # Top-right
            [bottom, left],   # Bottom-right
            [0, left]         # Bottom-left
        ])

        # Compute transformation matrix
        M = cv2.getPerspectiveTransform(src_points, dst_points)

        # Transform the point
        point = np.float32([[x * frame_width, y * frame_height]])
        transformed = cv2.perspectiveTransform(point.reshape(-1, 1, 2), M)

        return (float(transformed[0][0][0]), float(transformed[0][0][1]))



