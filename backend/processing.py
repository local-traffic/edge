"""
Shared processing logic for traffic detection.
Used by main.py for all platforms (PC and RPi).
"""

import os
import time
import cv2
import numpy as np
import supervision as sv
from dataclasses import dataclass, fields
from typing import Optional
from dotenv import load_dotenv

from .video_source import BaseVideoSource
from .detectors import new_detector
from .stationary_utils import MovingObjectDetector
from .video_utils import VideoRingBuffer, EventVideoWriter
from .coco_classes import COCO_CLASSES
from .events.event_manager import EventManager, SpeedMeasurement
from .zone_manager import ZoneManager
from .events.db_handler import PostgresHandler, SQLiteHandler
from .events.console_listener import ConsoleEventListener
from .web_streamer import WebStreamer
from .events.event_broadcaster import EventBroadcaster
from .tracker_utils import BoxmotTrackerWrapper, SupervisionTrackerWrapper
from .track_manager import TrackManager
from .speed_calculator import SpeedCalculator
from .decibel_meter import DecibelMeter, DummyDecibelMeter, ThreadedDecibelMeter
from .app_config import load_yaml_config


class Timer:
    def __init__(self, name="Block"):
        self.name = name

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.elapsed_ms = (self.end - self.start)*1000

@dataclass
class FrameTimingMetrics:
    """Performance metrics for a single frame."""
    # Individual component times (in milliseconds)
    inference_ms: float = 0.0
    tracking_ms: float = 0.0
    motion_detection_ms: float = 0.0
    zones_ms: float = 0.0
    annotation_ms: float = 0.0

    # Aggregate times
    total_pipeline_ms: float = 0.0
    fps: float = 0.0

    # Timestamp
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "inference_ms": round(self.inference_ms, 2),
            "tracking_ms": round(self.tracking_ms, 2),
            "motion_detection_ms": round(self.motion_detection_ms, 2),
            "zones_ms": round(self.zones_ms, 2),
            "annotation_ms": round(self.annotation_ms, 2),
            "total_pipeline_ms": round(self.total_pipeline_ms, 2),
            "fps": round(self.fps, 2),
            "timestamp": self.timestamp
        }


@dataclass
class ProcessingConfig:
    """Base configuration for the processing pipeline."""
    # Model
    model_type: str = "yolo"
    model_path: str = "yolov8s.pt"
    conf_thresh: float = 0.3
    ncnn_vulkan: bool = False

    # Tracker
    tracker_type: str = "bytetrack"
    track_thresh: float = 0.25
    track_buffer: int = 30
    match_thresh: float = 0.9

    # Recording
    record_events: bool = False
    buffer_size: float = 3.0
    post_event: float = 5.0
    max_recording_time: float = 20.0

    # Visualization
    tail_length: int = 100

    # Web streaming
    web_stream: bool = True
    web_port: int = 9090

    # Zones
    zone_config: Optional[str] = None

    # Misc
    loop: bool = False
    fps_limit: float = 0.0

    # Audio noise meter
    audio_device_index: Optional[int] = None

    # Motion detection thresholds
    movement_displacement_threshold: float = 40.0  # pixels

    # History lengths for motion detection
    moving_history_length: int = 30  # frames (visualization)
    recording_history_length: int = 90  # frames (recording trigger)
    track_history_length: int = 100  # max historical tracks

    @classmethod
    def from_args(cls, args) -> "ProcessingConfig":
        """Create config from argparse namespace, using class defaults."""
        config_fields = {f.name for f in fields(cls)}
        # Map args to config, handling name differences
        arg_mapping = {
            "audio_device": ("audio_device_index", lambda x: x),
        }

        kwargs = {}
        for key, value in vars(args).items():
            if key in arg_mapping:
                mapped_key, transform = arg_mapping[key]
                if mapped_key in config_fields:
                    kwargs[mapped_key] = transform(value)
            elif key in config_fields and value is not None:
                kwargs[key] = value

        return cls(**kwargs)


