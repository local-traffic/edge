import cv2
import threading
import time
import os
from collections import deque
from datetime import datetime

class VideoRingBuffer:
    """
    Maintains a ring buffer of the last N seconds of video frames.
    """
    def __init__(self, buffer_duration=5.0, fps=30):
        self.maxlen = int(buffer_duration * fps)
        self.buffer = deque(maxlen=self.maxlen)
        self.fps = fps

    def add_frame(self, frame):
        """Add a frame to the buffer."""
        self.buffer.append(frame)

    def get_all(self):
        """Return all frames currently in the buffer."""
        return list(self.buffer)


class EventVideoWriter:
    """
    Writes video events to disk in a separate thread.
    Handles pre-event buffering and post-event duration.
    """
    def __init__(self, output_dir="recordings", fps=30, max_duration=None):
        self.output_dir = output_dir
        self.fps = fps
        self.max_duration = max_duration
        self.resolution = None
        os.makedirs(output_dir, exist_ok=True)
        
        self.is_recording = False
        self.writer = None
        self.queue = deque()  # Queue for frames to be written
        self.lock = threading.Lock()
        self.running = True
        
        # Start worker thread
        self.thread = threading.Thread(target=self._write_loop, daemon=True)
        self.thread.start()

    def save_video(self, pre_event_buffer, filename_prefix):
        """
        Write what is in the ring buffer to wideo file
        Args:
            pre_event_buffer: List of frames from the ring buffer.
        """
        with self.lock:
            if not self.is_recording:
                h, w = pre_event_buffer[0].shape[:2]
                self.resolution = (w, h)
                self._create_writer(filename_prefix)

                self.is_recording = True
                # Add pre-event frames immediately
                for frame in pre_event_buffer:
                    self.queue.append(frame)

    def _create_writer(self, filename_prefix):
        if self.writer is not None:
            return

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Using .avi with XVID is generally safer/more compatible on Linux 
        # without strict codec deps, but user might prefer mp4.
        # Let's try XVID first as it's very robust for OpenCV.
        filename = f"{filename_prefix}_{ts}.avi"
        filepath = os.path.join(self.output_dir, filename)
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        # If user strictly needs mp4:
        # filename = f"event_{ts}.mp4"
        # fourcc = cv2.VideoWriter_fourcc(*'mp4v') # or 'avc1'
        
        self.writer = cv2.VideoWriter(
            filepath, fourcc, self.fps, self.resolution
        )
        if not self.writer.isOpened():
            print(f"Error: Failed to create video writer for {filepath}")
            self.writer = None
        else:
            print(f"[VideoWriter] Started writing to: {filename} ({self.resolution})")


    def _write_loop(self):
        """Worker thread loop."""
        while self.running:
            frame = None
            writer_to_close = None
            
            with self.lock:
                if self.queue:
                    frame = self.queue.popleft()
                    # Ensure writer exists if queue has frames (edge case)
                    if not self.writer and self.resolution:
                        self._create_writer()
                elif not self.is_recording and self.writer:
                    # Queue is empty and we are done recording -> close writer
                    writer_to_close = self.writer
                    self.writer = None
            
            if frame is not None and self.writer:
                self.writer.write(frame)
            
            if writer_to_close:
                writer_to_close.release()
                print("[VideoWriter] File closed and saved.")

            if frame is None:
                time.sleep(0.01)

    def stop(self):
        """Clean shutdown."""
        self.running = False
        self.thread.join()
        if self.writer:
            self.writer.release()
