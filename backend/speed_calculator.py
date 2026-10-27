"""
Speed measurement using perspective transformation.

Calculates real-world speed from track positions using the calibrated
perspective transformation.
"""

from typing import List, Optional, Callable
import math

from .events.event_manager import SpeedMeasurement


MIN_TRACK_POINTS = 5
ROLLING_WINDOW_FRAMES = 10
CALIBRATION_ERROR = 0.10
POSITION_ERROR_M = 0.5
MAX_ERROR_PCT = 50.0
MAX_PHYSICAL_SPEED_MS = 80.0  # ~216 km/h
SMOOTHING_FACTOR = 0.3        # EMA factor

class SpeedCalculator:
    def __init__(
        self,
        transform_func: Callable[[float, float, int, int], Optional[tuple]]
    ):
        """
        Initialize speed calculator.

        Args:
            transform_func: Function to transform normalized coords to world coords
        """
        self.transform = transform_func


    def calculate(
        self,
        points: List[dict],
        frame_width: int,
        frame_height: int
    ) -> SpeedMeasurement:
        """
        Calculate speed using timestamps if available.
        """
        if len(points) < MIN_TRACK_POINTS:
            return SpeedMeasurement(is_valid=False, comment=f"track too short ({len(points)} points)")

        world_points = self._transform_points(points, frame_width, frame_height)
        if len(world_points) < 2:
            return SpeedMeasurement(is_valid=False, comment="transform failed")

        # Calculate segment speeds
        segment_data = [] # List of (speed, weight)
        total_distance_segments = 0.0
        total_distance_straight = 0.0
        total_time = 0.0

        for i in range(1, len(world_points)):
            p1 = world_points[i - 1]
            p2 = world_points[i]

            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            d = math.hypot(dx, dy)

            t1 = p1[2]
            t2 = p2[2]
            dt = t2 - t1

            if dt <= 0.001:  # Avoid division by zero or duplicate timestamps, even with fps 100 there should be more, so probably some error
                continue

            speed = d / dt
            
            if speed > MAX_PHYSICAL_SPEED_MS:
                continue

            segment_data.append(speed)
            total_distance_segments += d
            total_time += dt


        if not segment_data:
            return SpeedMeasurement(is_valid=False, comment="no valid speed segments")

        # Calculate current speed using robust smoothing (e.g., EMA on recent segments)
        # We focus on the last few segments for "current" speed
        recent_window = segment_data[-min(len(segment_data), ROLLING_WINDOW_FRAMES):]
        
        # Simple weighted average (recent points matter more? or just average?)
        # Let's use simple average of the retained valid segments for stability
        current_speed = sum(recent_window) / len(recent_window)

        # Average over the whole track
        avg_speed = total_distance_segments / total_time if total_time > 0 else 0
        total_distance_straight = math.hypot(world_points[0][0] - world_points[-1][0],
                                             world_points[0][1] - world_points[-1][1])
        total_time_straight = world_points[-1][2] - world_points[0][2]
        avg_speed = total_distance_straight/total_time_straight

        max_speed = max(segment_data)
        min_speed = min(segment_data)
        
        error_pct = self._estimate_error(total_distance_segments)

        return SpeedMeasurement(
            is_valid=True,
            comment="",
            speed_ms=current_speed,
            avg_speed_ms=avg_speed,
            max_speed_ms=max_speed,
            min_speed_ms=min_speed,
            track_distance_m=total_distance_segments,
            track_duration_s=total_time,
            speed_error_pct=error_pct
        )

    def _transform_points(
        self,
        points: List[dict],
        frame_width: int,
        frame_height: int
    ) -> List[tuple]:
        """
        Transform pixel points to world coordinates.
        Returns list of (x, y, timestamp).
        """
        world_points = []
        for p in points:
            norm_x = p['x'] / frame_width
            norm_y = p['y'] / frame_height
            result = self.transform(norm_x, norm_y, frame_width, frame_height)
            if result:
                # Append timestamp (default to 0 if not present)
                t = p.get('time', 0.0)
                world_points.append(result + (t,))
        return world_points

    def _estimate_error(self, distance: float) -> float:
        """Estimate measurement error percentage."""
        if distance < 1.0:
            return MAX_ERROR_PCT

        distance_error = (POSITION_ERROR_M * 2) / distance
        total_error = math.sqrt(CALIBRATION_ERROR ** 2 + distance_error ** 2)
        return min(total_error * 100, MAX_ERROR_PCT)
