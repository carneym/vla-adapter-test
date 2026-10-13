# Simple calibration workflow

Command-line design specification; the guided command-line setup is not implemented yet. The aim is one guided setup per arm and a short readiness check at each session.

## First setup

Both arms are assembled and already moving in software. Inspect that working installation first and preserve any usable calibration. The steps below are needed only for missing or incompatible setup; do not repeat motor provisioning merely to adopt this project.

1. **Identify the arms.** Connect one controller at a time and label it leader or follower. Save device identity and the port, preferring stable identifiers where available. If the device cannot be identified reliably after reconnecting, ask the operator to identify it again.
2. **Check motor provisioning.** Confirm whether motor IDs and baud rates were configured during assembly. Only run provisioning when needed; it is different from calibration and requires the upstream one-motor-at-a-time procedure.
3. **Calibrate the follower.** Guide the user through LeRobot's reference pose and manual joint-range sweep with the official visual instructions alongside it.
4. **Calibrate the leader.** Repeat with a distinct, stable arm ID.
5. **Verify.** Compare corresponding poses, confirm gripper direction, then conduct a short supervised teleoperation check.
6. **Save and back up.** Retain the official calibration plus arm ID, motor inventory, software revision, units, and date. The application should locate the actual calibration path through the pinned LeRobot configuration rather than assume a cache location.

The current upstream entry points are `lerobot-find-port` and `lerobot-calibrate`. Calibration uses `--robot.type=so101_follower` for the follower and `--teleop.type=so101_leader` for the leader, each with its own port and stable ID. The implementation will generate the full commands from saved configuration instead of requiring the user to edit them repeatedly. [Official SO-101 instructions](https://huggingface.co/docs/lerobot/so101)

Calibration is physical: the operator still positions and moves the arm. The command-line prompts should explain each action, retain progress, identify which arm needs attention, and avoid automatic range sweeps.

## Daily startup

Connect the arms and cameras → confirm device identities and compatible calibration → preview cameras → check a known pose → enable the selected operating mode.

Do not redo motor provisioning or calibration as a daily step. Recalibrate if hardware/zero references change, a motor or linkage is replaced, stored calibration is incompatible, or pose verification fails. Recheck the scene/targets when the arm base or cameras move; that is separate from motor calibration.

Keep the same arm IDs for teleoperation, data collection, and inference. LeRobot associates calibration with those IDs. [Imitation-learning workflow](https://huggingface.co/docs/lerobot/il_robots)

## Keep three kinds of setup separate

| Setup | Purpose | When it changes |
| --- | --- | --- |
| Motor calibration | Consistent joint readings and commands | Motor/mechanical reference changes or failed verification |
| Camera/scene setup | Consistent visual input | Camera position/settings, base mounting, or workspace changes |
| Taught task positions | Home, raised arm, tissue presentation | User changes a target or arm base position |

For the initial image-and-joint policy, avoid requiring hand–eye calibration or a world-coordinate model unless a later feature needs them. A taught joint pose can express the fixed tissue presentation target while the base is fixed. It does not provide a portable Cartesian position if the base moves.

## Recovery behavior

Missing or mismatched calibration blocks motion and points to the affected arm. Device ambiguity blocks motion rather than swapping leader and follower. Never silently overwrite a working calibration. Back up the previous version and record why recalibration was performed.

Calibrated travel limits are not collision detection. Use a clamped base, clear working volume, conservative motion settings, and an accessible local stop/power disconnect during commissioning. Verify the stop behavior under the actual load before autonomous trials.