@dataclass
class PCConfig(ProcessingConfig):
    """PC-optimized configuration (receiving stream)."""
    pass


@dataclass
class RPiConfig(ProcessingConfig):
    """Raspberry Pi-optimized configuration (direct camera)."""
    pass


def add_common_args(parser, defaults: ProcessingConfig):
    """Add common arguments shared between PC and RPi apps."""
    
    # Model config
    parser.add_argument(
        "--model_type", type=str, default=defaults.model_type,
        choices=["yolo", "rfdetr", "hailo", "ncnn", "motion"], help="Model type"
    )
    parser.add_argument(
        "--model_path", type=str, default=defaults.model_path,
        help="Path to model weights"
    )
    parser.add_argument(
        "--conf_thresh", type=float, default=defaults.conf_thresh,
        help="Detection confidence threshold"
    )
    parser.add_argument(
        "--ncnn_vulkan", action="store_true",
        help="Enable Vulkan acceleration for NCNN (defaults to CPU)"
    )

    # Tracker config
    parser.add_argument(
        "--tracker", type=str, default=defaults.tracker_type,
        choices=["bytetrack", "ocsort"],
        help="Tracker type (bytetrack, ocsort)"
    )
    parser.add_argument(
        "--tracker_thresh", type=float, default=defaults.track_thresh,
        help="Tracker activation threshold"
    )
    parser.add_argument(
        "--track_buffer", type=int, default=defaults.track_buffer,
        help="Frames to keep lost tracks"
    )
    parser.add_argument(
        "--match_thresh", type=float, default=defaults.match_thresh,
        help="Tracker matching threshold"
    )

    # Recording config
    parser.add_argument(
        "--record_events", action="store_true",
        help="Enable event-based recording"
    )
    parser.add_argument(
        "--buffer_size", type=float, default=defaults.buffer_size,
        help="Pre-event buffer in seconds"
    )
    parser.add_argument(
        "--post_event", type=float, default=defaults.post_event,
        help="Post-event recording in seconds"
    )
    parser.add_argument(
        "--max_recording_time", type=float, default=defaults.max_recording_time,
        help="Maximum recording time in seconds"
    )

    # Visualization config
    parser.add_argument(
        "--tail_length", type=int, default=defaults.tail_length,
        help="Length of movement tails (N frames)"
    )

    parser.add_argument(
        "--zone_config", type=str, default=defaults.zone_config,
        help="Path to zone configuration YAML file"
    )

    # Web streaming config
    parser.add_argument(
        "--web_stream", action="store_true",
        help="Enable web streaming server for viewing in browser"
    )
    parser.add_argument(
        "--web_port", type=int, default=defaults.web_port,
        help="Port for web streaming server"
    )

    # Audio noise meter
    parser.add_argument(
        "--audio_device", type=int, default=None,
        help="Audio input device index for noise measurement (disabled if not set)"
    )

    # Misc config
    parser.add_argument(
        "--fps_limit", type=float, default=defaults.fps_limit,
        help="Limit replay FPS (0 for no limit)"
    )

    return parser


