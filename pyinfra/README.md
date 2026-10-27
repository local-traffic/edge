# Pyinfra Deployment for Local Traffic

Three steps, each its own pyinfra script (or `deploy.py` for all of them after host setup), run from the project root on the PC:

| Script | What it does | When |
|---|---|---|
| `setup_host.py` | Docker, Hailo kernel driver (`hailo-all`), deploy user in the `docker` group | once per Pi |
| `install_environment.py` | apt packages (as much as possible from Raspberry Pi OS), venv in `/opt/local-traffic/venv`, `/etc/local-traffic/env`; on a host also the systemd unit, in docker the `local-traffic:test` image | once, and when `requirements-rpi.txt` / `SYSTEM_PYTHON_PACKAGES` change |
| `upload_code.py` | builds the Vue app locally, rsyncs code to `/opt/local-traffic/app`, restarts the service / test container if running | every code change |
| `deploy.py` | all-in-one, idempotent: stops + disables the old `car-statistics` service, runs `install_environment.py`, uploads the code, (re)starts and enables `local-traffic`, fails unless `/metrics` answers | any time on a host |
| `run_tests.py` | uploads code + `test_videos/*` that have a `<video>.zones.yaml`, stops the service / test container, runs pytest with the host's detector (Hailo), restores what was running, log in `test_results/rpi_pytest.log` | after changes, `rpi` only |

The code dir is shared: the host service runs it directly, the docker test container bind-mounts the same path.
The venv lives outside it at the same path on the host and in the image, so uploading code never touches it.

## Prerequisites

- pyinfra on the PC (`uv add pyinfra` / `pip install pyinfra requests`), `npm` for the frontend build
- SSH key access to the Pis (`ssh-copy-id <user>@<rpi-host>`)
- `cp pyinfra/inventory.example.py pyinfra/inventory.py` and fill in your hosts, `ssh_user` and their `main.py` args (`inventory.py` is gitignored)
- Raspberry Pi OS Trixie on the Pi

## Production on the host

```bash
pyinfra pyinfra/inventory.py pyinfra/setup_host.py --limit rpi
pyinfra pyinfra/inventory.py pyinfra/install_environment.py --limit rpi            # --data clean_venv=true for a fresh venv
pyinfra pyinfra/inventory.py pyinfra/upload_code.py --limit rpi
ssh rpi 'sudo systemctl start local-traffic'                                     # first time only; later uploads restart it
```

Or after `setup_host.py`, everything else in one idempotent run:
```bash
pyinfra pyinfra/inventory.py pyinfra/deploy.py --limit rpi
```

Every inventory key starting with `--` becomes a `main.py` argument (systemd unit and container entry point alike).
Zone configs (`zones*.yaml`) are only copied when missing on the device, because they are edited there through the web UI.

## Fresh-install test in Docker (on the Pi)

`install_environment.py` against `inventory_docker.py` starts a clean `debian:trixie` container on the Pi (pyinfra
`@dockerssh` connector), turns it into a Raspberry Pi OS Lite lookalike (apt repos and keyrings copied from the Pi host, sudo, default user), runs the
same install as on the host and commits it as `local-traffic:test`. Host packages and the service are not touched.

### Step by step

1. **Host setup** (once per Pi; reboot after the first Hailo install so the driver loads):
   ```bash
   pyinfra pyinfra/inventory.py pyinfra/setup_host.py --limit rpi
   ssh rpi 'docker info --format "{{.ServerVersion}} {{.Architecture}}"'      # version + aarch64
   ```
   "permission denied" means the new `docker` group applies only from the next SSH login.

2. **Build the image** (environment install inside a container; again when dependencies change):
   ```bash
   pyinfra pyinfra/inventory_docker.py pyinfra/install_environment.py -y        # RPI_HOST=<rpi-host> RPI_USER=<user> pyinfra ...
   ssh rpi docker images                                                       # local-traffic:test must be listed
   ```

3. **Upload the code** (mounted into the container from `/opt/local-traffic/app`):
   ```bash
   pyinfra pyinfra/inventory.py pyinfra/upload_code.py --limit rpi
   ```

4. **Stop the host service**, it holds the camera and the Hailo chip (a missing unit is fine):
   ```bash
   ssh rpi 'sudo systemctl stop local-traffic'
   ```

