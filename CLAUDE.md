# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real-time vehicle traffic detection system using YOLO/RF-DETR models with support for both PC (receiving video stream) and Raspberry Pi (direct camera capture). The system tracks vehicles, detects zone crossings, records events, and stores statistics in PostgreSQL and other backends.
Project has pyinfra deployment scripts


## 2. Naming Conventions (STRICT)
**Core Rule:** Variable and class names must be **domain-specific**, not structural. You are forbidden from using generic architectural nouns on their own.

### 🚫 Forbidden Names (Do NOT use these alone)
* `Manager`, `Handler`, `Helper`, `Service`, `Controller`
* `Data`, `Info`, `Item`, `Object`, `Value`, `Element`
* `Broadcaster`, `Listener`, `Observer`

### ✅ Required Naming Style
* **Structure + Domain:**
    * Bad: `Broadcaster`
    * Good: `AuctionBidBroadcaster` or `StockPriceStreamer`
    * Bad: `UserManager`
    * Good: `UserAuthenticationSession` or `AdminPrivilegeGuard`

* **Variables & Arguments:**
    * Bad: `data`, `res`, `payload`
    * Good: `incomingBidPayload`, `apiResponseJson`, `sanitizedUserInput`

* **Booleans:**
    * Must answer a specific question.
    * Bad: `valid`, `done`, `flag`
    * Good: `isEmailFormatValid`, `hasAuctionEnded`, `shouldRetryConnection`

* **Arrays/Collections:**
    * Must be plural and descriptive.
    * Bad: `list`, `items`
    * Good: `pendingApprovalQueues`, `verifiedUserList`

---

## 3. Coding Style & Behavior
* **Explicit over Implicit:** If a variable name requires a comment to explain what it holds, rename the variable instead.
* **No "YOLO" Coding:**
    * Always add type definitions (if applicable).
    * Do not leave "TODO" or incomplete mock logic unless explicitly asked.
* **Refactoring:** When asked to refactor, prioritize renaming generic terms to domain-specific terms first.


### Output
- Return code first. Explanation after, only if non-obvious.
- No inline prose. Use comments sparingly - only where logic is unclear.
- No boilerplate unless explicitly requested.

### Code Rules
- Simplest working solution. No over-engineering.
- No abstractions for single-use operations.
- No speculative features or "you might also want..."
- Read the file before modifying it. Never edit blind.
- No docstrings or type annotations on code not being changed.
- No error handling for scenarios that cannot happen.
- Three similar lines is better than a premature abstraction.

### Review Rules
- State the bug. Show the fix. Stop.
- No suggestions beyond the scope of the review.
- No compliments on the code before or after the review.

### Detection Command Examples
```bash
# With video file for testing
python main.py --source recordings/test.avi --loop

# With Hailo AI accelerator (RPi 5 + AI Kit)
python main.py --model_type hailo --model_path yolov8n.hef


### Development Setup

**PC:**
```bash
uv init
uv add -r requirements.txt
source .venv/bin/activate  # or venv\Scripts\activate on Windows
```

### Running Tests
```bash
uv run pytest           # run all unit tests
uv run pytest -v        # verbose output
uv run pytest -x        # stop on first failure
uv run pytest --model_type hailo --model_path yolov8n.hef   # detector for the video pipeline tests (default yolo yolov8n.pt)

# whole suite on the rpi with its Hailo model, log in test_results/rpi_pytest.log
pyinfra pyinfra/inventory.py pyinfra/run_tests.py --limit rpi -y
```
Pipeline tests run every `test_videos/<name>.<ext>` that has a `test_videos/<name>.zones.yaml` next to it.

### OpenCV GStreamer Check
```bash
# Verify GStreamer support in OpenCV after env install
python -c "import cv2; print(cv2.getBuildInformation())" | grep -i gstreamer
```

### Development Mode (Vite Dev Server + Flask Backend)

**When changing the frontend, always start the local PC version (backend + Vite dev server, both in background) so the change can be checked interactively in the browser at http://localhost:3000.** Known-working commands from the repo root:
```bash
uv run python main.py --web_stream --source recordings/event_20260129_135641.avi --loop --model_path yolov8n.pt
cd frontend && npm run dev
```

For frontend development with hot module reload, run the Vite dev server separately from the Flask backend:

**Terminal 1: Start Flask Backend**
```bash
cd /workspace
python main.py --web_stream --source <your_video_source>

