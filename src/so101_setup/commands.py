"""Build reviewable LeRobot commands; never execute them."""

import json
import shlex

from .config import calibration_file, port_identity, validate_id


def teleop_command(root, config, without_cameras=False):
    args = ["uv", "run", "--locked", "lerobot-teleoperate", "--fps=30"]
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
        args += [f"--robot.cameras={json.dumps(cameras)}", "--display_data=true"]
    return shlex.join(args)
