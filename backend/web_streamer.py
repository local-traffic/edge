"""
Web streaming server for annotated video frames.
Provides MJPEG streaming over HTTP for viewing detection results in a browser.
"""

import logging
import os
import glob
import threading
import time
import urllib.parse
from collections import deque
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import supervision as sv
import yaml
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from dataclasses import asdict
from .coco_classes import COCO_CLASSES
from werkzeug.serving import make_server

from .decibel_meter import AudioDeviceInfo, DecibelMeter, DummyDecibelMeter, list_input_devices

logger = logging.getLogger(__name__)


def parse_stats_params():
    """Parse common query parameters shared by all stats endpoints."""
    hours = request.args.get('duration', default=24, type=int)
    bin_size = request.args.get('bin_size', default=5, type=int)
    bucket_mins = request.args.get('bucket', default=60, type=int)
    merge_directions = request.args.get('merge_directions', default='false', type=str).lower() == 'true'
    group_vehicles = request.args.get('group_vehicles', default='false', type=str).lower() == 'true'
    return hours, bin_size, bucket_mins, merge_directions, group_vehicles




class MetricsTracker:
    """Thread-safe rolling average metrics tracker."""

    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.metrics_history = deque(maxlen=window_size)
        self.lock = threading.Lock()
        self.last_update = time.time()

    def update(self, metrics: dict):
        with self.lock:
            self.metrics_history.append(metrics)
            self.last_update = time.time()

    def get_averaged(self) -> Optional[dict]:
        with self.lock:
            if not self.metrics_history:
                return None

            avg = {}
            keys = self.metrics_history[0].keys()
            for key in keys:
                if key != "timestamp":
                    values = [m[key] for m in self.metrics_history]
                    avg[key] = sum(values) / len(values)

            avg["timestamp"] = self.last_update
            avg["window_size"] = len(self.metrics_history)
            return avg


