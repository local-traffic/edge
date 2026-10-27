"""
Code upload tasks shared by upload_code.py and run_tests.py
"""

import os

from pyinfra import local
from pyinfra.operations import files, python

from modules.deploy_args import APP_CODE_DIR, build_rsync_exclude_flags

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def build_vue_app():
    local.shell(f"cd {project_root}/frontend && npm install && npm run build")


def sync_code():
    python.call(
        name="Build Vue app locally (once for all hosts)",
        function=build_vue_app,
        _run_once=True,
    )

    # zones are edited on the device through the web UI, so they are only seeded, never overwritten
    files.rsync(
        name=f"Sync code to {APP_CODE_DIR}",
        src=f"{project_root}/",
        dest=APP_CODE_DIR,
        flags=["-azrP", *build_rsync_exclude_flags(), "--exclude='zones*.yaml'"],
    )
    files.rsync(
        name="Seed zone configs missing on the device",
        src=f"{project_root}/",
        dest=APP_CODE_DIR,
        flags=["-azP", "--ignore-existing", "--include='zones*.yaml'", "--exclude='*'"],
    )