def setup_pipeline(config: ProcessingConfig, video_source: BaseVideoSource):
    """
    Setup the processing pipeline components.

    Returns dict with all initialized components.
    """
    # Load model
    detector = new_detector(
        config.model_type,
        config.model_path,
        use_vulkan=config.ncnn_vulkan
    )

    # Setup tracker
    fps = video_source.get_fps()
    print(f"Video Source FPS: {fps}")

    tracker = new_tracker(config, fps)

    track_manager = TrackManager(history_length=1000)

    load_dotenv()

    config_path = config.zone_config or os.getenv("ZONE_CONFIG") or "zones.yaml"
    config_data = load_yaml_config(config_path)

    # Apply saved settings where CLI didn't override
    noise_settings = config_data.get('noise_measurement', {})
    saved_device = noise_settings.get('device_index')
    if config.audio_device_index is None:
        config.audio_device_index = saved_device if saved_device is not None else 0

    detection_settings = config_data.get('detection_settings', {})
    saved_threshold = detection_settings.get('conf_threshold')
    if saved_threshold is not None:
        config.conf_thresh = saved_threshold

    if config.audio_device_index == -1:
        meter = DummyDecibelMeter()
    else:
        try:
            meter = DecibelMeter(device_index=config.audio_device_index)
        except (ValueError, OSError) as e:
            meter = DummyDecibelMeter()
    noise_meter = ThreadedDecibelMeter(meter)
    noise_meter.start()
    event_manager = EventManager(noise_meter_thread=noise_meter)

    console_listener = ConsoleEventListener(
        class_filter=None,
        event_types=None,
        verbose=True
    )
    event_manager.add_listener(console_listener)
    print("Attached Console Event Listener")

    event_broadcaster = EventBroadcaster(max_history=50)
    event_manager.add_listener(event_broadcaster)
    print("Attached Event Broadcaster for SSE")

    db_handler = None
    sqlite_handler = None

    try:
        sqlite_handler = SQLiteHandler()
        event_manager.add_listener(sqlite_handler)
        print("Attached SQLite Handler")
    except Exception as e:
        print(f"Failed to attach SQLite Handler: {e}")

    db_conn = os.getenv("POSTGRES_CONNECTION_STRING")
    if db_conn:
        try:
            db_handler = PostgresHandler(db_conn)
            event_manager.add_listener(db_handler)
            print("Attached PostgreSQL Handler")
        except Exception as e:
            print(f"Failed to attach DB Handler: {e}")
    else:
        print("No POSTGRES_CONNECTION_STRING found. Statistics will not be saved to remote DB.")

    zone_manager = ZoneManager(event_manager, track_manager, config_data, config_path, video_source=video_source)

    # Initialize speed calculator if perspective calibration available
    if zone_manager.get_perspective_transform():
        track_manager.speed_calculator = SpeedCalculator(zone_manager.transform_point_to_world)

    # Recording components
    ring_buffer = VideoRingBuffer(buffer_duration=config.buffer_size)
    
    return {
        "detector": detector,
        "tracker": tracker,
        "track_manager": track_manager,
        "event_manager": event_manager,
        "event_broadcaster": event_broadcaster,
        "db_handler": db_handler,
        "sqlite_handler": sqlite_handler,
        "zone_manager": zone_manager,
        "ring_buffer": ring_buffer,
        "fps": fps,
    }

def new_tracker(config, fps):
    if config.tracker_type == "bytetrack":
        sv_tracker = sv.ByteTrack(
            track_activation_threshold=config.track_thresh,
            lost_track_buffer=config.track_buffer,
            minimum_matching_threshold=config.match_thresh,
            frame_rate=fps
        )
        tracker = SupervisionTrackerWrapper(sv_tracker)
    elif config.tracker_type == "ocsort":
        tracker = BoxmotTrackerWrapper(
            tracker_type="ocsort",
            track_buffer=config.track_buffer,
            match_thresh=config.match_thresh,
            frame_rate=fps
        )
    else:
        raise ValueError(f"Unknown tracker type: {config.tracker_type}")
    return tracker


