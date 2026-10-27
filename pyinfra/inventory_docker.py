import os

# pyinfra starts a clean debian:trixie container on the Pi over SSH, install_environment.py turns it into local-traffic:test
rpi_hostname = os.environ.get("RPI_HOST", "rpi")
rpi_user = os.environ.get("RPI_USER", "pi")

container_tests = [
    (
        f"@dockerssh/{rpi_hostname}:debian:trixie",
        {
            "is_docker_target": True,
            "ssh_user": rpi_user,
            "location": "docker fresh-install test",
            "--source": "picamera",
            "--model_type": "hailo",
            "--model_path": "./yolov8n.hef",
            "--web_stream": "",
            "--web_port": 9090,
            "--hflip": "",
            "--vflip": "",
            "--zone_config": "zones.yaml",
        },
    ),
]
