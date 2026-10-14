"""Machine settings and explicit, non-destructive calibration import."""

import json
import re
from pathlib import Path

JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
CAMERA_WARMUP_S = 5


def port_identity(port):
    # macOS exposes callout and tty aliases for the same physical serial device.
    return re.sub(r"^/dev/(cu|tty)\.", "/dev/", port)


def project_root(start=None):
    start = Path(start or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "configs/hardware.example.json").is_file():
            return candidate
    raise ValueError("Run this command inside the vla-adapter-test checkout.")


def config_path(root):
    return root / "configs/hardware.local.json"


def load_config(root):
    path = config_path(root)
    if not path.exists():
        raise ValueError("Local configuration is missing. Run: so101 init --machine macbook")
    config = json.loads(path.read_text())
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported hardware configuration schema.")
    return config


def save_config(root, config):
    path = config_path(root)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    temporary.replace(path)


def initialize(root, machine):
    path = config_path(root)
    if path.exists():
        return path, False
    config = json.loads((root / "configs/hardware.example.json").read_text())
    config["control_host"].update(
        machine="macbook-air-m2" if machine == "macbook" else "mac-mini-m4",
        memory_gb=8 if machine == "macbook" else 16,
        selection_status="selected",
    )
    with path.open("x") as file:
        json.dump(config, file, indent=2)
        file.write("\n")
    return path, True


def validate_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
        raise ValueError("Arm ID must be 1–64 letters, digits, dots, underscores, or hyphens; start with a letter/digit.")
    return value


def validate_calibration(data):
    if not isinstance(data, dict) or set(data) != set(JOINTS):
        raise ValueError("Calibration must contain exactly the six SO-101 joint names.")
    for expected_id, name in enumerate(JOINTS, start=1):
        entry = data[name]
        fields = ("id", "drive_mode", "homing_offset", "range_min", "range_max")
        if not isinstance(entry, dict) or any(type(entry.get(key)) is not int for key in fields):
            raise ValueError(f"Invalid integer calibration fields for {name}.")
        if entry["id"] != expected_id:
            raise ValueError(f"Unexpected motor ID for {name}; expected {expected_id}.")
        if entry["range_min"] >= entry["range_max"]:
            raise ValueError(f"Invalid travel range for {name}.")


def calibration_file(root, config, role):
    value = config[role].get("calibration_path")
    if not value:
        raise ValueError(f"No {role} calibration selected. Use so101 calibration-import.")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    if path.name != f"{validate_id(config[role]['id'])}.json":
        raise ValueError(f"{role} calibration filename must match its arm ID.")
    if not path.is_file():
        raise ValueError(f"Missing {role} calibration: {path}")
    validate_calibration(json.loads(path.read_text()))
    return path.resolve()


def import_calibration(root, role, source, arm_id=None):
    config = load_config(root)
    source = Path(source).expanduser().resolve()
    raw = source.read_bytes()
    validate_calibration(json.loads(raw))
    arm_id = validate_id(arm_id or source.stem)
    relative = Path("calibration") / role / f"{arm_id}.json"
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != raw:
            raise ValueError(f"Refusing to overwrite different calibration: {destination}")
    else:
        with destination.open("xb") as file:
            file.write(raw)
    config[role].update(id=arm_id, calibration_path=relative.as_posix())
    save_config(root, config)
    return destination


def configure(root, leader_port=None, follower_port=None, overhead_camera=None, wrist_camera=None):
    config = load_config(root)
    for role, port in (("leader", leader_port), ("follower", follower_port)):
        if port is not None:
            if not port.startswith("/dev/"):
                raise ValueError("Use the full macOS serial device path beginning with /dev/.")
            config[role]["port"] = port
    if config["leader"].get("port") and config["follower"].get("port") and port_identity(config["leader"]["port"]) == port_identity(config["follower"]["port"]):
        raise ValueError("Leader and follower must use different ports.")
    for camera in config["cameras"]:
        index = overhead_camera if camera["name"] == "overhead" else wrist_camera
        if index is not None:
            if index < 0:
                raise ValueError("Camera indices must be nonnegative.")
            camera.update(device=index, capture_width=640, capture_height=480, fps=30)
    indices = [c["device"] for c in config["cameras"] if c.get("device") is not None]
    if len(set(indices)) != len(indices):
        raise ValueError("Overhead and wrist cameras must use different device indices.")
    save_config(root, config)
    return config_path(root)
