"""
One-time RPi host setup: Docker for the fresh-install test container, Hailo kernel driver on the host
(the driver loads at boot when the Hailo board is present; reboot after the first install).
Usage: pyinfra pyinfra/inventory.py pyinfra/setup_host.py --limit rpi
"""
import os
import sys

from pyinfra import host
from pyinfra.operations import apt, server, systemd

sys.path.insert(0, os.path.dirname(__file__))

from tasks.deploy_tasks import HAILO_HOST_PACKAGES

is_hailo_host = host.data.get("--model_type") == "hailo"
hailo_packages = HAILO_HOST_PACKAGES if is_hailo_host else []

apt.packages(
    name="Install Docker and Hailo driver",
    packages=["docker.io", *hailo_packages],
    update=True,
    cache_time=3600,
    _sudo=True,
)

systemd.service(
    name="Enable Docker",
    service="docker",
    running=True,
    enabled=True,
    _sudo=True,
)

server.user(
    name="Allow deploy user to run Docker",
    user=host.data.get("ssh_user"),
    groups=["docker"],
    append=True,
    _sudo=True,
)
