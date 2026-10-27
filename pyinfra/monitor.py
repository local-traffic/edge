"""
Fleet monitoring script for Car Statistics

Monitor health and status of deployed devices with detailed reporting.

Usage Examples:
    # Monitor all devices
    pyinfra inventory.py monitor.py



    # Monitor specific device
    pyinfra rpi monitor.py

What Gets Checked:
    - Service status (active/inactive)
    - Health check (HTTP /metrics endpoint)
    - System metrics (CPU, memory, disk, temperature)
    - Application metrics (from /metrics API)
    - Recent logs (last 10 lines)

Output:
    - Console report for each device
    - Detailed JSON report file: monitor-report-{hostname}-{timestamp}.json
    - Alerts for unhealthy devices

Use Cases:
    - Regular health checks
    - Pre/post deployment verification
    - Troubleshooting
    - Fleet status overview
"""

import os
import sys
import json
import requests
from typing import Dict, Any
from datetime import datetime
from pyinfra import host
from pyinfra.facts.systemd import SystemdStatus
from pyinfra.facts.server import Command

# Add modules to path
sys.path.insert(0, os.path.dirname(__file__))

from modules.common import health_check  # noqa: E402
from modules.deploy_args import APP_CODE_DIR, SERVICE_NAME  # noqa: E402

# Get configuration
service_name = host.data.get("service_name", SERVICE_NAME)
web_port = host.data.get("web_port", 9090)

# Storage for monitoring results
monitoring_data: Dict[str, Any] = {}

print(f"\n{'='*60}")
print(f"Monitoring: {host.name}")
print(f"Location: {host.data.get('location', 'unknown')}")
print(f"{'='*60}\n")

# ===== STEP 1: Check service status =====
print(f"[{host.name}] Checking service status...")

# Check service status using native SystemdStatus fact
service_status_data = host.get_fact(SystemdStatus)
service_active = service_status_data.get(service_name, False)

# Get detailed service info using Command fact
# Mimicking "systemctl show {service_name} -p ActiveState -p SubState --no-pager"
service_info_cmd = f"systemctl show {service_name} -p ActiveState -p SubState --no-pager"
service_info_output = host.get_fact(Command, command=service_info_cmd, _sudo=True)
service_details = service_info_output.split('\n') if service_info_output else ["ActiveState=unknown"]

monitoring_data["service_active"] = service_active
monitoring_data["service_details"] = service_details

# ===== STEP 2: Health check =====
print(f"[{host.name}] Running health check...")

health_status = health_check(host.name, web_port, retries=3, delay=2)
monitoring_data["health_check"] = "PASS" if health_status else "FAIL"

# ===== STEP 3: Get system metrics =====
print(f"[{host.name}] Collecting system metrics...")


# Helper to execute command and return stripped output or default
def get_fact_output(cmd, default="N/A"):
    out = host.get_fact(Command, command=cmd)
    return out.strip() if out else default


app_dir = APP_CODE_DIR

# CPU usage
# Attempt to parse top output to get idle time and subtract from 100
# Example line: %Cpu(s):  0.3 us,  0.3 sy,  0.0 ni, 99.3 id, ...
cpu_cmd = "top -bn1 | grep 'Cpu(s)'"
cpu_out = get_fact_output(cpu_cmd, default="")
cpu_percent = "N/A"
if cpu_out:
    try:
        # Simple parsing logic
        # Split by comma, find 'id', take the number before it
        parts = cpu_out.split(',')
        for part in parts:
            if "id" in part:
                # part might be " 99.3 id"
                idle_val = float(part.strip().split()[0])
                cpu_percent = f"{100.0 - idle_val:.1f}"
                break
    except Exception:
        pass

# Memory usage
# free | grep Mem -> Mem:   Total   Used   Free ...
# awk '{print $3/$2 * 100.0}'
mem_cmd = "free | grep Mem | awk '{print $3/$2 * 100.0}'"
mem_out = get_fact_output(mem_cmd, default="")
mem_percent = f"{float(mem_out):.0f}" if mem_out else "N/A"

# Disk usage
# df -h {app_dir} -> ...
# awk '{print $5}' gets the percentage column
disk_cmd = f"df -h {app_dir} | grep -v Filesystem | head -1 | awk '{{print $5}}'"
disk_percent = get_fact_output(disk_cmd)

# Temperature (Raspberry Pi specific)
temp_cmd = "vcgencmd measure_temp 2>/dev/null"
temp_out = get_fact_output(temp_cmd, default="")
# Expected: "temp=42.0'C"
temp_val = temp_out.split('=')[1] if "=" in temp_out else "N/A"

# Uptime
uptime_cmd = "uptime -p"
uptime_val = get_fact_output(uptime_cmd, default="unknown")

# Format system metrics list
system_metrics = [
    f"CPU: {cpu_percent}%",
    f"Memory: {mem_percent}%",
    f"Disk: {disk_percent}",
    f"Temperature: {temp_val}",
    f"Uptime: {uptime_val}"
]

monitoring_data["system_metrics"] = system_metrics

# ===== STEP 4: Get application metrics =====
if health_status:
    print(f"[{host.name}] Fetching application metrics...")

    try:
        url = f"http://{host.name}:{web_port}/metrics"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            app_metrics = response.json()
            monitoring_data["app_metrics"] = app_metrics
        else:
            monitoring_data["app_metrics"] = {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        monitoring_data["app_metrics"] = {"error": str(e)}
else:
    monitoring_data["app_metrics"] = {"error": "Service not healthy"}

# ===== STEP 5: Get recent logs =====
print(f"[{host.name}] Retrieving recent logs...")

logs_cmd = f"journalctl -u {service_name} -n 10 --no-pager"
logs_output = host.get_fact(Command, command=logs_cmd, _sudo=True)
recent_logs = logs_output.split('\n') if logs_output else []

monitoring_data["recent_logs"] = recent_logs

# ===== Display Results =====
print(f"\n{'='*60}")
print(f"Monitoring Report: {host.name}")
print(f"{'='*60}")
print(f"Location: {host.data.get('location', 'unknown')}")
print(f"Zone Config: {host.data.get('zone_config', 'zones.yaml')}")
print("\nService Status:")
print(f"  Active: {monitoring_data['service_active']}")
print(f"  Health Check: {monitoring_data['health_check']}")

print("\nSystem Metrics:")
for metric in monitoring_data.get("system_metrics", []):
    print(f"  {metric}")

# Fixed the logic error here: removed 'not' to properly print dict items
if monitoring_data.get("app_metrics") and isinstance(monitoring_data["app_metrics"], dict):
    print("\nApplication Metrics:")
    for key, value in monitoring_data.get("app_metrics", {}).items():
        if key != "timestamp":
            print(f"  {key}: {value}")

print("\nRecent Logs (last 10 lines):")
for log_line in monitoring_data.get("recent_logs", [])[:10]:
    print(f"  {log_line[:100]}")  # Truncate long lines

print(f"{'='*60}\n")

