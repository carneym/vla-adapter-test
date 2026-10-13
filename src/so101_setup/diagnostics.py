"""Read-only environment checks and a synthetic video round trip."""

import importlib.metadata
import platform
import shutil
import sys
import tempfile
from pathlib import Path

from .config import calibration_file, config_path, load_config


def inventory(root):
    packages = {}
    for name in ("lerobot", "torch", "torchvision", "torchcodec", "av", "opencv-python-headless", "feetech-servo-sdk"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    result = {
        "scope": "software inventory; hardware readiness not verified",
        "system": platform.system(), "architecture": platform.machine(),
        "python": platform.python_version(), "python_executable": sys.executable,
        "packages": packages,
        "commands": {name: shutil.which(name) for name in ("lerobot-find-port", "lerobot-find-cameras", "lerobot-calibrate", "lerobot-teleoperate", "lerobot-record")},
        "configuration": str(config_path(root)), "hardware_pending": [],
    }
    try:
        config = load_config(root)
        for role in ("leader", "follower"):
            if not config[role].get("port"):
                result["hardware_pending"].append(f"{role} port not selected")
            try:
                calibration_file(root, config, role)
            except (ValueError, OSError) as error:
                result["hardware_pending"].append(str(error))
        for camera in config["cameras"]:
            if camera.get("device") is None:
                result["hardware_pending"].append(f"{camera['name']} camera not selected")
    except (ValueError, OSError) as error:
        result["hardware_pending"].append(str(error))
    return result


def software_check():
    # Imports and synthetic data only: never instantiate a robot or camera.
    import av
    import cv2
    import numpy as np
    import scservo_sdk  # noqa: F401
    import torch
    from lerobot.datasets.video_utils import decode_video_frames
    from lerobot.robots.so_follower import SO101FollowerConfig
    from lerobot.teleoperators.so_leader import SO101LeaderConfig

    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("This lockfile targets Apple Silicon Macs; Modal uses a separate environment.")
    if sys.version_info[:2] != (3, 12) or importlib.metadata.version("lerobot") != "0.6.1":
        raise ValueError("Use the pinned project environment: uv sync --locked")
    # Constructing config dataclasses does not connect hardware.
    SO101FollowerConfig(port="/dev/unused")
    SO101LeaderConfig(port="/dev/unused")
    torch.ones(2, 3).sum().item()
    cv2.resize(np.zeros((32, 32, 3), dtype=np.uint8), (16, 16))
    with tempfile.TemporaryDirectory(prefix="so101-video-") as directory:
        path = Path(directory) / "test.mp4"
        with av.open(str(path), mode="w") as container:
            stream = container.add_stream("libx264", rate=10)
            stream.width = stream.height = 32
            stream.pix_fmt = "yuv420p"
            for index in range(3):
                frame = av.VideoFrame.from_ndarray(np.full((32, 32, 3), index * 60, dtype=np.uint8), format="rgb24")
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        frames = decode_video_frames(path, [0.0, 0.1, 0.2], tolerance_s=0.02, backend="pyav")
        if tuple(frames.shape) != (3, 3, 32, 32) or not torch.isfinite(frames).all():
            raise ValueError("Synthetic video round trip failed.")
        means = frames.mean(dim=(1, 2, 3))
        if not (means[0] < means[1] < means[2]):
            raise ValueError("Decoded video frame order is incorrect.")
    return {
        "passed": True,
        "checks": ["SO-101 config imports", "Feetech SDK import", "CPU tensor operation", "OpenCV resize", "H.264 encode and LeRobot PyAV decode"],
        "video_backend_tested": "pyav",
        "mps_available": torch.backends.mps.is_available(),
        "hardware_verified": False,
    }


def calibration_candidates():
    root = Path.home() / ".cache/huggingface/lerobot/calibration"
    # Search only the known LeRobot calibration directory, never other home data.
    return [str(path) for path in sorted(root.glob("*/*/*.json"))]
