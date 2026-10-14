"""Measure simultaneous camera capture through the pinned LeRobot camera API."""

import json
import math
import time
from datetime import datetime, timezone

from .config import load_config


def camera_check(root, duration=60.0):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Camera check duration must be a finite positive number of seconds.")
    settings = load_config(root)["cameras"]
    if len(settings) != 2 or {c["name"] for c in settings} != {"overhead", "wrist"}:
        raise ValueError("Configure exactly one overhead and one wrist camera.")
    for c in settings:
        if type(c.get("device")) is not int or c["device"] < 0:
            raise ValueError(f"Configure the {c['name']} camera index first.")
        for field in ("capture_width", "capture_height", "fps"):
            if type(c.get(field)) is not int or c[field] <= 0:
                raise ValueError(f"Configure a positive {field} for {c['name']}.")
    if settings[0]["device"] == settings[1]["device"]:
        raise ValueError("The two cameras must have different device indices.")

    from PIL import Image
    from lerobot.cameras.opencv import OpenCVCamera, OpenCVCameraConfig

    now = datetime.now(timezone.utc)
    output = root / ".cache" / "camera-check" / now.strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True)
    report = {
        "started_at": now.isoformat(),
        "requested_duration_s": duration,
        "measurement": "Distinct LeRobot host frame timestamps; not sensor timestamps or a hardware drop count.",
        "completed": False,
        "cameras": {},
    }
    cameras, timestamps, frames = {}, {}, {}
    start = None
    try:
        for c in settings:
            name = c["name"]
            print(f"Opening {name}, index {c['device']}, {c['capture_width']}x{c['capture_height']} at {c['fps']} fps...", flush=True)
            camera = OpenCVCamera(OpenCVCameraConfig(
                index_or_path=c["device"], width=c["capture_width"], height=c["capture_height"],
                fps=c["fps"], warmup_s=2,
            ))
            cameras[name] = camera
            timestamps[name] = []
            report["cameras"][name] = {"index": c["device"], "requested_fps": c["fps"]}
            camera.connect()

        start = time.perf_counter()
        next_progress = start + 15
        while time.perf_counter() - start < duration:
            for name, camera in cameras.items():
                if camera.thread is None or not camera.thread.is_alive():
                    raise RuntimeError(f"{name} capture thread stopped.")
                with camera.frame_lock:
                    stamp, frame = camera.latest_timestamp, camera.latest_frame
                if stamp is None or frame is None or time.perf_counter() - stamp > 2:
                    raise RuntimeError(f"{name} has no fresh frame within two seconds.")
                seen = timestamps[name]
                if stamp >= start and (not seen or stamp > seen[-1]):
                    seen.append(stamp)
                    frames[name] = frame
                    if len(seen) == 1:
                        Image.fromarray(frame).save(output / f"{name}-first.jpg")
            current = time.perf_counter()
            if current >= next_progress:
                counts = ", ".join(f"{name}: {len(ts)} fresh frames" for name, ts in timestamps.items())
                print(f"{current - start:.0f}s: {counts}", flush=True)
                next_progress += 15
            time.sleep(0.002)
        report["completed"] = True
    except BaseException as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        end = time.perf_counter()
        report["measured_duration_s"] = end - start if start is not None else 0
        for name, camera in cameras.items():
            try:
                if camera.is_connected or camera.thread is not None:
                    camera.disconnect()
            except Exception as error:
                report["completed"] = False
                report.setdefault("cleanup_errors", {})[name] = str(error)
        for name, ts in timestamps.items():
            gaps = [b - a for a, b in zip(ts, ts[1:])]
            # Include the edges so a startup or final capture stall cannot disappear from the report.
            all_gaps = ([ts[0] - start, *gaps, end - ts[-1]] if ts and start is not None else [report["measured_duration_s"]])
            summary = report["cameras"][name]
            summary.update(
                fresh_frames=len(ts),
                measured_fps=(len(ts) - 1) / (ts[-1] - ts[0]) if len(ts) > 1 else 0,
                max_observed_gap_ms=max(all_gaps) * 1000,
                frame_times_s=[t - start for t in ts] if start is not None else [],
            )
            if name in frames:
                frame = frames[name]
                summary["frame_shape"] = list(frame.shape)
                Image.fromarray(frame).save(output / f"{name}-last.jpg")
        report["capture_check_passed"] = report["completed"] and len(report["cameras"]) == 2 and all(
            c.get("measured_fps", 0) >= 0.95 * c["requested_fps"] and c.get("max_observed_gap_ms", math.inf) <= 200
            for c in report["cameras"].values()
        )
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"Camera report and previews: {output}", flush=True)
    for name, c in report["cameras"].items():
        print(f"{name}: {c['measured_fps']:.2f} fps, largest observed gap {c['max_observed_gap_ms']:.1f} ms")
    print("PASS: capture timing; review image framing separately." if report["capture_check_passed"] else "CHECK: capture timing did not meet the checkpoint thresholds.")
    return report
