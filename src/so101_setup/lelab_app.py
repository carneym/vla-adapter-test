"""Project settings adapter for the pinned LeLab collection UI.

Only this launcher installs the adapters; neither installed environment is edited.
Importing this module does not import LeRobot or open devices.
"""

import argparse
import json
import os
import sys
from functools import wraps
from pathlib import Path

from .commands import _hardware_arguments
from .config import CAMERA_WARMUP_S, calibration_file, load_config, port_identity, project_root

PROFILE_NAME = "SO101"


def camera_profile(config):
    return [
        {
            "id": camera["name"], "name": camera["name"], "type": "opencv",
            # Browser device IDs are origin-specific; a macOS USB ID is not one.
            "device_id": "",
            "camera_index": camera["device"], "width": camera["capture_width"],
            "height": camera["capture_height"], "fps": camera["fps"], "rotation": 0,
        }
        for camera in config["cameras"]
    ]


def configure_paths(root, config):
    # Constants in LeRobot are frozen at import time. Set these before any LeRobot import.
    os.environ["HF_LEROBOT_HOME"] = str(root / "data" / "lelab")
    os.environ["HF_LEROBOT_CALIBRATION"] = str(root / ".cache" / "lelab" / "calibration")
    from lelab.utils import config as paths

    state = root / ".cache" / "lelab" / "state"
    paths.CALIBRATION_BASE_PATH_TELEOP = str(state / "calibration" / "teleoperators")
    paths.CALIBRATION_BASE_PATH_ROBOTS = str(state / "calibration" / "robots")
    paths.PORT_CONFIG_PATH = str(state / "ports")
    paths.CONFIG_STORAGE_PATH = str(state / "saved_configs")
    paths.ROBOTS_PATH = str(state / "robots")
    profile = {}
    for role in ("leader", "follower"):
        calibration = calibration_file(root, config, role)
        setattr(paths, f"{role.upper()}_CONFIG_PATH", str(calibration.parent))
        setattr(paths, f"{role.upper()}_PORT_FILE", str(state / "ports" / f"{role}_port.txt"))
        setattr(paths, f"{role.upper()}_CONFIG_FILE", str(state / "saved_configs" / f"{role}_config.txt"))
        paths.save_robot_port(role, config[role]["port"])
        paths.save_robot_config(role, calibration.name)
        profile[f"{role}_port"] = config[role]["port"]
        profile[f"{role}_config"] = calibration.name
    # Ports/calibration follow machine-local settings each launch. Preserve GUI camera edits
    # unless the source machine settings changed (e.g. USB indices on another Mac).
    source = camera_profile(config)
    previous = state / "camera-source.json"
    if not paths.get_robot_record(PROFILE_NAME) or not previous.exists() or json.loads(previous.read_text()) != source:
        profile["cameras"] = source
    paths.save_robot_record(PROFILE_NAME, profile)
    previous.write_text(json.dumps(source, indent=2) + "\n")
    return paths.get_robot_record(PROFILE_NAME)


def apply_arm_settings(cfg, root, config, role):
    arm = config[role]
    if cfg.id != arm["id"] or port_identity(cfg.port) != port_identity(arm["port"]):
        raise ValueError(f"Select the {PROFILE_NAME} profile. Update {role} settings with so101 configure first.")
    cfg.calibration_dir = calibration_file(root, config, role).parent
    cfg.use_degrees = True
    if role == "follower":
        cfg.max_relative_target = float(arm.get("max_relative_target", 5.0))
        cfg.disable_torque_on_disconnect = arm.get("disable_torque_on_disconnect", False)
        for camera in cfg.cameras.values():
            camera.warmup_s = CAMERA_WARMUP_S
    return cfg


def reuse_motor_calibration(bus):
    """LeLab normally writes calibration on every connect. Verify our saved pair instead.

    Our follower holds torque on disconnect, so LeLab's assumption that torque is
    already disabled before those writes does not hold. Matching calibration needs
    no register writes; a mismatch needs explicit calibration outside collection.
    """
    def verify(calibration, cache=True):
        actual = bus.read_calibration()
        if actual != calibration:
            raise ValueError("Motor calibration differs from the saved file. Check/import calibration before collecting.")
        if cache:
            bus.calibration = calibration

    bus.write_calibration = verify


