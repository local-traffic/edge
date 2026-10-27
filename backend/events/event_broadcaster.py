"""
EventBroadcaster - SSE event listener for broadcasting detection events to web clients.
"""

import json
import threading
import time
from collections import deque
from dataclasses import asdict
from queue import Queue, Empty
from typing import Generator

from .event_manager import Event


class EventBroadcaster:
    """
    Event listener that broadcasts events to connected SSE clients.

    Maintains a buffer of recent events and pushes new events to all
    connected clients via Server-Sent Events.
    """

    def __init__(self, max_history: int = 50):
        """
        Args:
            max_history: Maximum number of recent events to keep in buffer
        """
        self.max_history = max_history
        self.recent_events = deque(maxlen=max_history)
        self.clients: list[Queue] = []
        self.lock = threading.Lock()

    def handle_event(self, event: Event):
        """Handle incoming detection event - broadcast to all clients."""
        event_dict = self._event_to_dict(event)

        with self.lock:
            self.recent_events.appendleft(event_dict)

            dead_clients = []
            for client_queue in self.clients:
                try:
                    client_queue.put_nowait(event_dict)
                except:
                    dead_clients.append(client_queue)

            for dead in dead_clients:
                self.clients.remove(dead)

    def get_recent_events(self, limit: int = None) -> list[dict]:
        """Get recent events from buffer."""
        with self.lock:
            events = list(self.recent_events)
        if limit:
            return events[:limit]
        return events

    def subscribe(self) -> Queue:
        """Subscribe a new SSE client, returns queue for receiving events."""
        client_queue = Queue(maxsize=100)
        with self.lock:
            self.clients.append(client_queue)
        return client_queue

    def unsubscribe(self, client_queue: Queue):
        """Unsubscribe an SSE client."""
        with self.lock:
            if client_queue in self.clients:
                self.clients.remove(client_queue)

    def generate_sse_stream(self, client_queue: Queue) -> Generator[str, None, None]:
        """Generate SSE stream for a client."""
        try:
            while True:
                try:
                    event_dict = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(event_dict)}\n\n"
                except Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            self.unsubscribe(client_queue)

    def _event_to_dict(self, event: Event) -> dict:
        """Convert Event dataclass to JSON-serializable dict."""
        event_dict = {
            "timestamp": event.timestamp,
            "time_str": time.strftime('%H:%M:%S', time.localtime(event.timestamp)),
            "zone_name": event.zone_name,
            "event_type": event.event_type,
            "tracker_id": event.tracker_id,
            "class_id": event.class_id,
            "class_name": event.class_name,
            "confidence": event.confidence,
            "direction": event.direction,
        }

        sm = event.speed_measurement
        event_dict["speed"] = {
            "is_valid": sm.is_valid,
            "comment": sm.comment,
            "speed_kmh": round(sm.speed_ms * 3.6, 1) if sm.speed_ms else 0,
            "avg_speed_kmh": round(sm.avg_speed_ms * 3.6, 1) if sm.avg_speed_ms else 0,
            "max_speed_kmh": round(sm.max_speed_ms * 3.6, 1) if sm.max_speed_ms else 0,
            "min_speed_kmh": round(sm.min_speed_ms * 3.6, 1) if sm.min_speed_ms else 0,
            "distance_m": round(sm.track_distance_m, 1),
            "duration_s": round(sm.track_duration_s, 1),
            "error_pct": round(sm.speed_error_pct, 0),
        }

        event_dict["noise"] = {
            "db_a": round(event.noise_level.db_a, 1),
            "db_linear": round(event.noise_level.db_linear, 1),
            "peak": round(event.noise_level.peak, 4),
        }

        return event_dict
