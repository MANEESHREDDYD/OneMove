"""GCP Safety Guard for ZonePilot infrastructure commands."""

import shutil
import subprocess
import sys


def verify_active_project() -> str:
    """Verifies that the active gcloud project starts with 'zonepilot-' and rejects signit-502902."""
    gcloud_bin = shutil.which("gcloud") or "gcloud.cmd" if sys.platform == "win32" else "gcloud"
    res = subprocess.run(
        [gcloud_bin, "config", "get-value", "project"],
        capture_output=True,
        text=True,
        check=True,
        shell=sys.platform == "win32",
    )
    project = res.stdout.strip()
    if not project:
        raise RuntimeError("SAFETY ABORT: No active GCP project configured.")

    if project in {"signit-502902", "project-2040fcfb-596f-42ba-9c9"}:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Protected external project '{project}' is active. Aborting."
        )

    if not project.startswith("zonepilot-"):
        raise RuntimeError(
            f"SAFETY ABORT: Active project '{project}' does not start with 'zonepilot-'."
        )

    return project


if __name__ == "__main__":
    try:
        active = verify_active_project()
        print(f"GCP Safety Guard PASS: Verified active project '{active}'.")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
