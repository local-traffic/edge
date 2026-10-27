"""
Upload code + test videos to the rpi, run the whole pytest suite there with the host's detector, restore the app.
The service / test container is stopped during the run (it holds /dev/hailo0) and started again only if it was running.
The pytest log lands in test_results/rpi_pytest.log on the PC; the run fails when tests fail.
Usage: pyinfra pyinfra/inventory.py pyinfra/run_tests.py --limit rpi -y
Override the model with --data test_model_type=hailo --data test_model_path=./yolov8n.hef
"""
import os
import sys
from pathlib import Path

from pyinfra import host
from pyinfra.facts.server import Command
from pyinfra.operations import files, pip, server

sys.path.insert(0, os.path.dirname(__file__))

from modules.deploy_args import APP_CODE_DIR, APP_VENV_PATH, SERVICE_NAME, TEST_CONTAINER_NAME
from tasks.code_upload_tasks import project_root, sync_code
from tasks.deploy_tasks import wait_for_metrics

TEST_HOST_NAME = "rpi"
TEST_VIDEOS_DIR = Path(project_root) / "test_videos"
REMOTE_PYTEST_LOG_PATH = "/tmp/local_traffic_pytest.log"
LOCAL_PYTEST_LOG_PATH = Path(project_root) / "test_results" / f"{TEST_HOST_NAME}_pytest.log"
PYTEST_EXIT_CODE_PREFIX = "pytest exit code:"


def find_test_video_file_names():
    videos_with_zone_configs = [
        video_path for video_path in TEST_VIDEOS_DIR.iterdir()
        if video_path.suffix != ".yaml" and video_path.with_suffix(".zones.yaml").exists()
    ]
    return sorted(
        file_name
        for video_path in videos_with_zone_configs
        for file_name in (video_path.name, video_path.with_suffix(".zones.yaml").name)
    )


def sync_test_videos():
    include_flags = [f"--include='{file_name}'" for file_name in find_test_video_file_names()]
    files.rsync(
        name="Sync test videos with their zone configs",
        src=f"{TEST_VIDEOS_DIR}/",
        dest=f"{APP_CODE_DIR}/test_videos/",
        flags=["-azP", *include_flags, "--exclude='*'"],
    )


def is_service_running():
    return host.get_fact(Command, command=f"systemctl is-active {SERVICE_NAME} || true") == "active"


def is_test_container_running():
    container_ids = host.get_fact(
        Command,
        command=f"command -v docker >/dev/null && docker ps -q --filter name=^{TEST_CONTAINER_NAME}$ || true",
    )
    return bool(container_ids)


def stop_hailo_users(was_service_running, was_container_running):
    if was_service_running:
        server.shell(name=f"Stop {SERVICE_NAME} service", commands=[f"systemctl stop {SERVICE_NAME}"], _sudo=True)
    if was_container_running:
        server.shell(name=f"Stop {TEST_CONTAINER_NAME} container", commands=[f"docker stop {TEST_CONTAINER_NAME}"])


def run_pytest(model_type, model_path):
    pytest_command = (
        f"cd {APP_CODE_DIR} && {APP_VENV_PATH}/bin/python -m pytest -v -p no:cacheprovider"
        f" --model_type {model_type} --model_path {model_path}"
    )
    # never fails here, so the app is restored before the exit code is checked
    server.shell(
        name=f"Run pytest with {model_type} {model_path}",
        commands=[f"{pytest_command} > {REMOTE_PYTEST_LOG_PATH} 2>&1; "
                  f"echo \"{PYTEST_EXIT_CODE_PREFIX} $?\" >> {REMOTE_PYTEST_LOG_PATH}"],
    )
    files.get(name="Download pytest log", src=REMOTE_PYTEST_LOG_PATH, dest=str(LOCAL_PYTEST_LOG_PATH))


def restore_hailo_users(was_service_running, was_container_running):
    if was_service_running:
        web_port = host.data.get("--web_port", 9090)
        server.shell(name=f"Start {SERVICE_NAME} service", commands=[f"systemctl start {SERVICE_NAME}"], _sudo=True)
        wait_for_metrics(web_port)
    if was_container_running:
        server.shell(
            name=f"Start {TEST_CONTAINER_NAME} container",
            commands=[
                f"docker start {TEST_CONTAINER_NAME}",
                f"sleep 5 && docker inspect -f '{{{{.State.Running}}}}' {TEST_CONTAINER_NAME} | grep -q true",
            ],
        )


if host.name == TEST_HOST_NAME:
    LOCAL_PYTEST_LOG_PATH.parent.mkdir(exist_ok=True)
    was_service_running = is_service_running()
    was_container_running = is_test_container_running()

    sync_code()
    sync_test_videos()
    pip.packages(name="Install pytest into the venv", packages=["pytest"], virtualenv=APP_VENV_PATH)

    stop_hailo_users(was_service_running, was_container_running)
    run_pytest(
        model_type=host.data.get("test_model_type", host.data.get("--model_type")),
        model_path=host.data.get("test_model_path", host.data.get("--model_path")),
    )
    restore_hailo_users(was_service_running, was_container_running)

    server.shell(
        name=f"Fail if tests failed, see {LOCAL_PYTEST_LOG_PATH}",
        commands=[f"tail -n 1 {REMOTE_PYTEST_LOG_PATH} | grep -qx '{PYTEST_EXIT_CODE_PREFIX} 0'"],
    )