# Examples:
python main.py --web_stream --source picamera  # RPi with camera
python main.py --web_stream --source gstreamer  # PC receiving stream
python main.py --web_stream --source test.mp4 --loop  # Video file
```

**Note**: The Flask backend will start on port **9090** by default (matches Vite proxy).

**Terminal 2: Start Vite Dev Server**
```bash
cd /workspace/frontend
npm run dev
```

Access the application at: **http://localhost:3000**

The Vite dev server will automatically proxy requests to the Flask backend:
- `/api/*` → `http://localhost:9090/api/*` (zones, settings, detections)
- `/video_feed` → `http://localhost:9090/video_feed` (MJPEG stream)
- `/metrics` → `http://localhost:9090/metrics` (performance metrics)


4. **Check browser console** for CORS errors or connection failures

## Deployment to Raspberry Pi

scripts in pyinfra/ define the deployment







**Pyinfra:**


### Initial Configuration

Edit `pyinfra/inventory.py`:

### Deployment Commands

**Deploy to all devices:**
```bash

**Rolling update (one device at a time):**
```bash
pyinfra pyinfra/inventory.py   pyinfra/monitor.py --data deploy_tag=v1.2.3 --parallel 1
```

**Deploy (host setup once, environment when dependencies change, code on every change):**
```bash
pyinfra pyinfra/inventory.py pyinfra/setup_host.py --limit rpi
pyinfra pyinfra/inventory.py pyinfra/install_environment.py --limit rpi
pyinfra pyinfra/inventory.py pyinfra/upload_code.py --limit rpi
```

**All-in-one idempotent host deploy (after setup_host; stops the old car-statistics service, restarts local-traffic, checks /metrics):**
```bash
pyinfra pyinfra/inventory.py pyinfra/deploy.py --limit rpi
```

**Docker fresh-install test image on the Pi:**
```bash
pyinfra pyinfra/inventory_docker.py pyinfra/install_environment.py -y
```

**Dry-run (preview changes):**
```bash
--dry
```


#### References

- [Official Raspberry Pi AI Kit Documentation](https://www.raspberrypi.com/documentation/accessories/ai-kit.html)
- [Hailo RPi5 Examples Repository](https://github.com/hailo-ai/hailo-rpi5-examples)
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)
- [Hailo Community Forums](https://community.hailo.ai/)

## Architecture

### Core Design Pattern
The codebase follows a **modular, shared-core architecture**:

1. **Shared Processing Logic** (`processing.py`): Main detection/tracking loop used by all platforms
2. **Unified Entry Point**: `main.py` handles both PC and RPi platforms through command-line arguments
3. **Video Source Abstraction** (`video_source.py`): Unified interface for OpenCV sources, Pi Camera, and GStreamer
4. **Model Abstraction** (`detectors/`): Modular detector package supporting YOLO, RF-DETR, Hailo, NCNN, and motion detection
5. **Event-Driven Architecture** (`event_manager.py`): Events dispatched to listeners (DB, console, etc.)

### Key Architectural Concepts

**Processing Pipeline Flow:**
```
Video Source → Detector → Tracker (ByteTrack) → Motion Detectors → Zone Manager → Event Manager → Listeners
                                                                                                      ↓
                                                                  Ring Buffer → Event Video Writer ← Recording Trigger
```

**Video Source Abstraction:**
- `BaseVideoSource`: Abstract interface with `read()`, `release()`, `get_fps()`, `is_opened()`
- `OpenCVVideoSource`: Handles GStreamer streams, video files, webcams
- `PiCameraVideoSource`: Direct Pi Camera access via picamera2

**Detector Abstraction:**
- `BaseDetector`: Abstract interface with `predict(image, conf_threshold)`
- `YOLODetector`: Ultralytics YOLO models (yolov8n/s/m/l/x.pt)
- `RFDETRDetector`: RF-DETR transformer-based detector
- `HailoDetector`: Hardware-accelerated inference on Hailo-8L (RPi 5 AI Kit)

**Zone Detection System:**
- `LineZoneWrapper`: Robust line crossing detection using segment intersection (works at low framerates)
- `PolygonZoneWrapper`: Polygon zone entry/exit detection
- `ZoneManager`: Loads zones from YAML config, dispatches events

**Event System:**
- Events: `line_cross`, `zone_enter`, `zone_exit`
- Listeners implement `handle_event(event)` method
- Built-in listeners: `ConsoleEventListener`, `PostgresHandler`

**Motion Detection:**
- `MovingObjectDetector`: Detects objects with significant displacement (centroid movement > threshold)
- Two separate `MovingObjectDetector` instances: one for visualization (30 frames), one for recording triggers (90 frames)

**Recording System:**
- `VideoRingBuffer`: Maintains pre-event buffer (5s on PC, 3s on RPi)
- `EventVideoWriter`: Triggered recording with pre/post-event buffers
- Recording triggered when object moves for full history length (90 frames)

### Configuration System

The system uses dataclass-based configs with platform-specific defaults:

- `ProcessingConfig`: Base configuration
- `PCConfig`: PC-optimized (yolov8s, 5s buffer, display enabled)
- `RPiConfig`: RPi-optimized (yolov8n, 3s buffer, display disabled)

Use `ProcessingConfig.from_args(args)` to create config from argparse namespace.

### Class ID Conventions

**IMPORTANT:** The codebase uses a unified class ID translation utility to ensure consistency across all detector types.

**Internal Model Formats:**
- **YOLO/Hailo/NCNN models**: 0-based class IDs (0=person, 1=bicycle, 2=car, 3=motorcycle, 5=bus, 7=truck)
- **RF-DETR models**: 1-based class IDs (1=person, 2=bicycle, 3=car, 4=motorcycle, 6=bus, 8=truck)
- **COCO_CLASSES dictionary**: 1-based class IDs (matches RF-DETR)

**Automatic Translation:**
All detectors use the `translate_class_ids_to_coco()` utility function to convert model-specific class IDs to the unified COCO 1-based format. This ensures:
- Correct class name lookups in `COCO_CLASSES` dictionary
- Consistent behavior across all detector types (YOLO, Hailo, NCNN, RF-DETR)
- No manual offset adjustments needed in zone configurations or event handlers

**For Developers:**
When adding new detector types, call `translate_class_ids_to_coco(detections)` before returning from `predict()` if the model uses 0-based indexing. Don't call it for models already using COCO 1-based format:

```python
# Example for 0-based model (YOLO, Hailo, NCNN)
from detector_utils import translate_class_ids_to_coco

def predict(self, image, conf_threshold=0.3):
    detections = self.model.predict(image)
    return translate_class_ids_to_coco(detections)  # Adds 1 to class IDs

# Example for 1-based model (RF-DETR, already COCO format)
def predict(self, image, conf_threshold=0.3):
    return self.model.predict(image)  # No translation needed
```

## Critical Implementation Details

### Zone Configuration (zones.yaml)

Zones are defined in YAML with geometry and optional class filters:

```yaml
zones:
  - name: "Main Crossing"
    type: "line"
    geometry: [[x1, y1], [x2, y2]]
    trigger_classes: ["car", "truck", "bicycle"]

  - name: "Parking Area"
    type: "polygon"
    geometry: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    trigger_classes: ["car"]
```

Load via `--zone_config zones.yaml` or set `ZONE_CONFIG` environment variable.

### Line Crossing Detection

The `LineZoneWrapper` uses **segment intersection** instead of simple point-in-line tests. This is critical for low-framerate scenarios (RPi) where objects may "jump" over lines between frames. The implementation:

1. Stores previous position for each tracker_id
2. Checks if segment (prev_pos → current_pos) intersects the line
3. Uses cross product method (`segments_intersect()`) for robust detection
4. Determines direction using `point_side_of_line()`
5. Marks tracker_id as crossed to prevent duplicate events

### GStreamer Pipeline

**On RPi (sender):**
```bash
rpicam-vid -t 0 --width 1280 --height 720 --framerate 30 --vflip --hflip \
  --inline --libav-format h264 -o - | \
  gst-launch-1.0 fdsrc ! h264parse ! rtph264pay config-interval=1 pt=96 ! \
  udpsink host=<PC_IP> port=9000
```

**On PC (receiver):**
```python
# In OpenCVVideoSource._get_gstreamer_pipeline()
"udpsrc port=9000 ! "
"application/x-rtp, media=(string)video, clock-rate=(int)90000, "
"encoding-name=(string)H264, payload=(int)96 ! "
"rtph264depay ! avdec_h264 ! videoconvert ! "
"video/x-raw, format=(string)BGR ! appsink drop=true"
```

### Environment Variables

Required for database storage:
```bash
POSTGRES_CONNECTION_STRING="postgresql://user:pass@host:port/dbname"
ZONE_CONFIG="zones.yaml"  # Optional, can also use --zone_config
```

### Web Streaming

Enable with `--web_stream --web_port 8080`. Access at `http://<device_ip>:8080/video_feed`.

The `WebStreamer` class runs a Flask server in a background thread serving MJPEG stream.

## Development Guidelines

### When Adding Features

1. **Shared Logic**: Add to `processing.py` if used by all platforms
2. **Platform-Specific**: Modify `main.py` only if platform-specific behavior is needed (rare)
3. **Configuration**: Add new parameters to `ProcessingConfig` dataclass and update `add_common_args()`
4. **Event Listeners**: Implement `handle_event(event)` method and register with `EventManager`

### When Modifying Detection

- Detector classes must implement `predict(image, conf_threshold)` returning `supervision.Detections`
- YOLO expects BGR images, RF-DETR expects RGB
- Always use external ByteTrack for consistency across models

### When Adding Zone Types

1. Subclass `ZoneWrapper` from `zone_manager.py`
2. Implement `update(detections, event_manager)` and `annotate(frame)`
3. Add to `ZoneManager.load_config()` type dispatch


### Performance Tuning

**Performance Benchmarks (Raspberry Pi 5 8GB + Hailo-8L):**

Tested with YOLOv8n model at 1280x720 resolution:
- **YOLO** (PyTorch): 5 fps - Standard Ultralytics inference
- **NCNN** (CPU optimized): 10 fps - 2x faster than PyTorch
- **Hailo** (AI Kit): 51 fps - 10x faster, hardware acceleration

**Recommendation**: Use Hailo for real-time applications on RPi 5 with AI Kit. NCNN is a good middle ground for RPi without Hailo hardware.

**RPi Optimizations:**
- Use yolov8n.pt (fastest YOLO nano model)
- Lower resolution: `--resolution 640x480`
- Reduce framerate: `--framerate 10`
- Use Hailo acceleration if available (51 fps vs 5 fps)

**PC Optimizations:**
- Use yolov8s/m for better accuracy
- Increase buffer sizes for longer pre-event capture
- Use RF-DETR for highest accuracy (slower)

## File Structure Reference

```
Core Processing:
├── processing.py           # Main detection loop, config system, pipeline setup
├── detectors/              # Detector package
│   ├── base.py            # BaseDetector abstract class
│   ├── yolo.py            # YOLO detector
│   ├── rfdetr.py          # RF-DETR detector
│   ├── ncnn.py            # NCNN detector (CPU optimized)
│   ├── hailo.py           # Hailo detector (hardware accelerated)
│   ├── motion.py          # Motion-based detector
│   └── factory.py         # Detector factory function
├── video_source.py         # Video source abstraction
├── zone_manager.py         # Line/polygon zone detection with events
├── event_manager.py        # Event dispatch system
├── db_handler.py           # PostgreSQL event storage
├── video_utils.py          # Ring buffer, event recording
├── stationary_utils.py     # Motion detection utilities
├── console_listener.py     # Console logging for events
└── web_streamer.py         # Web-based video streaming

Entry Point:
└── main.py                 # Universal application (PC and RPi)

Configuration:
├── zones.yaml              # Zone definitions
├── .env                    # Environment variables (DB connection)
├── requirements.txt        # PC dependencies
├── requirements-rpi.txt    # RPi dependencies
└── pyproject.toml          # Project metadata (uv package manager)
```

## Coding Standards for Generated Code

When generating or modifying code, follow these principles to ensure maintainability and clarity:

### 1. Minimize Internal State

**Principle:** Only store what's truly necessary to persist between operations. Avoid caching computed values or storing temporary data as instance variables.

**Bad - Unnecessary state:**
```python
class VehicleProcessor:
    def __init__(self):
        self.temp_detections = None
        self.last_count = 0
        self.cached_result = None

    def process(self, detections):
        self.temp_detections = detections
        self.last_count = len(detections)
        self.cached_result = self._analyze(self.temp_detections)
        return self.cached_result
```

**Good - Minimal state:**
```python
class VehicleProcessor:
    def __init__(self, model_config):
        self.model_config = model_config  # Only config persists

    def process(self, detections):
        return self._analyze(detections, self.model_config)
```

**Guidelines:**
- Pass data as function parameters, not instance variables
- Use `@property` for computed values instead of caching
- Question every `self.variable` - does it really need to persist?
- Prefer functional approaches where possible
- Code is the documentation, if readable enough the functionality doesnt need to be described indocumentation block, less is moree in this case

### 2. Use Specific, Descriptive Names

**Principle:** Variable names should reveal intent. Avoid generic names like `data`, `items`, `temp`, `result`.

**Bad - Generic names:**
```python
def process(data, flag):
    result = []
    for item in data:
        temp = item.value
        if flag and temp > 0:
            result.append(temp)
    return result
```

**Good - Specific names:**
```python
def filter_moving_vehicles(detections, include_stationary):
    vehicle_speeds = []
    for detection in detections:
        current_speed = detection.speed
        if include_stationary or current_speed > 0:
            vehicle_speeds.append(current_speed)
    return vehicle_speeds
```

**Naming Rules:**
- **Functions:** Use verbs (`calculate_speed`, `filter_zones`, `annotate_frame`)
- **Classes:** Use nouns (`ZoneManager`, `EventListener`, `VideoRingBuffer`)
- **Booleans:** Use questions (`is_active`, `has_crossing`, `should_record`)
- **Collections:** Pluralize (`detections`, `zone_events`, `tracked_vehicles`)
- **Avoid abbreviations** except standard ones (fps, url, id, api)


### 3. Eliminate Duplication (DRY)

**Principle:** Extract repeated logic into functions. Don't copy-paste code.

**Bad - Duplicated logic:**
```python
# In zone_manager.py
if vehicle_class in ["car", "truck", "bus", "motorcycle"]:
    heavy_vehicle_count += 1

# In event_handler.py
if vehicle_class in ["car", "truck", "bus", "motorcycle"]:
    record_heavy_vehicle_event(vehicle_class)

# In statistics.py
if vehicle_class in ["car", "truck", "bus", "motorcycle"]:
    update_heavy_vehicle_stats()
```

**Good - Extracted function:**
```python
# In vehicle_utils.py
def is_heavy_vehicle(vehicle_class):
    """Check if vehicle class is considered heavy for tracking purposes."""
    return vehicle_class in ["car", "truck", "bus", "motorcycle"]

# Usage everywhere:
if is_heavy_vehicle(vehicle_class):
    heavy_vehicle_count += 1
```

### 4. Add code comments only when they improve understanding, avoid banal comments

*** Bad ***
```python
    # Update in-memory settings
    self.camera_settings = settings
```

*** Good ***
```python
    self.camera_settings = settings
```

code speeks for itslef, doesnt need additional commment

**Guidelines:**
- If you write the same logic twice, extract it
- Create utility modules for shared functions
- Use composition over deep inheritance hierarchies

### 4. Reduce Complexity

**Principle:** Keep functions short, focused, and easy to understand. Avoid deep nesting.

**Function Guidelines:**
- **Length:** Aim for <20 lines; split longer functions
- **Parameters:** Max 3-4; use config objects if you need more
- **Single Responsibility:** One function does one thing
- **Early returns:** Reduce nesting with guard clauses



### 5. Project-Specific Patterns

When working with this codebase:

- **Always use `translate_class_ids_to_coco()`** for detector outputs to ensure consistent class ID format
- **Pass `supervision.Detections` objects** through the pipeline; don't extract and reconstruct
- **Event listeners should be stateless** when possible
- **Use dataclasses for configuration** objects, not dictionaries
- **Zone geometry** is always in pixel coordinates matching video resolution

### Quick Code Review Checklist

Before committing generated code, verify:

- [ ] Are all variable names specific and meaningful?
- [ ] Is any logic duplicated that could be extracted?
- [ ] Are functions <20 lines and doing one thing?
- [ ] Is state minimized to only what must persist?
- [ ] Are there magic numbers that should be named constants?
- [ ] Could any complex conditionals be extracted into named functions?
- [ ] Are there early returns to reduce nesting?


