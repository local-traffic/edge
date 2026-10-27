"""
Install system packages + venv (/opt/local-traffic/venv) and the run entry point, on a host or in the docker test image.
  host:   pyinfra pyinfra/inventory.py pyinfra/install_environment.py --limit rpi   (systemd service, enabled)
  docker: pyinfra pyinfra/inventory_docker.py pyinfra/install_environment.py -y     (commits local-traffic:test)
Recreate the venv from scratch with --data clean_venv=true.
"""
import os
import sys

from pyinfra import host

sys.path.insert(0, os.path.dirname(__file__))

from modules.common import check_system_requirements
from modules.deploy_args import APP_CODE_DIR
from tasks.deploy_tasks import (
    deploy_container_start_script,
    deploy_environment_file,
    deploy_systemd_service,
    install_system_packages,
    setup_virtualenv,
    upload_requirements,
)
from tasks.docker_image_tasks import commit_test_image, prepare_rpi_os_basics

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
is_docker_target = bool(host.data.get("is_docker_target", False))
ssh_user = host.data.get("ssh_user")

# the container runs as root, sudo is not installed yet when pyinfra gathers facts
should_use_sudo = not is_docker_target

if is_docker_target:
    prepare_rpi_os_basics(ssh_user)
else:
    check_system_requirements(APP_CODE_DIR)

install_system_packages(is_hailo_host=host.data.get("--model_type") == "hailo", should_use_sudo=should_use_sudo)
requirements_path = upload_requirements(
    os.path.join(project_root, "requirements-rpi.txt"), ssh_user, should_use_sudo=should_use_sudo
)
setup_virtualenv(
    requirements_path,
    should_recreate_venv=str(host.data.get("clean_venv", "")).lower() in ("1", "true", "yes"),
)
deploy_environment_file(host.data, should_use_sudo=should_use_sudo)

if is_docker_target:
    deploy_container_start_script(host.data)
    commit_test_image()
else:
    deploy_systemd_service(host.data)
