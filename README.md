# Traffic Detection

Real-time car/vehicle traffic detection using YOLO or RF-DETR models. Supports both PC (receiving video stream) and Raspberry Pi (direct camera capture).

* initially based on roboflow tracking and counting
    * https://blog.roboflow.com/yolov8-tracking-and-counting/
        * https://colab.research.google.com/github/roboflow-ai/notebooks/blob/main/notebooks/how-to-estimate-vehicle-speed-with-computer-vision.ipynb?ref=blog.roboflow.com
        * https://blog.roboflow.com/estimate-speed-computer-vision/
        * roboflow umi i rtps stream https://inference.roboflow.com/quickstart/run_model_on_rtsp_webcam/#installation

## Architecture

```
Shared Code:
├── video_source.py      # Video source abstraction
├── processing.py        # Main detection/tracking loop
├── detectors/           # Model abstraction (YOLO, RF-DETR, Hailo, NCNN)
│   ├── base.py         # BaseDetector abstract class
│   ├── yolo.py         # YOLO detector
│   ├── rfdetr.py       # RF-DETR detector
│   ├── ncnn.py         # NCNN detector (CPU optimized)
│   ├── hailo.py        # Hailo detector (hardware accelerated)
│   ├── motion.py       # Motion-based detector
│   └── factory.py      # Detector factory function
├── video_utils.py       # Ring buffer, event recording
├── zone_manager.py      # Line/polygon zone detection
├── event_manager.py     # Event dispatch system
├── db_handler.py        # PostgreSQL storage
└── stationary_utils.py  # Motion detection

Entry Point:
└── main.py              # Universal: PC and RPi support
```

## Quick Start

### Raspberry Pi

```bash
# Default: Pi Camera with optimized settings
python main.py

# With camera flip (if mounted upside down)
python main.py --vflip --hflip

# Lower resolution for better performance
python main.py --resolution 640x480 --framerate 10

```

### PC/Desktop

```bash
# Receive GStreamer stream on port 9000
python main.py --source gstreamer

# With video file (for testing)
python main.py --source video.mp4 --loop

# With webcam
python main.py --source 0

# With RF-DETR model
python main.py --source gstreamer --model_type rfdetr
```

### Common Options

Both PC and Raspberry Pi support the same arguments:
- `--model_type`: Model type (`yolo`, `rfdetr`, `hailo`, `ncnn`)
- `--zone_config`: Path to zone configuration YAML
- `--web_stream`: Enable web streaming on port 8080
- `--record_events`: Enable event-based recording

## Streaming from RPi to PC

If you want to run detection on PC while streaming from RPi:

**On RPi (send stream):**
```bash
rpicam-vid -t 0 --width 1280 --height 720 --framerate 30 --vflip --hflip --inline --libav-format h264 -o - | \
  gst-launch-1.0 fdsrc ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=<PC_IP> port=9000
```
 * rpicam-vid -t 0 --width 1280 --height 720 --framerate 30 --vflip --hflip --inline --libav-format h264 -o - | gst-launch-1.0 fdsrc ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=<PC_HOST> port=9000
 * gst-launch-1.0 udpsrc port=9000 ! application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! autovideosink sync=false


**On PC (receive and process):**
```bash
python main.py --source gstreamer
```

**Test stream without detection:**
```bash
gst-launch-1.0 udpsrc port=9000 ! application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! autovideosink sync=false
```

## Command Line Arguments

### main.py (All Platforms)

