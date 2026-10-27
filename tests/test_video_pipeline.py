import shutil
from pathlib import Path

import pytest

from backend.events.event_manager import EventManager
from backend.processing import PCConfig, run_processing_loop
from backend.video_source import OpenCVVideoSource

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_VIDEOS_DIR = REPO_ROOT / "test_videos"

pytestmark = pytest.mark.slow


def find_zone_config_path(video_path):
    return video_path.with_suffix(".zones.yaml")


def find_videos_with_zone_configs():
    if not TEST_VIDEOS_DIR.is_dir():
        return []
    return sorted(
        video_path.name
        for video_path in TEST_VIDEOS_DIR.iterdir()
        if video_path.suffix != ".yaml" and find_zone_config_path(video_path).exists()
    )


@pytest.fixture
def pipeline_config(request):
    return PCConfig(
        model_type=request.config.getoption("--model_type"),
        model_path=str(REPO_ROOT / request.config.getoption("--model_path")),
        web_stream=False,
        audio_device_index=-1,
    )


def run_video_through_pipeline(video_name, pipeline_config, tmp_path, monkeypatch):
    video_path = TEST_VIDEOS_DIR / video_name
    zone_config_path = tmp_path / "zones.yaml"
    shutil.copy(find_zone_config_path(video_path), zone_config_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("POSTGRES_CONNECTION_STRING", raising=False)
    monkeypatch.setattr("backend.processing.load_dotenv", lambda: None)

    dispatched_events = []
    original_dispatch = EventManager.dispatch

    def record_dispatch(event_manager, event):
        dispatched_events.append(event)
        original_dispatch(event_manager, event)

    monkeypatch.setattr(EventManager, "dispatch", record_dispatch)

    pipeline_config.zone_config = str(zone_config_path)
    run_processing_loop(OpenCVVideoSource(str(video_path)), pipeline_config)
    return dispatched_events


@pytest.mark.parametrize("video_name", find_videos_with_zone_configs())
def test_pipeline_runs_video_without_frame_errors(video_name, pipeline_config, tmp_path, monkeypatch, capsys):
    run_video_through_pipeline(video_name, pipeline_config, tmp_path, monkeypatch)

    assert "Error processing frame" not in capsys.readouterr().out


@pytest.mark.parametrize("video_name", find_videos_with_zone_configs())
def test_line_crossings_are_dispatched_without_perspective_calibration(video_name, pipeline_config, tmp_path, monkeypatch):
    dispatched_events = run_video_through_pipeline(video_name, pipeline_config, tmp_path, monkeypatch)

    line_cross_events = [event for event in dispatched_events if event.event_type == "line_cross"]
    assert line_cross_events
    assert all(not event.speed_measurement.is_valid for event in line_cross_events)