class WebStreamer:
    """
    MJPEG streaming server using Flask.

    Streams annotated frames to web browsers at specified port.
    Thread-safe frame updates allow integration with processing pipeline.
    """

    def __init__(
        self,
        zone_manager,
        track_manager,
        config,
        port: int = 9090,
        host: str = "0.0.0.0",
        detector=None,
        snapshot_dir=None,
        stats_handler=None,
        event_broadcaster=None,
        ring_buffer=None
    ):
        self.port = port
        self.host = host
        self.frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()
        self.metrics_tracker = MetricsTracker(window_size=30)
        self.zone_manager = zone_manager
        self.track_manager = track_manager
        self.config = config
        self.detector = detector
        self.snapshot_dir = snapshot_dir
        self.stats_handler = stats_handler
        self.event_broadcaster = event_broadcaster
        self.ring_buffer = ring_buffer
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        self._app = None
        self._server = None
        self._clip_output_dir = "recordings"
        os.makedirs(self._clip_output_dir, exist_ok=True)

        self._snapshot_yamls = []
        self._detector_conf_threshold = 0.3

        if self.snapshot_dir:
            self._load_snapshot_yamls()

    def update_frame(self, frame: np.ndarray):
        """Update the current frame to be streamed. Thread-safe."""
        with self.frame_lock:
            self.frame = frame.copy()

    def update_metrics(self, metrics):
        if metrics:
            self.metrics_tracker.update(metrics.to_dict())

    def _load_snapshot_yamls(self):
        pattern = os.path.join(self.snapshot_dir, '**', '*.yaml')
        yaml_paths = list(glob.glob(pattern, recursive=True))
        self._snapshot_yamls = sorted(list(set(yaml_paths)))

    def _parse_zone_from_directory(self, dir_name: str) -> str:
        """Format: YYYYMMDD-{zone_name_url_encoded}"""
        if '-' in dir_name:
            _, zone_encoded = dir_name.split('-', 1)
            return urllib.parse.unquote(zone_encoded)
        return "unknown"

    def _parse_filename_attrs(self, filename_base: str) -> tuple:
        """Parse filename to extract id and key=value attributes.
        Format: {id},key=value,key=value
        """
        parts = filename_base.split(',')
        file_id = parts[0] if parts else ""

        attrs = {}
        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                attrs[key] = value

        return file_id, attrs

    def _get_image(self, index):
        return self._get_img_suffix(index, "")

    def _get_thumbnail(self, index):
        return self._get_img_suffix(index, "_thumb")

    def _get_img_suffix(self, index, suffix):
        if index >= len(self._snapshot_yamls):
            return None

        yaml_path = Path(self._snapshot_yamls[index])
        filename = yaml_path.parent / (yaml_path.stem + suffix + '.jpg')
        return cv2.imread(str(filename))

    def _generate_frames(self):
        """Generator that yields MJPEG frames."""
        while self.running:
            with self.frame_lock:
                if self.frame is None:
                    blank = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(
                        blank, "Waiting for frames...", (150, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
                    )
                    frame = blank
                else:
                    frame = self.frame.copy()

            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
            )

            time.sleep(0.033)  # ~30 fps max

    def _requires(self, *attrs):
        """Decorator that returns 503 if any required dependency is None."""
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                for attr in attrs:
                    if getattr(self, attr) is None:
                        return jsonify({"error": f"{attr} not available"}), 503
                return f(*args, **kwargs)
            return wrapper
        return decorator

    # ── Route registration ────────────────────────────────────────────

    def _register_stream_routes(self, app):
        @app.route('/video_feed')
        def video_feed():
            return Response(
                self._generate_frames(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )

        @app.route('/metrics')
        def metrics():
            avg_metrics = self.metrics_tracker.get_averaged()
            if avg_metrics:
                return jsonify(avg_metrics)
            return jsonify({"error": "No metrics available"}), 503

    def _register_stats_routes(self, app):
        @app.route('/api/stats', methods=['GET'])
        @self._requires('stats_handler')
        def get_stats():
            hours, _, bucket_mins, merge_directions, group_vehicles = parse_stats_params()
            stats = self.stats_handler.get_stats(
                duration_seconds=hours * 3600,
                bucket_size=bucket_mins * 60,
                merge_directions=merge_directions,
                group_vehicles=group_vehicles
            )
            return jsonify({"stats": stats})

        @app.route('/api/stats/speeds', methods=['GET'])
        @self._requires('stats_handler')
        def get_speed_histogram():
            hours, bin_size, _, merge_directions, group_vehicles = parse_stats_params()
            histogram = self.stats_handler.get_speed_histogram(
                duration_seconds=hours * 3600,
                bin_size_kmh=bin_size,
                merge_directions=merge_directions,
                group_vehicles=group_vehicles
            )
            return jsonify({"histogram": histogram, "unit": "km/h"})

        @app.route('/api/stats/noise', methods=['GET'])
        @self._requires('stats_handler')
        def get_noise_histogram():
            hours, bin_size, _, merge_directions, group_vehicles = parse_stats_params()
            histogram = self.stats_handler.get_noise_histogram(
                duration_seconds=hours * 3600,
                bin_size_db=bin_size,
                merge_directions=merge_directions,
                group_vehicles=group_vehicles
            )
            return jsonify({"histogram": histogram, "unit": "dB(A)"})

    def _register_track_routes(self, app):
        @app.route('/api/tracks', methods=['GET'])
        def get_tracks():
            min_distance = request.args.get('min_distance', default=0, type=float)
            max_history = request.args.get('max_history', default=0, type=int)
            tracks = self.track_manager.get_tracks(min_distance=min_distance, max_history=max_history)
            return jsonify({
                "tracks": tracks,
                "history_length": self.track_manager.history_length,
            })

        @app.route('/api/tracks/settings', methods=['POST'])
        def update_track_settings():
            data = request.get_json()
            if not data or 'history_length' not in data:
                return jsonify({"error": "Missing history_length"}), 400

            try:
                length = int(data['history_length'])
                if length < 1:
                    return jsonify({"error": "History length must be positive"}), 400

                self.track_manager.set_history_length(length)
                return jsonify({
                    "success": True,
                    "history_length": self.track_manager.history_length
                })
            except ValueError:
                return jsonify({"error": "Invalid history_length"}), 400

    def _register_zone_routes(self, app):
        @app.route('/api/zones', methods=['GET'])
        def get_zones():
            zones = self.zone_manager.get_zones_config()
            return jsonify({"zones": zones})

        @app.route('/api/zones', methods=['POST'])
        def create_zone():
            zone_config = request.get_json()
            if not zone_config:
                return jsonify({"error": "Invalid zone configuration"}), 400

            required = ['name', 'type', 'geometry']
            if not all(field in zone_config for field in required):
                return jsonify({"error": f"Missing required fields: {required}"}), 400

            existing = [z for z in self.zone_manager.zones if z.name == zone_config['name']]
            if existing:
                return jsonify({"error": "Zone with this name already exists"}), 409

            self.zone_manager.add_zone(zone_config, save=True)
            return jsonify({"success": True, "zone": zone_config}), 201

        @app.route('/api/zones/<name>', methods=['PUT'])
        def update_zone(name):
            zone_config = request.get_json()
            if not zone_config:
                return jsonify({"error": "Invalid zone configuration"}), 400

            existing = [z for z in self.zone_manager.zones if z.name == name]
            if not existing:
                return jsonify({"error": "Zone not found"}), 404

            self.zone_manager.update_zone(name, zone_config)
            return jsonify({"success": True, "zone": zone_config})

        @app.route('/api/zones/<name>', methods=['DELETE'])
        def delete_zone(name):
            existing = [z for z in self.zone_manager.zones if z.name == name]
            if not existing:
                return jsonify({"error": "Zone not found"}), 404

            self.zone_manager.delete_zone(name)
            return jsonify({"success": True, "message": f"Zone '{name}' deleted"})

    def _register_config_routes(self, app):
        @app.route('/api/threshold', methods=['GET'])
        def get_threshold():
            return jsonify({"threshold": self.config.conf_thresh})

        @app.route('/api/threshold', methods=['POST'])
        def set_threshold():
            data = request.get_json()
            if not data or 'threshold' not in data:
                return jsonify({"error": "Missing threshold value"}), 400

            threshold = float(data['threshold'])
            if not (0.0 <= threshold <= 1.0):
                return jsonify({"error": "Threshold must be between 0.0 and 1.0"}), 400

            self.config.conf_thresh = threshold
            self.zone_manager.update_detection_settings({'conf_threshold': threshold})
            return jsonify({"success": True, "threshold": threshold})

        @app.route('/api/config', methods=['GET'])
        def get_config():
            from dataclasses import asdict
            return jsonify(asdict(self.config))

        @app.route('/api/settings', methods=['POST'])
        def detector_update_settings():
            data = request.get_json()
            if data and 'threshold' in data:
                self._detector_conf_threshold = float(data['threshold'])
                return jsonify({"success": True})
            if data and 'conf_threshold' in data:
                self._detector_conf_threshold = float(data['conf_threshold'])
                return jsonify({"success": True})
            return jsonify({"error": "Missing threshold value"}), 400

    def _register_camera_routes(self, app):
        @app.route('/api/camera/settings', methods=['GET'])
        def get_camera_settings():
            settings = self.zone_manager.get_camera_settings()
            is_picamera = (self.zone_manager.video_source is not None and
                           hasattr(self.zone_manager.video_source, 'set_af_window'))
            return jsonify({
                "is_picamera": is_picamera,
                "settings": settings,
                "af_window": settings.get('af_window')
            })

        @app.route('/api/camera/settings', methods=['POST'])
        def update_camera_settings():
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid request"}), 400

            if not hasattr(self.zone_manager.video_source, 'set_af_window'):
                return jsonify({"error": "Camera controls not available for this video source"}), 400

            success = self.zone_manager.update_camera_settings(data)
            if success:
                return jsonify({"success": True, "settings": data})
            return jsonify({"error": "Failed to update camera settings"}), 500

        @app.route('/api/camera/reset', methods=['POST'])
        def reset_camera_autofocus():
            if not hasattr(self.zone_manager.video_source, 'reset_af_window'):
                return jsonify({"error": "Camera controls not available"}), 400

            success = self.zone_manager.video_source.reset_af_window()
            if success:
                self.zone_manager.camera_settings['af_window'] = None
                self.zone_manager.save_config()
                return jsonify({"success": True})
            return jsonify({"error": "Failed to reset autofocus"}), 500

    def _register_perspective_routes(self, app):
        @app.route('/api/perspective', methods=['GET'])
        def get_perspective():
            perspective = self.zone_manager.get_perspective_transform()
            return jsonify({
                "enabled": perspective is not None,
                "perspective": perspective
            })

        @app.route('/api/perspective', methods=['POST'])
        def save_perspective():
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid request"}), 400

            required = ['corners', 'edge_lengths']
            if not all(field in data for field in required):
                return jsonify({"error": f"Missing required fields: {required}"}), 400

            if len(data['corners']) != 4:
                return jsonify({"error": "Must provide exactly 4 corners"}), 400

            edge_lengths = data['edge_lengths']
            if not all(k in edge_lengths for k in ['top', 'left', 'bottom']):
                return jsonify({"error": "edge_lengths must have top, left, bottom"}), 400

            success = self.zone_manager.update_perspective_transform(data)
            if success:
                return jsonify({"success": True, "perspective": data})
            return jsonify({"error": "Failed to save perspective"}), 500

        @app.route('/api/perspective', methods=['DELETE'])
        def delete_perspective():
            self.zone_manager.delete_perspective_transform()
            return jsonify({"success": True})

    def _register_detection_routes(self, app):
        @app.route('/api/image/<int:index>', methods=['GET'])
        def get_detector_image(index):
            if index < 0 or index >= len(self._snapshot_yamls):
                return Response(b'Invalid index', status=400)

            image = self._get_image(index)
            if image is None:
                return Response(b'Failed to load image', status=500)

            annotate = request.args.get('annotate', 'true').lower() == 'true'
            threshold_param = request.args.get('threshold')
            conf_threshold = float(threshold_param) if threshold_param else self._detector_conf_threshold

            # Resize if too large
            max_height = 900
            max_width = 1600
            h, w = image.shape[:2]
            if h > max_height or w > max_width:
                scale = min(max_width / w, max_height / h)
                image = cv2.resize(image, (int(w * scale), int(h * scale)))

            if annotate and self.detector:
                detections = self.detector.predict(image, conf_threshold=conf_threshold)

                if len(detections) > 0 and detections.confidence is not None:
                    mask = detections.confidence >= conf_threshold
                    detections = detections[mask]

                labels = []
                if detections.class_id is not None:
                    for class_id, confidence in zip(detections.class_id, detections.confidence):
                        class_name = COCO_CLASSES.get(class_id, f"class_{class_id}")
                        labels.append(f"{class_name} {confidence:.2f}")

                box_annotator = sv.BoxAnnotator(thickness=2)
                label_annotator = sv.LabelAnnotator(text_thickness=1, text_scale=0.5)
                image = box_annotator.annotate(scene=image.copy(), detections=detections)
                image = label_annotator.annotate(scene=image, detections=detections, labels=labels)

                info_text = [
                    f"Image: {index + 1}/{len(self._snapshot_yamls)}",
                    f"File: {self._snapshot_yamls[index]}",
                    f"Detections: {len(detections)}",
                    f"Conf: {conf_threshold:.2f}"
                ]
                y_offset = 30
                for line in info_text:
                    cv2.putText(image, line, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                    y_offset += 25

            success, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not success:
                return Response(b'Failed to encode image', status=500)

            return Response(encoded.tobytes(), mimetype='image/jpeg')

        @app.route('/api/thumbnail/<int:index>', methods=['GET'])
        def get_thumbnail(index):
            if index < 0 or index >= len(self._snapshot_yamls):
                return Response(b'Invalid index', status=400)

            thumbnail = self._get_thumbnail(index)
            if thumbnail is None:
                return Response(b'Failed to create thumbnail', status=500)

            success, encoded = cv2.imencode('.jpg', thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not success:
                return Response(b'Failed to encode thumbnail', status=500)

            return Response(encoded.tobytes(), mimetype='image/jpeg')

        @app.route('/api/detections', methods=['GET'])
        def get_detections():
            self._load_snapshot_yamls()

            if not self._snapshot_yamls:
                return jsonify({"detections": [], "total": 0, "classes": [], "zones": [], "event_types": []})

            class_filter = request.args.get('class_name', default=None, type=str)
            zone_filter = request.args.get('zone_name', default=None, type=str)
            event_type_filter = request.args.get('event_type', default=None, type=str)
            limit = request.args.get('limit', default=50, type=int)
            offset = request.args.get('offset', default=0, type=int)

            detections = []
            all_classes = set()
            all_zones = set()
            all_event_types = set()

            for idx, yaml_path_str in enumerate(self._snapshot_yamls):
                yaml_path = Path(yaml_path_str)

                try:
                    dir_name = yaml_path.parent.name
                    zone_name = self._parse_zone_from_directory(dir_name)
                    all_zones.add(zone_name)

                    if zone_filter and zone_name != zone_filter:
                        continue

                    file_id, attrs = self._parse_filename_attrs(yaml_path.stem)
                    class_name = attrs.get('class', 'unknown')
                    event_type = attrs.get('event-type', 'unknown')

                    all_classes.add(class_name)
                    all_event_types.add(event_type)

                    if class_filter and class_name != class_filter:
                        continue
                    if event_type_filter and event_type != event_type_filter:
                        continue

                    detections.append({
                        'index': idx,
                        'id': file_id,
                        'dir': dir_name,
                        'zone_name': zone_name,
                        'class_name': class_name,
                        'event_type': event_type,
                        'attrs': attrs,
                    })

                except Exception as e:
                    logger.warning("Error parsing %s: %s", yaml_path, e)
                    continue

            total = len(detections)
            paginated = detections[offset:offset + limit]

            return jsonify({
                "detections": paginated,
                "total": total,
                "offset": offset,
                "limit": limit,
                "classes": sorted(list(all_classes)),
                "zones": sorted(list(all_zones)),
                "event_types": sorted(list(all_event_types)),
            })

        @app.route('/api/detections/metadata/<int:index>')
        def get_detection_metadata(index):
            self._load_snapshot_yamls()

            if index < 0 or index >= len(self._snapshot_yamls):
                return jsonify({"error": "Invalid index"}), 400

            yaml_path = self._snapshot_yamls[index]
            if not os.path.isfile(yaml_path):
                return jsonify({"error": "Detection not found"}), 404

            with open(yaml_path, 'r') as f:
                meta = yaml.safe_load(f)
            return jsonify(meta)

    def _register_clip_routes(self, app):
        @app.route('/api/clip/save', methods=['POST'])
        @self._requires('ring_buffer')
        def save_clip():
            frames = self.ring_buffer.get_all()
            if not frames:
                return jsonify({"error": "No frames in buffer"}), 400

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"clip_{timestamp}.avi"
            filepath = os.path.join(self._clip_output_dir, filename)

            h, w = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            fps = self.ring_buffer.fps

            writer = cv2.VideoWriter(filepath, fourcc, fps, (w, h))
            if not writer.isOpened():
                return jsonify({"error": "Failed to create video writer"}), 500

            for frame in frames:
                writer.write(frame)
            writer.release()

            duration = len(frames) / fps
            return jsonify({
                "success": True,
                "filename": filename,
                "frames": len(frames),
                "duration": round(duration, 1),
                "fps": fps
            })

    def _register_event_routes(self, app):
        @app.route('/api/events', methods=['GET'])
        @self._requires('event_broadcaster')
        def get_events():
            limit = request.args.get('limit', default=50, type=int)
            events = self.event_broadcaster.get_recent_events(limit=limit)
            return jsonify({"events": events})

        @app.route('/api/events/stream')
        @self._requires('event_broadcaster')
        def events_stream():
            client_queue = self.event_broadcaster.subscribe()

            def generate():
                try:
                    yield from self.event_broadcaster.generate_sse_stream(client_queue)
                finally:
                    self.event_broadcaster.unsubscribe(client_queue)

            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )

    def _register_noise_routes(self, app):
        @app.route('/api/noise/devices', methods=['GET'])
        def get_noise_devices():
            try:
                devices = list_input_devices()
            except Exception:
                devices = []

            dummy_device = AudioDeviceInfo(
                index=-1,
                name="Dummy - 0 dB(A)",
                channels=0,
                sample_rate=0,
                is_default=False
            )
            devices.append(dummy_device)
            return jsonify([asdict(d) for d in devices])

        @app.route('/api/noise/level', methods=['GET'])
        def get_noise_level():
            noise_meter = self.zone_manager.event_manager._noise_meter_thread
            n = request.args.get('n', default=50, type=int)
            readings = noise_meter.get_last_n_readings(n)
            return jsonify({
                "readings": [asdict(r) for r in readings],
                "device_index": self.config.audio_device_index
            })

        @app.route('/api/noise/device', methods=['POST'])
        def set_noise_device():
            data = request.get_json()
            if not data or 'device_index' not in data:
                return jsonify({"error": "Missing device_index"}), 400

            device_index = int(data['device_index'])
            print(f"set device index {device_index}")

            noise_meter = self.zone_manager.event_manager._noise_meter_thread
            if device_index == -1:
                new_meter = DummyDecibelMeter()
            else:
                try:
                    new_meter = DecibelMeter(device_index=device_index)
                except Exception as e:
                    return jsonify({"Error when opening new sound device": str(e)}), 400

            noise_meter.set_decibel_meter(new_meter)
            self.config.audio_device_index = device_index
            self.zone_manager.update_noise_measurement({'device_index': device_index})
            return jsonify({"success": True, "device_index": device_index})


    def _register_spa_routes(self, app):
        @app.route('/')
        def index():
            return send_from_directory(app.static_folder, 'index.html')

        @app.route('/<path:path>')
        def catch_all(path):
            try:
                return send_from_directory(app.static_folder, path)
            except Exception:
                if path.startswith('api/'):
                    return jsonify({"error": "Not found"}), 404
                return send_from_directory(app.static_folder, 'index.html')

    # ── App creation ──────────────────────────────────────────────────

    def _create_app(self):
        static_folder = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
        app = Flask(__name__, static_folder=static_folder)
        CORS(app)

        self._register_stream_routes(app)
        self._register_stats_routes(app)
        self._register_track_routes(app)
        self._register_zone_routes(app)
        self._register_config_routes(app)
        self._register_camera_routes(app)
        self._register_perspective_routes(app)
        self._register_detection_routes(app)
        self._register_clip_routes(app)
        self._register_event_routes(app)
        self._register_noise_routes(app)
        self._register_spa_routes(app)  # Must be last

        @app.errorhandler(Exception)
        def handle_error(e):
            return jsonify({"error": str(e)}), 500

        logging.getLogger('werkzeug').setLevel(logging.ERROR)

        return app

    def _run_server(self):
        self._app = self._create_app()
        self._server = make_server(self.host, self.port, self._app, threaded=True)
        self._server.serve_forever()

    def start(self):
        if self.running:
            return

        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        print(f"Web streamer started at http://{self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self._server:
            self._server.shutdown()
        if self.server_thread:
            self.server_thread.join(timeout=2)
        print("Web streamer stopped")
