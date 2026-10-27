# Copy to pyinfra/inventory.py (gitignored) and fill in your hosts.
# Host data keys starting with "--" are passed to main.py, see modules/deploy_args.py

raspberry_pis = [
    (
        "rpi-1",
        {
            "--source": "picamera",
            "--model_type": "hailo",
            "--model_path": "./yolov8m.hef",
            "--web_stream": "",
            "--web_port": 9090,
            "--hflip": "",
            "--vflip": "",
            "--zone_config": "zones.yaml",
            "location": "example location",
        }
    ),
    (
        "rpi-2",
        {
            "--model_type": "hailo",
            "--model_path": "./yolov8n.hef",
            "--web_stream": "",
            "--web_port": 9090,
            "--zone_config": "zones.yaml",
            "location": "example location",
        }
    ),
]


all = (
    raspberry_pis,
    {
        "ssh_user": "pi",
        "global_version": "1.0.0"
    }
)
