#!/usr/bin/env python3
"""
Test script for PiCameraVideoSource on Raspberry Pi.
Run this to debug camera issues before running the full detection app.

Usage:
    python test_picamera.py                    # Basic test
    python test_picamera.py --show             # Show live video
    python test_picamera.py --save             # Save test frames
    python test_picamera.py --resolution 640x480 --framerate 30
    python test_picamera.py --vflip --hflip    # Flip camera
"""

import argparse
import time
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Test PiCameraVideoSource",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--resolution", type=str, default="1280x720",
        help="Camera resolution WxH"
    )
    parser.add_argument(
        "--framerate", type=int, default=15,
        help="Camera framerate"
    )
    parser.add_argument(
        "--vflip", action="store_true",
        help="Flip video vertically"
    )
    parser.add_argument(
        "--hflip", action="store_true",
        help="Flip video horizontally"
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Show live video window (requires display)"
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save test frames to disk"
    )
    parser.add_argument(
        "--frames", type=int, default=100,
        help="Number of frames to capture for test"
    )
    return parser.parse_args()


def parse_resolution(res_str: str) -> tuple:
    """Parse resolution string like '1280x720' to tuple."""
    try:
        w, h = res_str.lower().split('x')
        return (int(w), int(h))
    except ValueError:
        print(f"Invalid resolution format: {res_str}, using 1280x720")
        return (1280, 720)


def test_picamera2_import():
    """Test if picamera2 can be imported."""
    print("\n[1/6] Testing picamera2 import...")
    try:
        from picamera2 import Picamera2
        print("  OK: picamera2 imported successfully")
        return True
    except ImportError as e:
        print(f"  FAIL: Cannot import picamera2: {e}")
        print("  Fix: sudo apt install python3-picamera2")
        return False


def test_libcamera_import():
    """Test if libcamera can be imported."""
    print("\n[2/6] Testing libcamera import...")
    try:
        from libcamera import Transform
        print("  OK: libcamera imported successfully")
        return True
    except ImportError as e:
        print(f"  FAIL: Cannot import libcamera: {e}")
        print("  Fix: sudo apt install python3-libcamera")
        return False


def test_opencv_import():
    """Test if OpenCV can be imported."""
    print("\n[3/6] Testing OpenCV import...")
    try:
        import cv2
        print(f"  OK: OpenCV version {cv2.__version__}")
        return True
    except ImportError as e:
        print(f"  FAIL: Cannot import cv2: {e}")
        print("  Fix: sudo apt install python3-opencv")
        return False


def test_camera_detection():
    """Test if camera is detected by picamera2."""
    print("\n[4/6] Testing camera detection...")
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()

        # Get camera info
        camera_info = picam2.global_camera_info()
        if camera_info:
            print(f"  OK: Found {len(camera_info)} camera(s)")
            for i, cam in enumerate(camera_info):
                print(f"      Camera {i}: {cam}")
        else:
            print("  FAIL: No cameras detected")
            return False

        picam2.close()
        return True
    except Exception as e:
        print(f"  FAIL: Camera detection error: {e}")
        return False


