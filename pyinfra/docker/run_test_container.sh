#!/usr/bin/env bash
# Usage from the PC: ssh rpi 'bash -s' -- [main.py args] < pyinfra/docker/run_test_container.sh
set -euo pipefail

TEST_IMAGE_TAG="${LOCAL_TRAFFIC_TEST_IMAGE:-local-traffic:test}"
TEST_HOST_PORT="${LOCAL_TRAFFIC_TEST_PORT:-9091}"
# code shared with the host service, same path inside the container, see APP_CODE_DIR in pyinfra/modules/deploy_args.py
APP_CODE_DIR="/opt/local-traffic/app"

if [ ! -f "$APP_CODE_DIR/main.py" ]; then
    echo "No code in $APP_CODE_DIR. Upload it first from the PC:" >&2
    echo "  pyinfra pyinfra/inventory.py pyinfra/upload_code.py --limit rpi -y" >&2
    exit 1
fi

if systemctl is-active --quiet local-traffic; then
    echo "local-traffic service is running and holds the camera and /dev/hailo0." >&2
    echo "Stop it first: sudo systemctl stop local-traffic" >&2
    exit 1
fi

HOST_HAILO_DRIVER_VERSION="$(cat /sys/module/hailo_pci/version 2>/dev/null || echo none)"
IMAGE_HAILORT_VERSION="$(docker run --rm "$TEST_IMAGE_TAG" dpkg-query -W -f='${Version}' hailort 2>/dev/null || echo none)"
if [[ "$IMAGE_HAILORT_VERSION" != "$HOST_HAILO_DRIVER_VERSION"* ]]; then
    echo "WARNING: host hailo_pci driver $HOST_HAILO_DRIVER_VERSION != image hailort $IMAGE_HAILORT_VERSION" >&2
fi

docker rm -f local-traffic-test >/dev/null 2>&1 || true
docker run -d --name local-traffic-test --privileged \
    -v /dev:/dev \
    -v /run/udev:/run/udev:ro \
    -v "$APP_CODE_DIR:$APP_CODE_DIR" \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e POSTGRES_CONNECTION_STRING= \
    -p "$TEST_HOST_PORT:9090" \
    "$TEST_IMAGE_TAG" local-traffic-start "$@"

echo "Web UI: http://$(hostname):$TEST_HOST_PORT  logs: docker logs -f local-traffic-test  stop: docker rm -f local-traffic-test"
