APP_ROOT_DIR = "/opt/local-traffic"
# Same path on the host and inside the docker test container; the container bind-mounts it
APP_CODE_DIR = f"{APP_ROOT_DIR}/app"
APP_VENV_PATH = f"{APP_ROOT_DIR}/venv"
APP_CONFIG_DIR = "/etc/local-traffic"
APP_ENV_FILE_PATH = f"{APP_CONFIG_DIR}/env"
SERVICE_NAME = "local-traffic"
TEST_CONTAINER_NAME = "local-traffic-test"
TEST_IMAGE_TAG = "local-traffic:test"
CONTAINER_START_SCRIPT_PATH = "/usr/local/bin/local-traffic-start"

CODE_EXCLUDE_PATTERNS = [
    "venv",
    "venv2",
    ".venv",
    ".mypy_cache",
    "__pycache__",
    ".git",
    "node_modules",
    "test_videos",
    "snapshots/*",
    "*.pyc",
    "*.pth",
    "*.pt",
    "*.mp4",
    "traffic_stats.db",
]


def build_rsync_exclude_flags():
    return [f"--exclude='{pattern}'" for pattern in CODE_EXCLUDE_PATTERNS]


def build_cmd_args(host_data):
    # every host data key starting with "--" is a main.py command line param
    return " ".join(f"{key} {value}".strip() for key, value in host_data.items() if key.startswith("--"))