| Argument | Default | Description |
|----------|---------|-------------|
| `--source` | `picamera` | Video source: `picamera`, `gstreamer`, file path, or webcam index (0,1) |
| `--model_type` | `yolo` | Model type: `yolo`, `rfdetr`, `hailo`, or `ncnn` |
| `--model_path` | `yolov8s.pt` | Path to model weights |
| `--conf_thresh` | `0.3` | Detection confidence threshold |
| `--record_events` | off | Enable event-based recording |
| `--buffer_size` | `3.0` | Pre-event buffer in seconds |
| `--post_event` | `5.0` | Post-event recording in seconds |
| `--tail_length` | `20` | Length of movement tails (frames) |
| `--zone_config` | none | Path to zone configuration YAML |
| `--loop` | off | Loop video file |
| `--resolution` | `1280x720` | Camera resolution WxH (picamera only) |
| `--framerate` | `15` | Camera framerate (picamera only) |
| `--vflip` | off | Flip video vertically (picamera only) |
| `--hflip` | off | Flip video horizontally (picamera only) |
| `--web_stream` | off | Enable web streaming |
| `--web_port` | `8080` | Web streaming port |

## RPi Optimized Defaults

The RPi version uses optimized defaults for limited compute:
- Model: `yolov8n.pt` (nano - fastest)
- Framerate: 15fps
- Display: disabled
- Buffer: 3 seconds

## Environment Variables

| Variable | Description |
|----------|-------------|
| `POSTGRES_CONNECTION_STRING` | PostgreSQL connection URL for event storage |
| `ZONE_CONFIG` | Path to zone configuration YAML |

## Requirements

### PC
```bash
pip install -r requirements.txt
```

### Raspberry Pi