5. **Start the container**:
   ```bash
   # Pi camera, main.py args from inventory_docker.py
   ssh rpi 'bash -s' < pyinfra/docker/run_test_container.sh

   # or a video copied to /opt/local-traffic/app/test_videos/ on the Pi
   ssh rpi 'bash -s' -- --source test_videos/test.avi --loop --model_type hailo --model_path ./yolov8n.hef \
       --web_stream --web_port 9090 < pyinfra/docker/run_test_container.sh
   ```

6. **Check it**: web UI http://rpi:9091
   ```bash
   ssh rpi docker logs -f local-traffic-test                  # Ctrl+C stops following, not the app
   ssh -t rpi docker exec -it local-traffic-test bash         # shell in the running container
   ```
   After a code change run step 3 again; it restarts the running container.

7. **Back to production**:
   ```bash
   ssh rpi 'docker rm -f local-traffic-test && sudo systemctl start local-traffic'
   ```

The container runs `--privileged` with `/dev` mounted (camera, `/dev/hailo0`, sound) and without
`POSTGRES_CONNECTION_STRING`, so test events stay out of the production database. It installs only `hailort` +
`python3-hailort`; the kernel driver comes from the host and the run script warns if their versions differ.
pyinfra's `docker.*` operations cannot build images or pass devices, hence the connector and the run script.

Checks:

```bash
# images/containers; the connector commits once more on its own, untagged: ssh rpi docker image prune -f
ssh rpi 'docker images; docker ps -a'

# if apt fails (the Pi host has the same repos): each line must show a Candidate version
ssh rpi "sh -c 'for p in python3-venv python3-numpy python3-opencv python3-picamera2 python3-libcamera python3-pyaudio python3-psycopg2 python3-yaml python3-dotenv python3-psutil python3-flask python3-flask-cors python3-shapely python3-scipy python3-matplotlib python3-pandas python3-sklearn python3-requests python3-pil python3-loguru python3-git python3-regex python3-torch python3-torchvision hailort python3-hailort; do printf \"%s \" \$p; apt-cache policy \$p | grep Candidate || echo MISSING; done'"

# hailort must not pull the kernel driver build into the container (expect no output)
ssh rpi "sh -c 'apt-cache depends --recurse hailort python3-hailort | grep -i dkms'"

# venv uses system numpy 2.x / GStreamer cv2 from /usr/lib/python3/dist-packages, no pip opencv
ssh rpi "docker run --rm local-traffic:test /opt/local-traffic/venv/bin/python -c 'import numpy, cv2, hailo_platform, ultralytics, boxmot, rfdetr; print(numpy.__version__, numpy.__file__, cv2.__file__)'"
ssh rpi "docker run --rm local-traffic:test /opt/local-traffic/venv/bin/pip list 2>/dev/null | grep -iE '^(numpy|opencv|torch) '"

# shell in the image
ssh -t rpi docker run --rm -it local-traffic:test bash
```

## Tests on the Pi

```bash
pyinfra pyinfra/inventory.py pyinfra/run_tests.py --limit rpi -y
pyinfra pyinfra/inventory.py pyinfra/run_tests.py --limit rpi -y --data test_model_path=./yolov8n.hef
```

The run fails when a test fails; the full pytest output is in `test_results/rpi_pytest.log`.

## Monitoring

```bash
pyinfra pyinfra/inventory.py pyinfra/monitor.py
```

Service status, health check (`/metrics`), system metrics, recent logs and a JSON report per device.

## Useful commands

```bash
pyinfra pyinfra/inventory.py pyinfra/install_environment.py --limit rpi --dry      # preview changes
pyinfra pyinfra/inventory.py exec --limit rpi -- sudo journalctl -u local-traffic -n 50
curl http://rpi:9090/metrics
```

## File structure

```
pyinfra/
├── inventory.py              # devices and their main.py args
├── inventory_docker.py       # docker test target (@dockerssh on the Pi)
├── config.py                 # pyinfra settings
├── setup_host.py             # 1. host setup
├── install_environment.py    # 2. packages + venv, host or docker image
├── upload_code.py            # 3. code upload + restart
├── monitor.py                # fleet status
├── docker/run_test_container.sh
├── modules/
│   ├── common.py             # health check, preflight
│   └── deploy_args.py        # shared paths, rsync excludes, main.py args
├── tasks/
│   ├── deploy_tasks.py       # apt, venv, env file, systemd unit, container entry point
│   └── docker_image_tasks.py # RPi OS lookalike + image commit
└── templates/
```
