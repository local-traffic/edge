"""
Upload code to /opt/local-traffic/app, shared by the host service and the docker test container,
then restart whichever of them is running (a stopped one stays stopped).
Usage: pyinfra pyinfra/inventory.py pyinfra/upload_code.py --limit rpi
"""
import os
import sys

from pyinfra.operations import server

sys.path.insert(0, os.path.dirname(__file__))

from modules.deploy_args import SERVICE_NAME, TEST_CONTAINER_NAME
from tasks.code_upload_tasks import sync_code

sync_code()

server.shell(
    name=f"Restart {SERVICE_NAME} service if running",
    commands=[f"systemctl try-restart {SERVICE_NAME}"],
    _sudo=True,
)
server.shell(
    name=f"Restart {TEST_CONTAINER_NAME} container if running",
    commands=[
        "if command -v docker >/dev/null; then"
        f" docker ps -q --filter name=^{TEST_CONTAINER_NAME}$ | xargs -r docker restart; fi"
    ],
)
