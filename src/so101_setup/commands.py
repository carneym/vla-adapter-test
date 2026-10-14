"""Build reviewable LeRobot commands; never execute them."""

import json
import math
import shlex
from datetime import datetime, timezone

from .config import calibration_file, port_identity, validate_id


def _hardware_arguments(root, config, without_cameras=False):
    args = []
    ports = []
    for role, prefix in (("follower", "robot"), ("leader", "teleop")):
        arm = config[role]
        port = arm.get("port")
        if not isinstance(port, str) or not port.startswith("/dev/"):
            raise ValueError(f"Configure the {role} port first with so101 configure.")
        ports.append(port)
        calibration = calibration_file(root, config, role)
        args += [
            f"--{prefix}.type=so101_{role}",
            f"--{prefix}.port={port}",
            f"--{prefix}.id={validate_id(arm['id'])}",
            f"--{prefix}.calibration_dir={calibration.parent}",
            f"--{prefix}.use_degrees=true",
        ]
    if port_identity(ports[0]) == port_identity(ports[1]):
        raise ValueError("Leader and follower must use different ports.")
    # This is a cap relative to measured position, not a velocity limit.
    relative_target = config["follower"].get("max_relative_target", 5.0)
    if type(relative_target) not in (int, float) or not math.isfinite(relative_target) or relative_target <= 0:
        raise ValueError("Set follower.max_relative_target to a finite positive number.")
    release = config["follower"].get("disable_torque_on_disconnect", False)
    if type(release) is not bool:
        raise ValueError("Set follower.disable_torque_on_disconnect to true or false.")
    args += [
        f"--robot.max_relative_target={float(relative_target)}",
        f"--robot.disable_torque_on_disconnect={str(release).lower()}",
    ]
    if not without_cameras:
        cameras = {}
        for camera in config["cameras"]:
            index = camera.get("device")
            if type(index) is not int or index < 0:
                raise ValueError(f"Configure the {camera['name']} camera index or use --without-cameras.")
            for field in ("capture_width", "capture_height", "fps"):
                if type(camera.get(field)) is not int or camera[field] <= 0:
                    raise ValueError(f"Set a positive {field} for camera {camera['name']}.")
            cameras[camera["name"]] = {
                "type": "opencv", "index_or_path": index,
                "width": camera["capture_width"], "height": camera["capture_height"], "fps": camera["fps"],
            }
        if set(cameras) != {"overhead", "wrist"}:
            raise ValueError("Configure exactly the overhead and wrist camera views.")
        if cameras["overhead"]["index_or_path"] == cameras["wrist"]["index_or_path"]:
            raise ValueError("The two camera indices must be different.")
        args += [f"--robot.cameras={json.dumps(cameras)}"]
    return args


def teleop_command(root, config, without_cameras=False):
    args = ["uv", "run", "--locked", "lerobot-teleoperate", "--fps=30"]
    args += _hardware_arguments(root, config, without_cameras)
    if not without_cameras:
        args += ["--display_data=true"]
    return shlex.join(args)


def record_command(root, config, session=None):
    """Print one local commissioning episode, not an accepted training dataset."""
    session = validate_id(session or datetime.now(timezone.utc).strftime("raise-arm-smoke-%Y%m%dT%H%M%SZ"))
    destination = root / "data" / session
    if destination.exists():
        raise ValueError(f"Dataset already exists: {destination}. Choose another --session; existing data is preserved.")
    args = ["uv", "run", "--locked", "lerobot-record"]
    args += _hardware_arguments(root, config)
    args += [
        f"--dataset.repo_id=local/{session}",
        f"--dataset.root={destination}",
        "--dataset.no_stamp=true",
        "--dataset.single_task=Raise your arm.",
        "--dataset.fps=30",
        "--dataset.num_episodes=1",
        "--dataset.episode_time_s=15",
        "--dataset.reset_time_s=10",
        "--dataset.push_to_hub=false",
        "--dataset.private=true",
        "--dataset.video=true",
        "--dataset.streaming_encoding=true",
        "--dataset.encoder_threads=2",
        "--dataset.encoder_queue_maxsize=30",
        "--dataset.rgb_encoder.vcodec=h264",
        "--dataset.rgb_encoder.preset=veryfast",
        "--dataset.rgb_encoder.crf=23",
        "--dataset.rgb_encoder.g=30",
        "--resume=false",
        "--display_data=false",
        "--play_sounds=true",
    ]
    return shlex.join(args)
