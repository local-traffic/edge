import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

collect_ignore_glob = ["tests_technology/*", "ui/*"]


def pytest_addoption(parser):
    parser.addoption("--model_type", default="yolo", help="detector used by the video pipeline tests")
    parser.addoption("--model_path", default="yolov8n.pt", help="model file, relative to the repo root")
