"""Verify a recorded candidate and assemble the delivery package.

Nothing here trusts the recording harness. The candidate is probed as a binary,
frames are extracted for inspection, and the package is written only from what
the probe actually reports.

Usage: python scripts/demo/finalize.py artifacts/swiggy-demo/candidates/FINAL_CANDIDATE_1.webm
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FINAL = Path("artifacts/swiggy-demo/final")
APPROVED = FINAL / "onemove-swiggy-demo-FINAL-APPROVED.webm"
APPROVED_MP4 = FINAL / "onemove-swiggy-demo-FINAL-APPROVED.mp4"
FRAME_TIMES = [5, 20, 40, 60, 90, 120, 150, 180, 210]


def ff() -> str:
    return Path("C:/tmp/ffpath").read_text().strip()


def probe(path: Path) -> dict:
    out = subprocess.run([ff(), "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    res = re.search(r", (\d{3,5})x(\d{3,5})", out)
    seconds = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))
    return {
        "duration_seconds": round(seconds, 2),
        "duration_hms": f"{int(seconds // 60)}:{seconds % 60:05.2f}",
        "width": int(res.group(1)),
        "height": int(res.group(2)),
        "size_bytes": path.stat().st_size,
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    src = Path(sys.argv[1])
    if not src.is_file():
        raise SystemExit(f"candidate not found: {src}")

    info = probe(src)
    print(f"candidate ......... {src}")
    print(f"  duration ........ {info['duration_hms']}  ({info['duration_seconds']}s)")
    print(f"  resolution ...... {info['width']}x{info['height']}")
    print(f"  size ............ {info['size_bytes']:,} bytes")

    # Hard gates, checked against the binary rather than the test report.
    assert 180 <= info["duration_seconds"] <= 300, "duration outside 180-300s"
    assert (info["width"], info["height"]) == (1920, 1080), "not 1920x1080"
    assert info["size_bytes"] != 2_972_006, "this is the rejected 47s recording"
    assert abs(info["duration_seconds"] - 46.76) > 1, "this is the rejected 47s recording"

    FINAL.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, APPROVED)

    # H.264 transcode of the approved master; the master is preserved untouched.
    subprocess.run(
        [ff(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(APPROVED),
         "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", "-an", str(APPROVED_MP4)],
        check=True,
    )
    mp4 = probe(APPROVED_MP4)
    assert abs(mp4["duration_seconds"] - info["duration_seconds"]) < 1.0, "transcode drifted"

    frames = FINAL / "frames"
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir()
    times = FRAME_TIMES + [max(1, int(info["duration_seconds"]) - 5)]
    for t in times:
        subprocess.run(
            [ff(), "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", str(APPROVED),
             "-frames:v", "1", "-vf", "scale=1280:-1", str(frames / f"t{t:03d}.png"), "-y"],
            check=True,
        )

    wx = json.loads(Path("public/demo/bengaluru-traffic.json").read_text(encoding="utf-8"))
    base = json.loads(Path("public/demo/bengaluru-basemap.json").read_text(encoding="utf-8"))

    approved_sha = sha256(APPROVED)
    mp4_sha = sha256(APPROVED_MP4)

    (FINAL / "checksums.sha256").write_text(
        f"{approved_sha}  {APPROVED.name}\n{mp4_sha}  {APPROVED_MP4.name}\n",
        encoding="utf-8", newline="\n",
    )

    (FINAL / "metadata.json").write_text(json.dumps({
        "artifact": APPROVED.name,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": info["duration_seconds"],
        "resolution": f"{info['width']}x{info['height']}",
        "sha256": approved_sha,
        "mp4_sha256": mp4_sha,
        "network": {
            "zones": len(base["zones"]),
            "h3_resolution": 8,
            "evidence_class": "PUBLIC_GEOGRAPHIC",
            "source": "pilot_roads.osm.pbf",
            "bbox": base["bbox"],
        },
        "traffic": {
            "provider": wx["provider"],
            "evidence_class": wx["evidence_class"],
            "captured_at": wx["captured_at"],
            "corridors": [s["name"] for s in wx["segments"]],
        },
        "weather": {"provider": "Open-Meteo", "evidence_class": "PUBLIC_OFFICIAL"},
        "solver": "Google OR-Tools CP-SAT",
    }, indent=2), encoding="utf-8")

    print(f"\napproved .......... {APPROVED}")
    print(f"  sha256 .......... {approved_sha}")
    print(f"mp4 ............... {APPROVED_MP4}  ({mp4['size_bytes']:,} bytes)")
    print(f"  sha256 .......... {mp4_sha}")
    print(f"frames ............ {len(times)} written to {frames}")


if __name__ == "__main__":
    main()