def install_adapters(root, config):
    import lerobot.robots.so_follower as followers
    import lerobot.teleoperators.so_leader as leaders

    # Both LeLab teleop and LeRobot's recording factories resolve these exports.
    # Keeping the original classes' names/properties preserves robot/dataset type IDs.
    def configured_device(original, role):
        @wraps(original)
        def create(cfg):
            device = original(apply_arm_settings(cfg, root, config, role))
            reuse_motor_calibration(device.bus)
            return device
        return create

    # v0.6.0 aliases SO100 and SO101 config classes; its registry can resolve either
    # type name when constructing the same SO101-configured pair.
    followers.SO100Follower = followers.SO101Follower = configured_device(followers.SO101Follower, "follower")
    leaders.SO100Leader = leaders.SO101Leader = configured_device(leaders.SO101Leader, "leader")

    from lelab import record, teleoperate

    # Also apply settings to generated configs, before any device construction.
    for module in (record, teleoperate):
        for role, attr in (("follower", "SO101FollowerConfig"), ("leader", "SO101LeaderConfig")):
            original = getattr(module, attr)

            def configured_config(*args, _original=original, _role=role, **kwargs):
                return apply_arm_settings(_original(*args, **kwargs), root, config, _role)

            setattr(module, attr, configured_config)

    upstream_create = record.create_record_config

    @wraps(upstream_create)
    def create_record_config(request):
        cfg = upstream_create(request)
        cfg.dataset.encoder_threads = 2
        cfg.dataset.encoder_queue_maxsize = 30
        cfg.dataset.rgb_encoder.vcodec = "h264"
        cfg.dataset.rgb_encoder.preset = "veryfast"
        cfg.dataset.rgb_encoder.crf = 23
        cfg.dataset.rgb_encoder.g = cfg.dataset.fps
        return cfg

    record.create_record_config = create_record_config

    from lelab import train

    upstream_training_command = train.build_training_command

    @wraps(upstream_training_command)
    def build_training_command(request, output_dir, python_executable="python", job_target=None):
        cmd = upstream_training_command(request, output_dir, python_executable, job_target)
        # The pinned LeRobot default detects TorchCodec's package, but does not
        # verify that its FFmpeg dylibs load on macOS. PyAV reads our H.264 files
        # without that system-library dependency. Cloud runners keep their default.
        if sys.platform == "darwin" and (job_target is None or job_target.runner == "local"):
            cmd.extend(["--dataset.video_backend", "pyav"])
        return cmd

    train.build_training_command = build_training_command


def prepare(root):
    root = Path(root).resolve()
    config = load_config(root)
    _hardware_arguments(root, config)  # Validate files and values; no device access.
    profile = configure_paths(root, config)
    install_adapters(root, config)
    return profile


def main(argv=None):
    parser = argparse.ArgumentParser(description="LeLab with this project's saved SO101 settings")
    parser.add_argument("--check", action="store_true", help="Validate config generation without opening devices or a server")
    parser.add_argument("--no-open", action="store_true", help="Do not open the system browser")
    args = parser.parse_args(argv)
    root = project_root()
    profile = prepare(root)
    if args.check:
        from lelab.record import RecordingRequest, create_record_config

        cfg = create_record_config(RecordingRequest(
            **{k: profile[k] for k in ("leader_port", "follower_port", "leader_config", "follower_config")},
            cameras={c["name"]: c for c in profile["cameras"]},
            dataset_repo_id="local/config-check", single_task="Raise your arm.",
            num_episodes=5, episode_time_s=15, reset_time_s=30,
        ))
        print(json.dumps({
            "profile": PROFILE_NAME, "devices_opened": False,
            "dataset_root": str(cfg.dataset.root), "episodes": cfg.dataset.num_episodes,
            "reset_seconds": cfg.dataset.reset_time_s,
            "max_relative_target": cfg.robot.max_relative_target,
            "use_degrees": [cfg.robot.use_degrees, cfg.teleop.use_degrees],
            "disable_torque_on_disconnect": cfg.robot.disable_torque_on_disconnect,
            "camera_warmup_seconds": {k: v.warmup_s for k, v in cfg.robot.cameras.items()},
            "video_codec": cfg.dataset.rgb_encoder.vcodec,
        }, indent=2))
        return
    from lelab.scripts.lelab import main as launch

    print(f"LeLab profile: {PROFILE_NAME}; datasets: {root / 'data' / 'lelab'}")
    print("The UI opens idle. Use its controls to start/stop teleoperation or recording.")
    launch(["--no-open"] if args.no_open else [])
