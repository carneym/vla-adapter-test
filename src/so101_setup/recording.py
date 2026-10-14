"""Explicitly start a recording only when the operator invokes record-test."""

import os
import shlex
import sys
import time

from .commands import record_arguments


def record_test(root, config, setup_seconds=15, dry_run=False):
    if type(setup_seconds) is not int or setup_seconds < 0:
        raise ValueError("Setup time must be a nonnegative whole number of seconds.")
    args = record_arguments(root, config)
    destination = next(a.split("=", 1)[1] for a in args if a.startswith("--dataset.root="))
    argv = [sys.executable, "-m", "lerobot.scripts.lerobot_record", *args]
    print(f"New recording: {destination}", flush=True)
    print("One 15-second raise-arm episode; both cameras; uploads disabled.", flush=True)
    if dry_run:
        print(f"Dry run: would wait {setup_seconds}s before connecting. No devices opened.")
        print(shlex.join(argv))
        return
    print("Stop other camera/arm processes. Match the leader to the follower's current pose.", flush=True)
    print("Ctrl+C cancels setup. After connection, wait for 'Recording episode 0', then raise and hold.", flush=True)
    try:
        for remaining in range(setup_seconds, 0, -1):
            if remaining % 5 == 0 or remaining <= 3 or remaining == setup_seconds:
                print(f"Connecting in {remaining} seconds...", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Setup cancelled. No devices were opened.", flush=True)
        return
    print("Connecting cameras and arms; camera warmup can take several seconds...", flush=True)
    # Replace this process so LeRobot stays in the foreground and receives terminal controls directly.
    # No shell or eval; paths, task text and camera JSON remain distinct arguments.
    os.execv(sys.executable, argv)