def process_frame(
    frame: np.ndarray,
    config: ProcessingConfig,
    pipeline: dict,
    trace_annotator: sv.TraceAnnotator,
    box_annotator: sv.BoxAnnotator,
    label_annotator: sv.LabelAnnotator,
    trigger_classes: list,
    moving_detector: MovingObjectDetector,
    recording_moving_detector: MovingObjectDetector,
    video_writer: EventVideoWriter
) -> tuple[Optional[np.ndarray], Optional[FrameTimingMetrics]]:
    """
    Process a single frame through the detection pipeline.

    Returns:
        tuple: (annotated_frame, timing_metrics)
            - annotated_frame: Annotated frame or None if display disabled
            - timing_metrics: Performance metrics or None if not collecting
    """
    detector = pipeline["detector"]
    tracker = pipeline["tracker"]
    track_manager = pipeline["track_manager"]
    zone_manager = pipeline["zone_manager"]
    ring_buffer = pipeline["ring_buffer"]
    

    # Initialize timing (only collect if web_streamer enabled)
    collect_metrics = True
    if collect_metrics:
        metrics = FrameTimingMetrics()
        pipeline_start = time.perf_counter()

    ring_buffer.add_frame(frame.copy())


    with Timer("Inference") as t:
        if config.model_type == "rfdetr":
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            detections = detector.predict(image_rgb, conf_threshold=config.conf_thresh)
        else:
            detections = detector.predict(frame, conf_threshold=config.conf_thresh)

    metrics.inference_ms = t.elapsed_ms

    # TIMING POINT 2: Tracking
    if collect_metrics:
        t0 = time.perf_counter()

    # Pass frame to tracker wrapper (handled appropriately by wrapper)
    tracked_detections = tracker.update_with_detections(detections, frame=frame)

    if collect_metrics:
        metrics.tracking_ms = (time.perf_counter() - t0) * 1000

    # TIMING POINT 3: Motion Detection
    if collect_metrics:
        t0 = time.perf_counter()

    moving_detector.update(tracked_detections)
    recording_moving_detector.update(tracked_detections)


    if collect_metrics:
        metrics.motion_detection_ms = (time.perf_counter() - t0) * 1000

    # TIMING POINT 4: Zones
    if collect_metrics:
        t0 = time.perf_counter()

    zone_manager.update(tracked_detections, original_frame=frame)

    if collect_metrics:
        metrics.zones_ms = (time.perf_counter() - t0) * 1000

    # Determine moving objects for visualization
    moving_mask = []
    for completer_track_id in tracked_detections.tracker_id:
        is_moving = moving_detector.is_moving(completer_track_id, min_displacement=config.movement_displacement_threshold)
        moving_mask.append(is_moving)

    moving_mask = np.array(moving_mask, dtype=bool)

    if len(moving_mask) == len(tracked_detections):
        moving_detections = tracked_detections[moving_mask]
    else:
        moving_detections = sv.Detections.empty()

    completed_track_ids = track_manager.update(moving_detections)

    # Finalize pending events for completed tracks (with final speed measurement)
    frame_height, frame_width = frame.shape[:2]
    event_manager = pipeline["event_manager"]

    for completer_track_id in completed_track_ids:
        track = track_manager.get_completed_track(completer_track_id)

        if track_manager.speed_calculator:
            final_speed = track_manager.speed_calculator.calculate(
                track['points'], frame_width, frame_height
            )
        else:
            final_speed = SpeedMeasurement(is_valid=False, comment='no perspective calibration')
        event_manager.finalize_event(completer_track_id, final_speed)
    

    #event means the object was moving and produced an event on the zone, maybe there were more objects, doesnt matter stare it all
    if config.record_events and len(completed_track_ids)>0:
        video_writer.save_video(ring_buffer.get_all(), "event")


    # Create labels for moving detections
    moving_labels = []
    for class_id, confidence, completer_track_id in zip(
        moving_detections.class_id,
        moving_detections.confidence,
        moving_detections.tracker_id
    ):
        class_name = COCO_CLASSES.get(class_id, "unknown")
        label = f"#{completer_track_id} {class_name} {confidence:.2f}"

        # Add speed if available
        if track_manager.speed_calculator:
            track = track_manager.get_track_with_speed(
                int(completer_track_id), frame_width, frame_height
            )
            if track and 'speed' in track and track['speed'].is_valid:
                speed_kmh = track['speed'].speed_ms * 3.6
                label += f" {speed_kmh:.0f}km/h"

        moving_labels.append(label)

    # TIMING POINT 5: Annotation
    if collect_metrics:
        t0 = time.perf_counter()

    # Annotate frame
    annotated_frame = frame.copy()

    if zone_manager:
        annotated_frame = zone_manager.annotate(annotated_frame)

    annotated_frame = box_annotator.annotate(
        scene=annotated_frame,
        detections=moving_detections
    )
    annotated_frame = label_annotator.annotate(
        scene=annotated_frame,
        detections=moving_detections,
        labels=moving_labels
    )
    annotated_frame = trace_annotator.annotate(
        scene=annotated_frame,
        detections=moving_detections
    )


    if collect_metrics:
        metrics.annotation_ms = (time.perf_counter() - t0) * 1000
        metrics.total_pipeline_ms = (time.perf_counter() - pipeline_start) * 1000
        metrics.fps = 1000.0 / metrics.total_pipeline_ms if metrics.total_pipeline_ms > 0 else 0.0
        metrics.timestamp = time.time()

    return annotated_frame, (metrics if collect_metrics else None)