See [Raspberry Pi Installation](#raspberry-pi-installation) section below for detailed setup instructions.

## OpenCV GStreamer Support

Check if GStreamer is enabled:
```bash
python -c "import cv2; print(cv2.getBuildInformation())" | grep -i gstreamer
```

If it shows `GStreamer: NO`, you need to uninstall opencv-python and install opencv with GStreamer support:
```bash
pip uninstall opencv-python
# Install opencv-python built with GStreamer support
```

## Raspberry Pi Installation

### Prerequisites

Raspberry Pi 4 or 5 with Raspberry Pi OS (64-bit recommended).

### 1. Install system dependencies

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-libcamera python3-opencv python3-venv
```

### 2. Create virtual environment with system packages

```bash
cd /path/to/project
python3 -m venv --system-site-packages venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements-rpi.txt
```

### 4. Verify installation

```bash
# Check picamera2
python -c "from picamera2 import Picamera2; print('picamera2 OK')"

# Check OpenCV
python -c "import cv2; print('OpenCV', cv2.__version__)"
```

### 5. Run the application

```bash
# Basic usage with Pi Camera
python main.py

# With camera flip (if mounted upside down)
python main.py --vflip --hflip

# Lower resolution for better performance
python main.py --resolution 640x480 --framerate 10

# With zone configuration
python main.py --zone_config zones.yaml
```

### Hailo Acceleration (RPi 5 + AI Kit)

The Hailo AI Kit provides 10x performance improvement over CPU-based YOLO (51 fps vs 5 fps).


For detailed installation instructions, hardware requirements, model compilation, and troubleshooting, see **CLAUDE.md** section "Hailo AI Kit Installation".

#### Manual Installation

1.  **Install Hailo Software**:
    ```bash
    sudo apt update
    sudo apt install hailo-all -y
    ```

2.  **Download Compiled Model (.hef)**:
    ```bash
    wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.12.0/hailo8l/yolov8n.hef
    ```

3.  **Run with Hailo**:
    ```bash
    python main.py --model_type hailo --model_path yolov8n.hef
    ```


### NCNN Acceleration (CPU optimized)

NCNN provides optimized CPU inference, which can be faster than standard PyTorch on Raspberry Pi.

1.  **Export Model to NCNN format**:
    You need to export your YOLOv8 model to NCNN format using Ultralytics.
    ```bash
    yolo export model=yolov8n.pt format=ncnn
    # This creates a folder 'yolov8n_ncnn_model' containing 'model.ncnn.param' and 'model.ncnn.bin'
    ```

2.  **Run with NCNN**:
    ```bash
    # CPU (default)
    python main.py --model_type ncnn --model_path yolov8n_ncnn_model

    # GPU (Vulkan)
    python main.py --model_type ncnn --model_path yolov8n_ncnn_model --ncnn_vulkan
    ```

### Performance Benchmarks (Raspberry Pi 5 8GB + Hailo-8L)

Tested with YOLOv8n model at 1280x720 resolution:

| Backend | FPS | Notes |
|---------|-----|-------|
| **YOLO** (PyTorch) | 5 fps | Standard Ultralytics inference |
| **NCNN** (CPU) | 10 fps | 2x faster than PyTorch |
| **Hailo** (AI Kit) | 51 fps | 10x faster - hardware acceleration |

**Recommendation**: Use Hailo for real-time applications on RPi 5 with AI Kit. NCNN is a good middle ground for RPi without Hailo hardware.

### RPi Performance Tips

- Use `yolov8n.pt` (nano) model - it's the default and fastest
- Lower resolution (640x480) improves framerate significantly
- Use 15fps or lower for stable detection
- Consider passive cooling or heatsinks for extended operation

### Streaming Only (No Local Detection)

If you want RPi to only stream video to a PC for processing:

```bash
# On RPi - stream to PC
rpicam-vid -t 0 --width 1280 --height 720 --framerate 30 --vflip --hflip \
  --inline --libav-format h264 -o - | \
  gst-launch-1.0 fdsrc ! h264parse ! rtph264pay config-interval=1 pt=96 ! \
  udpsink host=<PC_IP> port=9000

# On PC - receive and process
python main.py --source gstreamer
```

## RPI

**Service Management Commands** (on RPi):
```bash
# View live logs
sudo journalctl -u local-traffic -f

# Restart service
sudo systemctl restart local-traffic
sudo systemctl stop local-traffic
sudo systemctl start local-traffic
sudo systemctl status local-traffic
```
### Deployment Best Practices

1. **Always use Git tags** for deployments (enables version tracking)
   ```bash
   git tag -a v1.2.3 -m "Add new zone detection feature"
   git push origin v1.2.3
   ```

4. **Check logs after deployment**
   ```bash
   ssh <user>@<rpi-host>
   sudo journalctl -u local-traffic -f
   ```

## Troubleshooting

### Hailo + NCNN Compatibility Issue (Numpy Version Conflict)

**Problem**: After installing NCNN, Hailo detector fails with:
```
[HailoRT] [error] CHECK failed - Memory size of vstream yolov8n/input_layer1 does not match the frame count! (Expected 1228800, got 0)
```

**Root Cause**:
- Hailo requires **numpy 1.x** (1.20-1.26)
- NCNN installation may upgrade numpy to **2.x**
- Numpy 2.0 introduced breaking changes in the C API that make Hailo incompatible

**Solution**:

1. **Pin numpy version** in `requirements-rpi.txt` and `requirements.txt`:
   ```
   numpy>=1.20,<2.0  # Hailo requires numpy 1.x (not 2.x)
   ```

2. **Reinstall numpy** at correct version:
   ```bash
   pip uninstall -y numpy
   pip install "numpy>=1.20,<2.0"
   python3 -c "import numpy; print('numpy:', numpy.__version__)"  # Should show 1.26.x
   ```

3. **Code fix applied** in `detector_utils.py` (HailoDetector.predict):
   ```python
   input_data = np.expand_dims(input_data, axis=0)
   input_data = np.ascontiguousarray(input_data, dtype=np.uint8)  # Ensure C-contiguous array
   ```
   This ensures the array memory layout is compatible with Hailo's requirements.

**Verification**:
```bash
# Test Hailo
python main.py --model_type hailo --model_path yolov8n.hef --source picamera

# Test NCNN
python main.py --model_type ncnn --model_path yolov8n_ncnn_model --source picamera
```

Both should work without errors.

## Testing and Debugging

### Interactive Detector Testing

#### Web UI (Recommended)

Use `test_detector_web.py` for a web-based interface accessible from any browser on port **9091**:

```bash
# Test with Hailo detector
python test_detector_web.py --source_dir ./test_images --model_type hailo --model_path yolov8n.hef

# Test with YOLO detector
python test_detector_web.py --source_dir ./test_images --model_type yolo --model_path yolov8n.pt

# Test with NCNN detector
python test_detector_web.py --source_dir ./test_images --model_type ncnn --model_path yolov8n_ncnn_model

# Test with RF-DETR detector
python test_detector_web.py --source_dir ./test_images --model_type rfdetr

# With custom confidence threshold
python test_detector_web.py --source_dir ./test_images --model_type yolo --conf_thresh 0.5
```

Then open **http://localhost:9091** in your browser.

**Features:**
- 🌐 Web-based UI accessible from any device on the network
- ⬅️➡️ Navigate with buttons or arrow keys
- 🎚️ Real-time confidence threshold adjustment with slider
- 📊 Live detection count and debug information
- 🎨 Dark theme with cyberpunk aesthetics
- 📱 Responsive design for mobile and desktop
- 🚀 Perfect for headless RPi deployments (SSH + browser)

**Features:**
- Visual verification of object detection and class labeling
- Displays class IDs and names for debugging
- Shows detection count and confidence scores
- Auto-resizes large images for display
- Perfect for testing class ID translation fixes



### Common Issues

**OpenCV without GStreamer support:**
- PC: Install opencv-python compiled with GStreamer
- RPi: Use system OpenCV (`python3 -m venv --system-site-packages`)

**Zone events not firing:**
- Verify zone coordinates match video resolution
- Check `trigger_classes` filter in zones.yaml
- Use segment intersection for lines (robust to low FPS)

**Recording not triggering:**
- Increase `--buffer_size` and `--post_event` durations
- Check if objects are classified in `trigger_classes`
- Verify object movement exceeds `min_displacement` threshold

## Links

- [Supervision Library](https://supervision.roboflow.com/0.26.0/#install)


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

**Docker fresh-install test image on the Pi:**
```bash
pyinfra pyinfra/inventory_docker.py pyinfra/install_environment.py -y
```

**Dry-run (preview changes):**
```bash
--dry
```
### Ad-Hoc Commands

```bash
# Execute command on all devices
pyinfra inventory.py exec -- uptime

# Check service status
pyinfra inventory.py exec -- sudo systemctl status local-traffic

# View logs
pyinfra inventory.py exec -- sudo journalctl -u local-traffic -n 20
```


### Pyinfra Best Practices

1. **Use Git tags** for deployments
2. **Test a fresh install in Docker first** (`pyinfra pyinfra/inventory_docker.py pyinfra/install_environment.py`)
3. **Use `--parallel 1`** for production rolling updates
4. **Test with `--dry`** flag first
5. **Monitor regularly** with `monitor.py`

See `pyinfra/README.md` for complete documentation.

### Hailo AI Kit Installation (Raspberry Pi 5)

The Hailo AI Kit provides hardware-accelerated inference with 10x performance improvement over CPU-based YOLO (51 fps vs 5 fps). Follow these steps to set up the Hailo-8L AI accelerator on Raspberry Pi 5.

For **Raspberry Pi OS Trixie** (latest):
```bash
sudo apt update
sudo apt install dkms -y
sudo apt install hailo-all -y
```


This installs:
- Hailo firmware and kernel drivers (DKMS)
- HailoRT runtime libraries
- TAPPAS Core (GStreamer elements and post-processing)
- Python bindings for HailoRT

**3. Configure PCIe Speed** (M.2 HAT users only, AI HAT+ auto-configures)

Enable PCIe Gen3 for optimal performance (Gen2 works but reduces throughput):
```bash
sudo raspi-config
# Navigate: 6 Advanced Options → A8 PCIe Speed → Yes (Enable Gen3)
sudo reboot
```
**4. Verify Installation**

Check Hailo device detection:
```bash
lspci | grep Hailo
# Expected: "Hailo-8 AI Processor" or similar
```

Verify HailoRT:
```bash
hailortcli fw-control identify
# Should display Hailo device information
```

Verify GStreamer plugins:
```bash
gst-inspect-1.0 hailotools
gst-inspect-1.0 hailo
# Both should list available Hailo elements
```

If GStreamer plugins fail to load, clear the cache:
```bash
rm ~/.cache/gstreamer-1.0/registry.aarch64.bin
gst-inspect-1.0 hailo  # Re-inspect
```

**5. Install Project Dependencies**

```bash
source venv/bin/activate
pip install "numpy>=1.20,<2.0"  # Critical: Hailo requires numpy 1.x
pip install hailort  # Python bindings
```



#### Model Compilation

Hailo requires models in **HEF (Hailo Executable Format)**. YOLO `.pt` models must be converted using the Hailo Dataflow Compiler.

**Option 1: Use Pre-compiled Models**

Download pre-compiled models from [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo):
```bash
# Example: Download YOLOv8n HEF
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.12.0/hailo8l/yolov8n.hef
```

**Option 2: Compile Custom Models**

Convert ONNX models to HEF using Hailo Dataflow Compiler (requires separate installation):

1. Export YOLO model to ONNX:
```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
model.export(format="onnx", imgsz=640)
```

2. Compile ONNX to HEF using Hailo Model Zoo:
```bash
hailomz compile --ckpt yolov8n.onnx \
                --hw-arch hailo8l \
                --calib-path calibration_images/ \
                --yaml yolov8n.yaml \
                --classes 80
```

**Calibration Requirements:**
- 16-64 representative images from training dataset
- Diverse samples covering typical use cases
- Used for quantization optimization

**Note:** Hailo Dataflow Compiler runs in Docker and requires significant RAM. Consider using pre-compiled models for faster setup.

#### Troubleshooting

**PCIe Detection Issues:**
```bash
# Verify PCIe connection
lspci | grep Hailo

# Check PCIe speed (should show Gen3 for best performance)
sudo dmesg | grep -i pcie
```

## UV
system packages trouble with pyaudio and numpy
```
uv venv --system-site-packages
```

then uv sync , but then its incopmatible with the container and vice versa ... 

how to run py test inside container, sharing  of the .venv file is nontrivi

**Driver Page Size:**
Ensure `/etc/modprobe.d/hailo_pci.conf` contains:
```
options hailo_pci force_desc_page_size=4096
```

**Numpy Version Conflict (CRITICAL):**
Hailo requires numpy 1.x. If you see "Memory size does not match" errors:
```bash
pip uninstall -y numpy
pip install "numpy>=1.20,<2.0"
```

## Common Issues

**CRITICAL: Hailo + NCNN numpy version conflict:**
- **Issue**: Hailo fails with "Memory size... does not match! (Expected 1228800, got 0)"
- **Cause**: Hailo requires numpy 1.x, NCNN installation may upgrade to numpy 2.x
- **Fix**: Pin numpy version in requirements files:
  ```
  numpy>=1.20,<2.0  # Hailo requires numpy 1.x (not 2.x)
  ```
- **Reinstall**: `pip uninstall -y numpy && pip install "numpy>=1.20,<2.0"`
- **Code fix**: `detector_utils.py:322` uses `np.ascontiguousarray()` to ensure C-contiguous array layout
- Both Hailo and NCNN work correctly with numpy 1.26.x

**OpenCV without GStreamer support:**
- PC: Install opencv-python compiled with GStreamer
- RPi: Use system OpenCV (`python3 -m venv --system-site-packages`)

**Hailo model output format:**
- Check if HEF includes NMS postprocessing
- Debug by printing output keys/shapes in `HailoDetector.predict()`
- May need custom decoder for specific HEF compilation

**Zone events not firing:**
- Verify zone coordinates match video resolution
- Check `trigger_classes` filter in zones.yaml
- Use segment intersection for lines (robust to low FPS)

**Recording not triggering:**
- Increase `--buffer_size` and `--post_event` durations
- Check if objects are classified in `trigger_classes` (processing.py:241-244)
- Verify object movement exceeds `min_displacement` threshold