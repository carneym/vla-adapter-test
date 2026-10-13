#!/usr/bin/env python3
"""Print a read-only computer inventory; never connect to robot hardware."""

import argparse
import importlib.metadata
import json
import platform
import shutil
import sys


def inventory():
    packages = {}
    for name in ("lerobot", "torch", "modal", "opencv-python-headless", "pyserial"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "scope": "computer inventory only; hardware readiness not verified",
        "system": platform.system(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "commands": {
            name: shutil.which(name)
            for name in ("git", "uv", "modal", "lerobot-find-port", "lerobot-calibrate")
        },
        "packages_in_this_python": packages,
        "next_step": "Run bash scripts/setup.sh macbook, then uv run --locked so101 doctor --check (see docs/SETUP.md).",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable inventory")
    args = parser.parse_args()
    result = inventory()
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print("SO-101 project: read-only computer inventory")
    print("Hardware readiness is NOT verified by this command.")
    print(f"System: {result['system']} / {result['architecture']}")
    print(f"Python: {result['python']} ({result['python_executable']})")
    for name, path in result["commands"].items():
        print(f"Command {name}: {path or 'not found'}")
    for name, version in result["packages_in_this_python"].items():
        print(f"Package {name}: {version or 'not installed in this Python'}")
    print(result["next_step"])


if __name__ == "__main__":
    main()
