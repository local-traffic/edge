"""
Environment install tasks shared by the host and the docker test image
"""

import os
from pyinfra import host
from pyinfra.operations import apt, files, pip, server, systemd

from modules.deploy_args import (
    APP_CODE_DIR,
    APP_CONFIG_DIR,
    APP_ENV_FILE_PATH,
    APP_ROOT_DIR,
    APP_VENV_PATH,
    CONTAINER_START_SCRIPT_PATH,
    SERVICE_NAME,
    build_cmd_args,
)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

# Prefer distro packages: they are prebuilt for the Pi's Python and built against the same numpy as hailo-all
SYSTEM_PYTHON_PACKAGES = [
    "python3-venv",
    "python3-numpy",
    "python3-opencv",
    "python3-picamera2",
    "python3-libcamera",
    "python3-pyaudio",
    "python3-psycopg2",
    "python3-yaml",
    "python3-dotenv",
    "python3-psutil",
    "python3-flask",
    "python3-flask-cors",
    "python3-shapely",
    "python3-scipy",
    "python3-matplotlib",
    "python3-pandas",
    "python3-sklearn",
    "python3-requests",
    "python3-pil",
    "python3-loguru",
    "python3-git",
    "python3-regex",
    "python3-torch",
    "python3-torchvision",
]

# Pulled in by ultralytics/boxmot via pip; they would shadow the GStreamer-enabled system cv2
PIP_OPENCV_WHEELS = ["opencv-python", "opencv-python-headless", "opencv-contrib-python"]


# kernel driver, installed on the host by setup_host.py
HAILO_HOST_PACKAGES = ["hailo-all"]
# hailo-all already contains these on the host; the container gets only them, hailo-dkms cannot build a kernel module there
HAILO_RUNTIME_PACKAGES = ["hailort", "python3-hailort"]


def install_system_packages(is_hailo_host, should_use_sudo):
    hailo_packages = HAILO_RUNTIME_PACKAGES if is_hailo_host else []
    apt.packages(
        name="Install system Python packages",
        packages=SYSTEM_PYTHON_PACKAGES + hailo_packages,
        update=True,
        cache_time=3600,
        _sudo=should_use_sudo,
    )


def upload_requirements(local_requirements_path, ssh_user, should_use_sudo):
    files.directory(
        name=f"Create {APP_ROOT_DIR}",
        path=APP_ROOT_DIR,
        present=True,
        user=ssh_user,
        group=ssh_user,
        _sudo=should_use_sudo,
    )
    files.put(
        name="Upload Python requirements",
        src=local_requirements_path,
        dest=f"{APP_ROOT_DIR}/requirements-rpi.txt",
    )
    return f"{APP_ROOT_DIR}/requirements-rpi.txt"


def setup_virtualenv(requirements_path, should_recreate_venv=False):
    if should_recreate_venv:
        files.directory(
            name="Remove existing virtual environment",
            path=APP_VENV_PATH,
            present=False,
        )

    pip.venv(
        name="Create virtual environment",
        path=APP_VENV_PATH,
        python="python3",
        site_packages=True,  # system numpy/opencv/picamera2/hailort come from apt
        present=True,
    )

    pip.packages(
        name="Upgrade pip",
        packages=["pip"],
        latest=True,
        virtualenv=APP_VENV_PATH,
    )

    pip.packages(
        name="Install Python dependencies",
        requirements=requirements_path,
        virtualenv=APP_VENV_PATH,
    )

    pip.packages(
        name="Remove pip OpenCV wheels (use system python3-opencv)",
        packages=PIP_OPENCV_WHEELS,
        present=False,
        virtualenv=APP_VENV_PATH,
    )


def deploy_environment_file(host_data, should_use_sudo):
    files.directory(
        name=f"Create {APP_CONFIG_DIR}",
        path=APP_CONFIG_DIR,
        present=True,
        user=host_data.get("ssh_user"),
        group=host_data.get("ssh_user"),
        mode="755",
        _sudo=should_use_sudo,
    )

    files.template(
        name="Deploy environment configuration",
        src=os.path.join(TEMPLATE_DIR, "env-file.j2"),
        dest=APP_ENV_FILE_PATH,
        user=host_data.get("ssh_user"),
        group=host_data.get("ssh_user"),
        mode="644",
        hostname=host.name,
        location=host_data.get("location"),
        _sudo=should_use_sudo,
    )


def deploy_systemd_service(host_data):
    files.template(
        name=f"Deploy systemd service: {SERVICE_NAME}",
        src=os.path.join(TEMPLATE_DIR, "systemd-service.j2"),
        dest=f"/etc/systemd/system/{SERVICE_NAME}.service",
        mode="644",
        ssh_user=host_data.get("ssh_user"),
        app_dir=APP_CODE_DIR,
        venv_path=APP_VENV_PATH,
        env_file_path=APP_ENV_FILE_PATH,
        cmd_args=build_cmd_args(host_data.dict()),
        _sudo=True,
    )

    systemd.daemon_reload(
        name="Reload systemd",
        _sudo=True,
    )

    # enabled for boot; starting is left to upload_code.py / the operator, the code may not be uploaded yet
    systemd.service(
        name=f"Enable {SERVICE_NAME} service",
        service=SERVICE_NAME,
        running=None,
        enabled=True,
        _sudo=True,
    )


def deploy_container_start_script(host_data):
    files.template(
        name="Deploy container start script",
        src=os.path.join(TEMPLATE_DIR, "container-start.sh.j2"),
        dest=CONTAINER_START_SCRIPT_PATH,
        mode="755",
        code_dir=APP_CODE_DIR,
        venv_path=APP_VENV_PATH,
        env_file_path=APP_ENV_FILE_PATH,
        cmd_args=build_cmd_args(host_data.dict()),
    )


def wait_for_metrics(web_port):
    server.shell(
        name=f"Wait for /metrics on port {web_port}",
        commands=[
            f"for attempt in $(seq 30); do curl -sf http://localhost:{web_port}/metrics >/dev/null && exit 0;"
            f" sleep 2; done; echo '{SERVICE_NAME} does not answer on port {web_port}'; exit 1"
        ],
    )
