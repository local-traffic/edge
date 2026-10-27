import cv2
import time
import sys
from video_utils import VideoRingBuffer, EventVideoWriter
from video_source import OpenCVVideoSource


def main():
    print("Initializing Stream...")
    video_source = OpenCVVideoSource("gstreamer")

    if not video_source.is_opened():
        print("Error: Could not open stream.")
        sys.exit(1)

    # Setup Buffer and Writer
    # Buffer 2 seconds, Record 5 seconds post-event
    buffer_duration = 2.0
    post_event_duration = 5.0
    
    ring_buffer = VideoRingBuffer(buffer_duration=buffer_duration, fps=30)
    video_writer = EventVideoWriter(output_dir="test_recordings")

    print(f"Stream opened. Filling buffer ({buffer_duration}s)...")
    
    start_time = time.time()
    triggered = False
    
    while True:
        ret, frame = video_source.read()
        if not ret:
            print("Stream ended.")
            break

        # 1. Add to buffer
        ring_buffer.add_frame(frame.copy())
        
        # 3. Simulate Event Trigger after 3 seconds
        if not triggered and (time.time() - start_time > 3.0):
            print(">>> TRIGGERING TEST RECORDING <<<")
            video_writer.start_recording(
                pre_event_buffer=ring_buffer.get_all(),
                post_event_duration=post_event_duration
            )
            triggered = True

        # Visualization
        display_frame = frame.copy()
        if video_writer.is_recording:
            cv2.circle(display_frame, (30, 30), 10, (0, 0, 255), -1)
            cv2.putText(display_frame, "REC", (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Check if finished
            if triggered and not video_writer.is_recording:
                # This logic is tricky because start_recording sets a time in the future.
                # video_writer.is_recording remains True until that time.
                pass
        
        elif triggered:
            print("Recording finished. Exiting...")
            break

        cv2.imshow("Test Recorder", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_writer.stop()
    video_source.release()
    cv2.destroyAllWindows()
    print("Done. Check 'test_recordings' folder.")


if __name__ == "__main__":
    main()
