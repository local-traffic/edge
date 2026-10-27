"""
Traffic Detection Application - Main Entry Point
Supports both PC and Raspberry Pi platforms.
- PC: Receives GStreamer streams, video files, or webcam
- RPi: Uses Pi Camera for direct capture, also supports video files
"""

import sys
import argparse

from backend.video_source import PiCameraVideoSource, OpenCVVideoSource
from backend.processing import RPiConfig, add_common_args, run_processing_loop


def parse_args():
    parser = argparse.ArgumentParser(
        description="Traffic Detection and Tracking Application",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Add common arguments with RPi defaults
    add_common_args(parser, RPiConfig())

    # Video source argument
    parser.add_argument(
        "--source", type=str, default="picamera",
        help="Video source: 'picamera' for Pi Camera, 'gstreamer' for GStreamer stream, path to video file, or webcam index (0,1)"
    )
    parser.add_argument(
        "--loop", action="store_true",
        help="Loop video file (only for file source)"
    )

    # RPi-specific arguments (camera)
    parser.add_argument(
        "--resolution", type=str, default="1280x720",
        help="Camera resolution WxH (only for picamera)"
    )
    parser.add_argument(
        "--framerate", type=int, default=15,
        help="Camera framerate (only for picamera)"
    )
    parser.add_argument(
        "--vflip", action="store_true",
        help="Flip video vertically (only for picamera)"
    )
    parser.add_argument(
        "--hflip", action="store_true",
        help="Flip video horizontally (only for picamera)"
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


def main():
    args = parse_args()

    # Setup video source based on --source argument
    if args.source == "picamera":
        # Use Pi Camera
        resolution = parse_resolution(args.resolution)
        video_source = PiCameraVideoSource(
            resolution=resolution,
            framerate=args.framerate,
            vflip=args.vflip,
            hflip=args.hflip
        )

        if not video_source.is_opened():
            print("Error: Could not open Pi Camera")
            print("Make sure picamera2 is installed and camera is enabled")
            sys.exit(1)

        print(f"Pi Camera opened: {resolution[0]}x{resolution[1]} @ {args.framerate}fps")
    else:
        # Use video file, GStreamer stream, or webcam via OpenCV
        video_source = OpenCVVideoSource(args.source)

        if not video_source.is_opened():
            print(f"Error: Could not open video source: {args.source}")
            sys.exit(1)

        print(f"Video source opened: {args.source}")

    # Build config from args
    config = RPiConfig.from_args(args)

    # Run processing
    run_processing_loop(video_source, config)


if __name__ == "__main__":
    main()
