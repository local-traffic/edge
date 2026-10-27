"""
Video source abstraction for cross-platform support.
Provides unified interface for OpenCV sources (PC) and Pi Camera (RPi).
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
import numpy as np
import cv2


class BaseVideoSource(ABC):
    """Abstract base class for video sources."""

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read a frame. Returns (success, frame_bgr)."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release resources."""
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """Get the frame rate."""
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """Check if source is open."""
        pass

    def reopen(self) -> bool:
        """Reopen source for looping. Returns success."""
        return False


class OpenCVVideoSource(BaseVideoSource):
    """Video source using OpenCV (GStreamer, files, webcams)."""

    def __init__(self, source: str):
        """
        Args:
            source: 'gstreamer', file path, or webcam index as string
        """
        self.source_spec = source
        self.cap = None
        self._open()

    def _get_gstreamer_pipeline(self) -> str:
        return (
            "udpsrc port=9000 ! "
            "application/x-rtp, media=(string)video, clock-rate=(int)90000, "
            "encoding-name=(string)H264, payload=(int)96 ! "
            "rtph264depay ! "
            "avdec_h264 ! "
            "videoconvert ! "
            "video/x-raw, format=(string)BGR ! "
            "appsink drop=true"
        )

    def _open(self) -> bool:
        if self.source_spec == "gstreamer":
            pipeline = self._get_gstreamer_pipeline()
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        else:
            try:
                source = int(self.source_spec)
            except ValueError:
                source = self.source_spec
            self.cap = cv2.VideoCapture(source)
        return self.cap.isOpened()

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.cap is None:
            return False, None
        return self.cap.read()

    def release(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None

    def get_fps(self) -> float:
        if self.cap is None:
            return 30.0
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        return fps if fps > 0 else 30.0

    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def reopen(self) -> bool:
        self.release()
        return self._open()


class PiCameraVideoSource(BaseVideoSource):
    """Video source using picamera2 for Raspberry Pi Camera."""

    def __init__(
        self,
        resolution: Tuple[int, int] = (1280, 720),
        framerate: int = 30,
        vflip: bool = False,
        hflip: bool = False,
        af_window: Optional[Tuple[float, float, float, float]] = None
    ):
        self.resolution = resolution
        self.framerate = framerate
        self.vflip = vflip
        self.hflip = hflip
        self.af_window = af_window  # Autofocus window in normalized coordinates (0.0-1.0)
        self.picam2 = None
        self._open()

    def _open(self) -> bool:
        try:
            from picamera2 import Picamera2
            from libcamera import Transform, controls

            self.picam2 = Picamera2()
            self.controls = controls

            transform = Transform(vflip=self.vflip, hflip=self.hflip)

            config = self.picam2.create_video_configuration(
                main={"size": self.resolution, "format": "RGB888"},
                transform=transform,
            )
            self.picam2.configure(config)
            self.picam2.start()

            # Ensure Continuous AF by default
            try:
                self.picam2.set_controls({'AfMode': self.controls.AfModeEnum.Continuous})
            except Exception as e:
                print(f"Warning: Could not set AfMode: {e}")

            # Apply AfWindows if specified
            if self.af_window:
                self.set_af_window(self.af_window)

            return True
        except ImportError as e:
            print(f"Error: picamera2 not available: {e}")
            return False
        except Exception as e:
            print(f"Error opening Pi Camera: {e}")
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.picam2 is None:
            return False, None
        try:
            frame = self.picam2.capture_array()
            return True, frame
        except Exception as e:
            print(f"Error reading from Pi Camera: {e}")
            return False, None

    def release(self) -> None:
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None

    def get_fps(self) -> float:
        return float(self.framerate)

    def is_opened(self) -> bool:
        return self.picam2 is not None

    def reopen(self) -> bool:
        self.release()
        return self._open()

    def set_af_window(self, window: Tuple[float, float, float, float]) -> bool:
        """
        Set autofocus window to tell camera where to focus.

        Args:
            window: (x, y, width, height) in normalized coordinates (0.0-1.0)

        Returns:
            bool: True if successful
        """
        if not self.picam2:
            return False

        try:
            x, y, w, h = window

            # Validate normalized coordinates
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and
                    0.0 <= w <= 1.0 and 0.0 <= h <= 1.0):
                print("Error: AfWindow coordinates must be normalized (0.0-1.0)")
                return False

            # Validate bounds
            if x + w > 1.0 or y + h > 1.0:
                print(f"Error: AfWindow out of bounds (x+w={x+w}, y+h={y+h})")
                # Clamp to valid bounds
                w = min(w, 1.0 - x)
                h = min(h, 1.0 - y)

            # Validate minimum size (at least 5% of frame)
            if w < 0.05 or h < 0.05:
                print("Error: AfWindow too small (min 0.05 or 5% of frame)")
                return False

            # Get sensor resolution for coordinate mapping
            try:
                # sensor_resolution is available in recent picamera2 versions
                # It returns (width, height) of the full sensor array
                sensor_w, sensor_h = self.picam2.sensor_resolution
            except Exception as e:
                print(f"Warning: Could not get sensor_resolution: {e}")
                # Fallback: try to guess from camera config or default to a reasonable high res
                # This is a safety fallback, usually sensor_resolution should be available
                sensor_w, sensor_h = 4608, 2592  # Default to IMX708 size as fallback

            # Calculate pixel coordinates
            # AfWindows expects coordinates relative to the full sensor array
            x_pix = int(x * sensor_w)
            y_pix = int(y * sensor_h)
            w_pix = int(w * sensor_w)
            h_pix = int(h * sensor_h)

            print(f"Setting AfWindow: Norm({x:.2f},{y:.2f},{w:.2f},{h:.2f}) -> "
                  f"Pix({x_pix},{y_pix},{w_pix},{h_pix}) on Sensor({sensor_w}x{sensor_h})")

            # Set window and trigger autofocus
            # Use Auto mode (One-shot) to force focus on the specific window
            controls = {
                'AfWindows': [(x_pix, y_pix, w_pix, h_pix)],
                'AfMode': self.controls.AfModeEnum.Auto,
                'AfTrigger': self.controls.AfTriggerEnum.Start
            }
            self.picam2.set_controls(controls)
            self.af_window = (x, y, w, h)
            return True
        except Exception as e:
            print(f"Error setting AfWindow: {e}")
            import traceback
            traceback.print_exc()
            return False

    def reset_af_window(self) -> bool:
        """Reset to default autofocus (full frame)."""
        if not self.picam2:
            return False

        try:
            # Get sensor resolution
            try:
                sensor_w, sensor_h = self.picam2.sensor_resolution
            except Exception:
                sensor_w, sensor_h = 4608, 2592

            # Reset to full frame and switch back to Continuous AF
            controls = {
                'AfWindows': [(0, 0, sensor_w, sensor_h)],
                'AfMode': self.controls.AfModeEnum.Continuous,
                'AfTrigger': self.controls.AfTriggerEnum.Cancel
            }
            self.picam2.set_controls(controls)
            self.af_window = None
            print("Reset to default autofocus (full frame, Continuous)")
            return True
        except Exception as e:
            print(f"Error resetting AfWindow: {e}")
            return False

    def get_af_window(self) -> Optional[Tuple[float, float, float, float]]:
        """Get current AfWindow setting."""
        return self.af_window
