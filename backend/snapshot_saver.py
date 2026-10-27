"""
Snapshot saver with metadata for traffic detection events.

Saves JPEG snapshots with accompanying YAML metadata files containing
class, speed, bounding box, trajectory history, and event information.
"""
import os
import cv2
import yaml
import numpy as np
import datetime
import urllib.parse
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from .events.event_manager import SpeedMeasurement


def convert_numpy_to_python(obj):
    """
    Recursively convert NumPy types to native Python types for YAML serialization.
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj


THUMBNAIL_WIDTH = 80


def get_snapshot_directory(timestamp: float, zone_name: str, base_dir: str = "snapshots") -> str:
    dt = datetime.datetime.fromtimestamp(timestamp)
    safe_zone = urllib.parse.quote(zone_name, safe='')

    return os.path.join(
        base_dir,
        f"{dt.year}{dt.month:02d}{dt.day:02d}-{safe_zone}"
    )


def generate_filename_base(timestamp: float, class_name: str, event_type: str) -> str:
    """Generate base filename: HHMMSS,key=value,key=value"""
    dt = datetime.datetime.fromtimestamp(timestamp)
    return f"{dt.strftime('%H%M%S.%f')},class={class_name},event-type={event_type}"


def create_thumbnail(frame, width: int = THUMBNAIL_WIDTH):
    """Create a resized thumbnail maintaining aspect ratio."""
    h, w = frame.shape[:2]
    height = int(h * width / w)
    return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)


def save_snapshot_with_metadata(
    frame,
    timestamp: float,
    zone_name: str,
    event_type: str,
    tracker_id: int,
    class_id: int,
    class_name: str,
    confidence: float,
    bounding_box: List[float],
    direction: Optional[str] = None,
    speed_measurement: Optional[SpeedMeasurement] = None,
    trajectory_points: Optional[List[Dict[str, float]]] = None,
    track_start_time: Optional[float] = None,
    base_dir: str = "snapshots"
) -> Optional[str]:
    """
    Save snapshot with thumbnail and YAML metadata.

    Args:
        frame: OpenCV image (BGR format)
        timestamp: Unix timestamp of event
        zone_name: Name of the zone where event occurred
        event_type: line_cross, zone_enter, or zone_exit
        tracker_id: Object tracking ID
        class_id: COCO class ID
        class_name: Human-readable class name
        confidence: Detection confidence (0-1)
        bounding_box: [x1, y1, x2, y2] in pixels
        direction: "in" or "out" for line crossings
        speed_measurement: Speed data if available
        trajectory_points: List of {x, y, time} dicts
        track_start_time: Unix timestamp when track started
        base_dir: Base directory for snapshots

    Returns:
        Path to saved YAML metadata file, or None if save failed
    """
    if frame is None:
        return None

    directory = get_snapshot_directory(timestamp, zone_name, base_dir)
    os.makedirs(directory, exist_ok=True)

    filename_base = generate_filename_base(timestamp, class_name, event_type)

    image_filename = f"{filename_base}.jpg"
    thumb_filename = f"{filename_base}_thumb.jpg"
    meta_filename = f"{filename_base}.yaml"

    image_path = os.path.join(directory, image_filename)
    thumb_path = os.path.join(directory, thumb_filename)
    meta_path = os.path.join(directory, meta_filename)

    # Save full image
    cv2.imwrite(image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

    # Save thumbnail
    thumbnail = create_thumbnail(frame)
    cv2.imwrite(thumb_path, thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])

    # Build metadata
    dt = datetime.datetime.fromtimestamp(timestamp)
    frame_height, frame_width = frame.shape[:2]

    metadata = {
        'image_file': image_filename,
        'thumbnail_file': thumb_filename,
        'event': {
            'type': event_type,
            'zone_name': zone_name,
            'timestamp': dt.isoformat(),
            'timestamp_unix': timestamp,
        },
        'object': {
            'class_id': class_id,
            'class_name': class_name,
            'confidence': round(confidence, 4),
            'tracker_id': tracker_id,
            'bounding_box': [round(x, 1) for x in bounding_box],
        },
        'frame': {
            'width': frame_width,
            'height': frame_height,
        }
    }

    if direction:
        metadata['event']['direction'] = direction

    # Add speed data if available
    if speed_measurement and speed_measurement.is_valid:
        metadata['speed'] = {
            'current_ms': round(speed_measurement.speed_ms, 2),
            'avg_ms': round(speed_measurement.avg_speed_ms, 2),
            'max_ms': round(speed_measurement.max_speed_ms, 2),
            'min_ms': round(speed_measurement.min_speed_ms, 2),
            'distance_m': round(speed_measurement.track_distance_m, 2),
            'duration_s': round(speed_measurement.track_duration_s, 2),
            'error_pct': round(speed_measurement.speed_error_pct, 1),
            'is_valid': speed_measurement.is_valid,
        }
    elif speed_measurement:
        metadata['speed'] = {
            'is_valid': False,
            'comment': speed_measurement.comment,
        }

    # Add trajectory if available
    if trajectory_points and len(trajectory_points) > 0:
        # Convert points for YAML
        points_for_yaml = [
            {'x': round(p['x'], 1), 'y': round(p['y'], 1), 't': round(p['time'], 3)}
            for p in trajectory_points
        ]

        trajectory = {
            'point_count': len(points_for_yaml),
            'points': points_for_yaml,
        }

        if track_start_time:
            trajectory['start_time'] = datetime.datetime.fromtimestamp(track_start_time).isoformat()

        if trajectory_points:
            last_time = trajectory_points[-1].get('time', timestamp)
            trajectory['end_time'] = datetime.datetime.fromtimestamp(last_time).isoformat()

            if track_start_time:
                trajectory['duration_s'] = round(last_time - track_start_time, 3)

        metadata['trajectory'] = trajectory

    # Save metadata YAML (convert NumPy types to native Python for compatibility)
    with open(meta_path, 'w') as f:
        yaml.dump(convert_numpy_to_python(metadata), f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return meta_path
