"""
Docker test image tasks: make a clean debian:trixie container look like a fresh Raspberry Pi OS Lite,
then commit it as the test image. Container ops run as root without sudo: facts are gathered with
the op's _sudo before sudo is installed.
"""

from pyinfra import host
from pyinfra.api import StringCommand
from pyinfra.operations import apt, python, server

from modules.deploy_args import TEST_IMAGE_TAG

# the Pi host is Raspberry Pi OS Trixie: reuse its repo config and current keyrings
# (the old raspberrypi.gpg.key download has SHA1 self-signatures, rejected by Trixie apt since 2026-02-01)
HOST_APT_CONFIG_PATHS = ["etc/apt/sources.list.d", "etc/apt/preferences.d", "usr/share/keyrings"]


def _copy_host_apt_config(rpi_ssh, container_id):
    host_apt_config_copy = (
        f"tar -C / -cf - {' '.join(HOST_APT_CONFIG_PATHS)} | docker exec -i {container_id} tar -C / -xf -"
    )
    is_copied, copy_output = rpi_ssh.run_shell_command(StringCommand(host_apt_config_copy))
    if not is_copied:
        raise Exception(f"Copying host apt config failed: {copy_output.stderr}")


def prepare_rpi_os_basics(ssh_user):
    apt.packages(
        name="Install RPi OS Lite basics",
        packages=["ca-certificates", "sudo", "python3"],
        update=True,
    )
    python.call(
        name="Copy Raspberry Pi apt repos and keyrings from the host",
        function=_copy_host_apt_config,
        rpi_ssh=host.connector.ssh,
        container_id=host.host_data["docker_container_id"],
    )
    apt.update(name="Refresh apt lists with Raspberry Pi repo")
    server.user(
        name="Create default RPi user",
        user=ssh_user,
        uid=1000,
        shell="/bin/bash",
        ensure_home=True,
    )


def _commit_container(rpi_ssh, container_id):
    is_committed, commit_output = rpi_ssh.run_shell_command(
        StringCommand("docker", "commit", container_id, TEST_IMAGE_TAG)
    )
    if not is_committed:
        raise Exception(f"docker commit failed: {commit_output.stderr}")


def commit_test_image():
    # the dockerssh connector commits again on disconnect, but untagged
    python.call(
        name=f"Commit container as {TEST_IMAGE_TAG}",
        function=_commit_container,
        rpi_ssh=host.connector.ssh,
        container_id=host.host_data["docker_container_id"],
    )
