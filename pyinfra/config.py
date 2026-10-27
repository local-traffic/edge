"""
Pyinfra global configuration settings

This file configures how pyinfra behaves during deployments.
Settings here apply to all operations across all hosts.

Key Settings:
    - PARALLEL: Number of hosts to process simultaneously (default: 5)
    - CONNECT_TIMEOUT: SSH connection timeout in seconds
    - FAIL_PERCENT: If set, allows some hosts to fail without stopping deployment
    - SUDO: Whether to use sudo by default (we use explicit _sudo=True in operations)

Documentation: https://docs.pyinfra.com/en/latest/api/reference.html#pyinfra.api.config
"""

from pyinfra import config

# Connection settings
config.SUDO = False
config.USE_SUDO_PASSWORD = False
config.CONNECT_TIMEOUT = 30

# Execution settings
config.PARALLEL = 5
config.FAIL_PERCENT = None  # Fail if any host fails

# Output settings
config.VERBOSE = False
config.QUIET = False

# SSH settings
config.SSH_STRICT_HOST_KEY_CHECKING = False
config.SSH_PARAMIKO_CONNECT_KWARGS = {
    "allow_agent": True,
    "look_for_keys": True,
}
