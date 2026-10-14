"""Repository-local LeRobot setup. No subcommand starts motor movement."""

import argparse
import json
import sys

from .commands import teleop_command
from .config import configure, import_calibration, initialize, load_config, project_root
from .diagnostics import calibration_candidates, inventory, software_check


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create local settings without overwriting existing settings")
    init.add_argument("--machine", choices=("macbook", "mac-mini"), default="macbook")
    doctor = commands.add_parser("doctor", help="Inspect software and pending configuration; no hardware access")
    doctor.add_argument("--check", action="store_true", help="Also run imports and a synthetic video test")
    doctor.add_argument("--json", action="store_true")
    commands.add_parser("ports", help="List serial devices without opening them")
    commands.add_parser("calibrations", help="List existing LeRobot calibration files without changing them")
    cameras = commands.add_parser("camera-check", help="Open both configured cameras, save previews, and measure capture; no arm access")
    cameras.add_argument("--duration", type=float, default=60.0)
    imported = commands.add_parser("calibration-import", help="Copy a chosen calibration into ignored local storage")
    imported.add_argument("--role", choices=("leader", "follower"), required=True)
    imported.add_argument("--source", required=True)
    imported.add_argument("--id", dest="arm_id", help="Default: preserve the source file's stem as the arm ID")
    settings = commands.add_parser("configure", help="Save this machine's serial ports and camera indices")
    settings.add_argument("--leader-port")
    settings.add_argument("--follower-port")
    settings.add_argument("--overhead-camera", type=int)
    settings.add_argument("--wrist-camera", type=int)
    command = commands.add_parser("teleop-command", help="Print a LeRobot command for review; never execute it")
    command.add_argument("--without-cameras", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = project_root()
        if args.command == "init":
            path, created = initialize(root, args.machine)
            print(f"{'Created' if created else 'Kept existing'} {path}")
            print("Next: uv run --locked so101 doctor --check")
        elif args.command == "doctor":
            result = inventory(root)
            if args.check:
                result["software_check"] = software_check()
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"{result['system']} {result['architecture']} | Python {result['python']}")
                for name, version in result["packages"].items():
                    print(f"  {name}: {version or 'missing'}")
                if args.check:
                    print("PASS: software imports and synthetic video round trip (PyAV).")
                    print(f"MPS available: {result['software_check']['mps_available']} (policy inference untested)")
                for item in result["hardware_pending"]:
                    print(f"PENDING: {item}")
                print("Arms and cameras have not been opened or verified by this command.")
        elif args.command == "ports":
            from serial.tools.list_ports import comports
            devices = sorted(comports(), key=lambda item: item.device)
            for item in devices:
                print(f"{item.device}\t{item.description}\tserial={item.serial_number or 'unknown'}")
            if not devices:
                print("No serial devices found. Connect a controller, then repeat.")
        elif args.command == "calibrations":
            paths = calibration_candidates()
            print("\n".join(paths) if paths else "No files in the standard LeRobot calibration directory.")
            print("Select the known working file for each physical arm; files are not selected automatically.")
        elif args.command == "camera-check":
            from .camera_check import camera_check
            result = camera_check(root, args.duration)
            return 0 if result["capture_check_passed"] else 1
        elif args.command == "calibration-import":
            print(import_calibration(root, args.role, args.source, args.arm_id))
            print("Original preserved. Imported file has the expected schema; physical calibration is unverified.")
        elif args.command == "configure":
            print(configure(root, args.leader_port, args.follower_port, args.overhead_camera, args.wrist_camera))
        elif args.command == "teleop-command":
            print(teleop_command(root, load_config(root), args.without_cameras))
            print("Printed only. Running this upstream command enables teleoperation; verify hardware first.", file=sys.stderr)
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
