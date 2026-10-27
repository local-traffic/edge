"""
Full idempotent host deploy: environment, code, service running and answering on /metrics.
Stops and disables the pre-rename car-statistics service, its files are left in place.
Usage: pyinfra pyinfra/inventory.py pyinfra/deploy.py --limit rpi
"""
import os
import sys

from pyinfra import host, local
from pyinfra.facts.systemd import SystemdStatus
from pyinfra.operations import systemd

sys.path.insert(0, os.path.dirname(__file__))

from modules.deploy_args import SERVICE_NAME
from tasks.code_upload_tasks import sync_code
from tasks.deploy_tasks import wait_for_metrics

LEGACY_SERVICE_NAME = "car-statistics"

if f"{LEGACY_SERVICE_NAME}.service" in host.get_fact(SystemdStatus):
    systemd.service(
        name=f"Stop and disable legacy {LEGACY_SERVICE_NAME} service",
        service=LEGACY_SERVICE_NAME,
        running=False,
        enabled=False,
        _sudo=True,
    )

local.include("./install_environment.py")
sync_code()

systemd.service(
    name=f"Restart and enable {SERVICE_NAME} service",
    service=SERVICE_NAME,
    running=True,
    restarted=True,
    enabled=True,
    _sudo=True,
)
wait_for_metrics(host.data.get("--web_port", 9090))
