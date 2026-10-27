import time
from dataclasses import dataclass, field
from typing import Optional

from ..decibel_meter import SoundLevel, ThreadedDecibelMeter


@dataclass
class SpeedMeasurement:
    """Speed measurement data for tracked objects."""
    is_valid: bool = False
    comment: str = ""
    speed_ms: float = 0.0
    avg_speed_ms: float = 0.0
    max_speed_ms: float = 0.0
    min_speed_ms: float = 0.0
    track_distance_m: float = 0.0
    track_duration_s: float = 0.0
    speed_error_pct: float = 0.0


@dataclass
class Event:
    timestamp: float
    zone_name: str
    event_type: str  # "line_cross", "zone_enter", "zone_exit"
    tracker_id: int
    class_id: int
    class_name: str
    confidence: float
    direction: Optional[str] = None  # "in" or "out" for line crossings
    speed_measurement: SpeedMeasurement = field(default_factory=SpeedMeasurement)
    noise_level: SoundLevel = field(default_factory=SoundLevel)


class EventManager:
    def __init__(self, noise_meter_thread: ThreadedDecibelMeter):
        self.events = []
        self.listeners = []
        self.pending_events = {}  # tracker_id -> Event (waiting for track completion)
        self._noise_meter_thread = noise_meter_thread

    def add_listener(self, listener):
        """Register a listener object that has a handle_event(event) method."""
        self.listeners.append(listener)

    def queue_event(self, event: Event):
        """Queue an event for later dispatch when track completes."""
        self.pending_events[event.tracker_id] = event
        time_str = time.strftime('%H:%M:%S', time.localtime(event.timestamp))
        direction_str = f" ({event.direction})" if event.direction else ""
        print(f"[{time_str}] Queued: {event.event_type} in '{event.zone_name}' | "
              f"ID: {event.tracker_id} ({event.class_name}){direction_str}")

    def finalize_event(self, tracker_id: int, final_speed: SpeedMeasurement):
        """Dispatch pending event with final speed measurement."""
        if tracker_id not in self.pending_events:
            return
        event = self.pending_events.pop(tracker_id)
        event.speed_measurement = final_speed
        self.dispatch(event)

    def dispatch(self, event: Event):
        """
        Dispatch an event to listeners.
        """

        readings = self._noise_meter_thread.get_last_n_readings(1)
        if readings:
            event.noise_level = readings[0]

        self.events.append(event)
        
        # Format for display (Console Logging)
        time_str = time.strftime('%H:%M:%S', time.localtime(event.timestamp))
        direction_str = f" ({event.direction})" if event.direction else ""
        
        print(f"[{time_str}] Event: {event.event_type} in '{event.zone_name}' | "
              f"ID: {event.tracker_id} ({event.class_name}){direction_str}")
        
        # Notify listeners
        for listener in self.listeners:
            try:
                listener.handle_event(event)
            except Exception as e:
                print(f"Error in event listener {type(listener).__name__}: {e}")
