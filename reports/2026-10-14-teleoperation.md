# SO-101 teleoperation checkpoint — 2026-10-14

Status: functioning teleoperation confirmed by the operator; the full C2 acceptance gate remains incomplete.

## Completed

- Both USB controller identities were selected by the operator and their ports saved locally.
- Changing the hub port restored controller detection. No LeRobot port-discovery or driver change was needed.
- All twelve motors responded to read-only queries. Current motor calibration values differed from the Mac's older cached files, so the current values were recovered into the ignored `calibration/` directory and imported. Copies exactly matched the motor registers at recovery time; old files were preserved.
- An agent-run 20-second test at 10 Hz with `max_relative_target=1.0` exited normally. The operator reported uneven motion; elbow and wrist bend showed little movement with that limit.
- The operator subsequently reported that 2 was still ineffective for those joints, while **5 produced functioning teleoperation**. This is the observed working setting for this arm pair, not a universal SO-101 threshold.
- Read-only diagnostics found torque enabled and status registers equal to zero on all follower joints. These readings do not establish tracking accuracy or rule out mechanical issues.

## Settings to carry forward

- LeRobot 0.6.1; body joints in degrees; gripper in its normalized 0–100 range.
- Target control rate: 30 Hz. The operator's successful run was not independently instrumented for timing.
- `follower.max_relative_target`: 5.0. This caps target error relative to measured position, not velocity. A target does not advance farther while the measured joint remains stationary.
- `follower.disable_torque_on_disconnect`: false. Normal disconnect keeps the follower powered at the last target. Local emergency-stop and power-disconnect behavior still need a deliberate hardware test.
- Calibration and machine settings remain private local files. Copy `calibration/` when transferring the same arms to another computer; rediscover ports and camera indices.

## Next checkpoint

Identify overhead and wrist cameras; inspect their images and test simultaneous capture at 640×480, 30 fps for 60 seconds. Save the measured results before collecting short raise-arm demonstration episodes. No camera capture or dataset recording is established by this teleoperation report.

Remaining C2 checks include several corresponding poses and all six directions, measured tracking error, two minutes of supervised operation, deliberate stop behavior, and reconnecting without recalibration. Do not mark C2 complete solely from the successful teleoperation report.
