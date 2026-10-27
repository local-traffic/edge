"""
Common utility functions for Car Statistics deployment
"""

import os
import time
import requests
from pyinfra import host
from pyinfra.facts.systemd import SystemdStatus
from pyinfra.facts.server import Command


def health_check(hostname, port=9090, retries=10, delay=3):
    url = f"http://{hostname}:{port}/metrics"

    for i in range(retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            if i < retries - 1:
                time.sleep(delay)

    return False


def check_service_status(service_name):
    # SystemdStatus returns a dict of {service_name: bool} indicating active status
    service_status = host.get_fact(SystemdStatus)
    return service_status.get(service_name, False)


def check_system_requirements(app_dir):
    results = {}

    # Check disk space using df command
    # awk '{print $5}' extracts the Use% column (e.g. 45%)
    cmd = f"df -h {os.path.dirname(app_dir)} | grep -v Filesystem | head -1 | awk '{{print $5}}'"
    disk_out = host.get_fact(Command, command=cmd, _sudo=False)

    if disk_out:
        disk_usage_str = disk_out.strip().replace('%', '')
        try:
            disk_usage = int(disk_usage_str)
            results["disk_usage"] = disk_usage

            if disk_usage > 95:
                raise Exception(f"Disk is critically full ({disk_usage}%). Free up space before deploying.")
            elif disk_usage > 85:
                print(f"⚠ Warning: Disk usage is {disk_usage}%")
        except ValueError:
            results["disk_usage"] = "unknown"

    # Check Python availability
    # Use 'which python3' to check if it's in the path
    python_check = host.get_fact(Command, command="which python3", _sudo=False)

    results["python_available"] = bool(python_check)

    if not python_check:
        raise Exception("Python 3 is not installed")

    return results