def run_processing_loop(
    video_source: BaseVideoSource,
    config: ProcessingConfig
) -> None:
    """
    Main processing loop.

    Args:
        video_source: Initialized video source
        config: Processing configuration
    """
    if not video_source.is_opened():
        print("Error: Video source is not open")
        return

    pipeline = setup_pipeline(config, video_source)

    # Motion detectors
    # Two separate instances: one for visualization (short history), one for recording trigger (longer history)
    moving_detector = MovingObjectDetector(history_length=config.moving_history_length)
    recording_moving_detector = MovingObjectDetector(history_length=config.recording_history_length)

    # Instantiate annotators locally (not part of pipeline singleton)
    trace_annotator = sv.TraceAnnotator(trace_length=config.tail_length)
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    video_writer = EventVideoWriter(max_duration=config.max_recording_time)


    # Trigger classes based on model type
    if config.model_type == "rfdetr":
        trigger_classes = [1, 2, 3, 8]  # 1-based COCO
    else:
        trigger_classes = [0, 1, 2, 7]  # 0-based COCO

    if config.web_stream:
        # Pass detector and snapshot directory for detector test API
        import os
        snapshot_dir = os.path.join(os.path.dirname(__file__),'..' ,'snapshots')
        web_streamer = WebStreamer(
            zone_manager=pipeline["zone_manager"],
            track_manager=pipeline["track_manager"],
            config=config,
            port=config.web_port,
            detector=pipeline["detector"],
            snapshot_dir=snapshot_dir if os.path.isdir(snapshot_dir) else None,
            stats_handler=pipeline["sqlite_handler"],
            event_broadcaster=pipeline["event_broadcaster"],
            ring_buffer=pipeline["ring_buffer"]
        )
        web_streamer.start()

    print("Starting processing loop... Press 'q' to quit.")

    target_frame_time = 1.0 / config.fps_limit if config.fps_limit > 0 else 0

    try:
        while True:
            loop_start_time = time.perf_counter()
            ret, frame = video_source.read()
            if not ret:
                if config.loop:
                    print("Looping video...")
                    if not video_source.reopen():
                        print("Error: Could not re-open video source for looping.")
                        break
                    continue
                else:
                    print("Stream ended.")
                    break

            try:
                annotated_frame, metrics = process_frame(
                    frame, config, pipeline, trace_annotator,
                    box_annotator, label_annotator, trigger_classes,
                    moving_detector, recording_moving_detector,
                    video_writer
                )

                if config.web_stream:
                    web_streamer.update_frame(annotated_frame)
                    web_streamer.update_metrics(metrics)


            except Exception as e:
                print(f"Error processing frame: {e}")
                import traceback
                traceback.print_exc()

            elapsed = time.perf_counter() - loop_start_time
            if target_frame_time > 0 and elapsed < target_frame_time:
                time.sleep(target_frame_time - elapsed)

    finally:
        # Cleanup
        if pipeline.get("noise_meter"):
            try:
                pipeline["noise_meter"].stop()
            except Exception:
                pass
        if pipeline.get("db_handler"):
            pipeline["db_handler"].stop()
        if pipeline.get("sqlite_handler"):
            pipeline["sqlite_handler"].stop()
        if pipeline.get("web_streamer"):
            pipeline["web_streamer"].stop()
        video_writer.stop()
        video_source.release()
