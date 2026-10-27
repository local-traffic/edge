"""
Console event listener for detection events.
Prints to console when objects are detected in zones.
"""

import time
from typing import Optional, List

from .event_manager import Event


class ConsoleEventListener:
    """
    Event listener that prints detection events to console.

    Can filter by class names and/or event types.
    """

    # Vehicle classes for convenience
    VEHICLE_CLASSES = ["car", "truck", "bus", "motorcycle", "bicycle"]

    def __init__(
        self,
        class_filter: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
        verbose: bool = True
    ):
        """
        Args:
            class_filter: List of class names to listen for (e.g., ["car", "truck"]).
                         If None, listens for all classes.
            event_types: List of event types to listen for (e.g., ["zone_enter", "line_cross"]).
                        If None, listens for all event types.
            verbose: If True, prints detailed info. If False, prints compact format.
        """
        self.class_filter = class_filter
        self.event_types = event_types
        self.verbose = verbose
        self.event_count = 0

    def handle_event(self, event: Event):
        """Handle incoming detection event."""
        # Filter by class
        if self.class_filter and event.class_name not in self.class_filter:
            return

        # Filter by event type
        if self.event_types and event.event_type not in self.event_types:
            return

        self.event_count += 1
        time_str = time.strftime('%H:%M:%S', time.localtime(event.timestamp))

        if self.verbose:
            self._print_verbose(event, time_str)
        else:
            self._print_compact(event, time_str)

    def _print_verbose(self, event: Event, time_str: str):
        """Print detailed event information."""
        direction_str = f" -> {event.direction.upper()}" if event.direction else ""
        print(f"\n{'='*50}")
        print(f"[{time_str}] DETECTION EVENT #{self.event_count}")
        print(f"  Zone:       {event.zone_name}")
        print(f"  Event:      {event.event_type}{direction_str}")
        print(f"  Object:     {event.class_name} (ID: {event.tracker_id})")
        print(f"  Confidence: {event.confidence:.1%}")

        # Print speed info
        sm = event.speed_measurement
        if sm.is_valid:
            speed_kmh = sm.speed_ms * 3.6
            avg_kmh = sm.avg_speed_ms * 3.6
            distance = sm.track_distance_m
            duration = sm.track_duration_s
            error = sm.speed_error_pct
            print(f"  Speed:      {speed_kmh:.1f} km/h (avg: {avg_kmh:.1f} km/h)")
            print(f"  Track:      {distance:.1f}m in {duration:.1f}s")
            print(f"  Error:      ±{error:.0f}%")
        else:
            print(f"  Speed:      N/A ({sm.comment})")

        if event.noise_level is not None:
            print(f"  Noise:      {event.noise_level.db_a:.1f} dB(A)")

        print(f"{'='*50}")

    def _print_compact(self, event: Event, time_str: str):
        """Print compact one-line event."""
        direction_str = f"({event.direction})" if event.direction else ""
        sm = event.speed_measurement
        if sm.is_valid:
            speed_kmh = sm.speed_ms * 3.6
            error = sm.speed_error_pct
            speed_str = f" | {speed_kmh:.0f}km/h ±{error:.0f}%"
        else:
            speed_str = f" | {sm.comment}"
        noise_str = f" | {event.noise_level.db_a:.0f}dB(A)" if event.noise_level is not None else ""
        print(f"[{time_str}] {event.class_name} #{event.tracker_id} | "
              f"{event.event_type} {direction_str} @ {event.zone_name}{speed_str}{noise_str}")