def test_video_source(args):
    """Test PiCameraVideoSource class."""
    print("\n[5/6] Testing PiCameraVideoSource...")

    try:
        from video_source import PiCameraVideoSource
    except ImportError as e:
        print(f"  FAIL: Cannot import PiCameraVideoSource: {e}")
        return False

    resolution = parse_resolution(args.resolution)

    print(f"  Creating source: {resolution[0]}x{resolution[1]} @ {args.framerate}fps")
    print(f"  Flips: vflip={args.vflip}, hflip={args.hflip}")

    source = PiCameraVideoSource(
        resolution=resolution,
        framerate=args.framerate,
        vflip=args.vflip,
        hflip=args.hflip
    )

    if not source.is_opened():
        print("  FAIL: Could not open PiCameraVideoSource")
        return False

    print("  OK: PiCameraVideoSource opened")
    print(f"  Reported FPS: {source.get_fps()}")

    # Read a few frames
    print(f"  Reading {args.frames} frames...")

    import cv2

    frame_count = 0
    error_count = 0
    start_time = time.time()

    for i in range(args.frames):
        ret, frame = source.read()

        if not ret or frame is None:
            error_count += 1
            print(f"    Frame {i}: FAIL (ret={ret})")
            continue

        frame_count += 1

        # First frame info
        if frame_count == 1:
            print(f"  Frame shape: {frame.shape}")
            print(f"  Frame dtype: {frame.dtype}")

            if args.save:
                filename = "test_frame_first.jpg"
                cv2.imwrite(filename, frame)
                print(f"  Saved: {filename}")

        # Show live video if requested
        if args.show:
            # Add frame info overlay
            info_text = f"Frame {frame_count} | {frame.shape[1]}x{frame.shape[0]}"
            cv2.putText(frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("PiCamera Test", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("  User quit (pressed 'q')")
                break

    elapsed = time.time() - start_time
    actual_fps = frame_count / elapsed if elapsed > 0 else 0

    print(f"\n  Results:")
    print(f"    Frames captured: {frame_count}/{args.frames}")
    print(f"    Errors: {error_count}")
    print(f"    Time elapsed: {elapsed:.2f}s")
    print(f"    Actual FPS: {actual_fps:.1f}")

    # Save last frame
    if args.save and frame_count > 0:
        ret, frame = source.read()
        if ret and frame is not None:
            filename = "test_frame_last.jpg"
            cv2.imwrite(filename, frame)
            print(f"    Saved: {filename}")

    # Cleanup
    source.release()
    if args.show:
        cv2.destroyAllWindows()

    print("  OK: PiCameraVideoSource released")

    return error_count == 0


def test_reopen(args):
    """Test reopen functionality."""
    print("\n[6/6] Testing reopen functionality...")

    try:
        from video_source import PiCameraVideoSource
    except ImportError:
        print("  SKIP: Could not import PiCameraVideoSource")
        return True

    resolution = parse_resolution(args.resolution)

    source = PiCameraVideoSource(
        resolution=resolution,
        framerate=args.framerate,
        vflip=args.vflip,
        hflip=args.hflip
    )

    if not source.is_opened():
        print("  FAIL: Could not open source initially")
        return False

    # Read one frame
    ret, frame = source.read()
    if not ret:
        print("  FAIL: Could not read initial frame")
        source.release()
        return False

    print("  Initial open: OK")

    # Reopen
    if not source.reopen():
        print("  FAIL: reopen() returned False")
        return False

    if not source.is_opened():
        print("  FAIL: Source not opened after reopen")
        return False

    # Read frame after reopen
    ret, frame = source.read()
    if not ret:
        print("  FAIL: Could not read frame after reopen")
        source.release()
        return False

    print("  Reopen: OK")

    source.release()
    return True


def test_af_window(args):
    """Test autofocus window setting."""
    print("\n[7/6] Testing AfWindow...")

    try:
        from video_source import PiCameraVideoSource
    except ImportError:
        print("  SKIP: Could not import PiCameraVideoSource")
        return True

    resolution = parse_resolution(args.resolution)
    source = PiCameraVideoSource(
        resolution=resolution,
        framerate=args.framerate,
        vflip=args.vflip,
        hflip=args.hflip
    )

    if not source.is_opened():
        print("  FAIL: Could not open source")
        return False

    print("  Testing set_af_window (center 20%)...")
    # Center window: 20% width/height at center
    success = source.set_af_window((0.4, 0.4, 0.2, 0.2))

    if success:
        print("  OK: set_af_window returned True")
    else:
        print("  FAIL: set_af_window returned False")

    print("  Testing reset_af_window...")
    success_reset = source.reset_af_window()
    if success_reset:
        print("  OK: reset_af_window returned True")
    else:
        print("  FAIL: reset_af_window returned False")

    source.release()
    return success and success_reset


def main():
    args = parse_args()

    print("=" * 50)
    print("PiCameraVideoSource Test Script")
    print("=" * 50)

    results = []

    # Run tests
    results.append(("picamera2 import", test_picamera2_import()))
    results.append(("libcamera import", test_libcamera_import()))
    results.append(("OpenCV import", test_opencv_import()))

    # Only continue if imports succeeded
    if all(r[1] for r in results):
        results.append(("Camera detection", test_camera_detection()))

        if results[-1][1]:  # Camera detected
            results.append(("PiCameraVideoSource", test_video_source(args)))
            results.append(("Reopen", test_reopen(args)))
            results.append(("AfWindow", test_af_window(args)))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = 0
    failed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed > 0:
        print("\nTroubleshooting:")
        print("  1. Make sure camera is enabled: sudo raspi-config")
        print("  2. Check camera cable connection")
        print("  3. Install dependencies: sudo apt install python3-picamera2 python3-libcamera python3-opencv")
        print("  4. Reboot after enabling camera")
        sys.exit(1)
    else:
        print("\nAll tests passed! Camera is ready for use.")
        sys.exit(0)


if __name__ == "__main__":
    main()
