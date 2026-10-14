# Portable LeRobot setup for Apple Silicon Macs

The MacBook Air M2 (8 GB) is the initial control machine. The same lockfile supports the Mac mini M4 (16 GB). This environment is for arm control and data collection; VLA-Adapter CUDA training remains separate on Modal.

## Install on either Mac

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed (`brew install uv` with Homebrew), then:

```sh
git clone https://github.com/carneym/vla-adapter-test.git
cd vla-adapter-test
bash scripts/setup.sh macbook
```

On the Mac mini, use `bash scripts/setup.sh mac-mini`. For an existing checkout, run the setup command in that checkout. The script creates `.venv`, installs the versions in `uv.lock`, initializes `configs/hardware.local.json`, and runs software checks. Repeating it preserves existing local configuration. It never opens serial ports or cameras or starts robot motion.

Python 3.12 is selected through `.python-version`; uv can download it if no suitable interpreter is present. LeRobot is pinned to **0.6.1**, with its `core_scripts` and `feetech` extras. PyTorch is pinned to **2.10.0**, torchvision to **0.25.0**, and TorchCodec to **0.10.0**. All transitive dependencies and distribution hashes are recorded in `uv.lock`. The supported target is **macOS arm64**, not Intel Macs, Windows, or the Modal training container. [LeRobot installation](https://huggingface.co/docs/lerobot/installation) · [Pinned release](https://github.com/huggingface/lerobot/tree/v0.6.1)

No model weights, training policy extras, Modal jobs, or credentials are needed for setup. Use `uv run --locked` for commands so a different active Python environment cannot accidentally supply robot dependencies.

## Checkpoint A — Software ready

```sh
uv run --locked so101 doctor --check
```

Pass: SO-101 configuration and motor SDK imports, a CPU tensor operation, OpenCV image processing, and a synthetic H.264 encode/LeRobot decode round trip. This does not test cameras, serial communication, calibration, or policy inference. Hardware settings may still be listed as `PENDING` while software checks pass.

The video check explicitly uses **PyAV**, whose wheel includes FFmpeg libraries. A system FFmpeg installation is not required for this tested path. TorchCodec is installed as a LeRobot dependency but its decoding path needs compatible system FFmpeg libraries; it is not covered by this check. Use `video_backend="pyav"` when loading datasets initially. In this release LeRobot also falls back to PyAV if TorchCodec cannot load. macOS may print duplicate FFmpeg Objective-C class warnings when OpenCV and PyAV load together; successful synthetic video checks do not establish camera capture readiness.

## Checkpoint B — Select the existing arms and calibration

List serial devices without opening them and list saved calibration candidates:

```sh
uv run --locked so101 ports
uv run --locked so101 calibrations
```

If arm identity is unclear, connect one controller at a time and repeat `ports`. Do not guess leader/follower from device order. Save the observed paths:

```sh
uv run --locked so101 configure \
  --leader-port=/dev/cu.YOUR_LEADER \
  --follower-port=/dev/cu.YOUR_FOLLOWER
```

Replace these placeholders with actual paths. Select the calibration file used by your existing working setup for each physical arm:

```sh
uv run --locked so101 calibration-import \
  --role leader --source /absolute/path/to/working_leader.json
uv run --locked so101 calibration-import \
  --role follower --source /absolute/path/to/working_follower.json
```

Import validates the six-joint schema, copies the file into `calibration/leader/` or `calibration/follower/`, and records a relative path. It preserves the filename stem as the arm ID and leaves the original untouched. An existing destination with different contents is never overwritten. Use `--id` only when intentionally assigning a new local ID to that same physical arm. Identical calibration schemas do not establish that a file belongs to the right arm; confirm the pair from the previous working setup.

Pass: correct ports are saved and the intended calibration pair is imported. No motor provisioning or new calibration is needed merely to move computers. Physical pose verification remains required before use with this LeRobot version.

## Checkpoint C — Identify cameras, then review teleoperation

Run the upstream camera discovery command yourself when the cameras are connected:

```sh
uv run --locked lerobot-find-cameras opencv --output-dir .cache/camera-preview
```

This opens cameras and writes preview images. Grant macOS Camera access to the terminal application when prompted. Review the images to identify overhead and wrist, including any built-in laptop camera in the enumeration. Configure the indices you observed:

```sh
uv run --locked so101 configure --overhead-camera=0 --wrist-camera=1
```

The indices above are examples. Initial settings are 640×480 at 30 fps per camera to limit USB and memory load on the 8 GB MacBook. If a camera does not support that mode, edit its capture settings in `configs/hardware.local.json` after checking its supported modes. Device indices can change after reconnecting; re-identify them on every machine.

To position a configured camera with a live view:

```sh
uv run --locked so101 camera-preview
# Or preview the wrist:
uv run --locked so101 camera-preview --camera wrist
```

Open the local URL printed in the terminal. The browser shows a live view at up to 15 fps and a **Stop camera** button. This preview records nothing, opens only the selected camera, and binds only to this Mac's loopback address. The camera keeps capturing at its configured rate. Stop it with the button or Ctrl+C before running other camera commands; closing the tab alone does not release the camera. It automatically stops after 30 minutes; `--duration=300` sets a five-minute limit. The URL changes each time it starts.

Then test both configured cameras together, with arm control stopped:

```sh
uv run --locked so101 camera-check
```

This opens only the two configured indices for 60 seconds through LeRobot, saves first/last previews and a JSON timing report under `.cache/camera-check/`, and closes the cameras. It never opens arm ports. The initial capture gate requires at least 95% of the requested frame rate per camera and no observed gap over 200 ms. Timing uses distinct host frame timestamps, so it is not a sensor synchronization test or an exact hardware dropped-frame count. Inspect framing separately: the overhead view should contain the follower's task workspace and the wrist view should show the gripper and nearby objects. A short `--duration=5` run is useful for preview but does not complete the 60-second checkpoint.

The [first camera checkpoint](../reports/2026-10-14-cameras.md) measured 29.97 fps overhead and 30.02 fps wrist with both connected through the hub. Those measurements establish capture timing for that setup; overhead framing and throughput during demonstration recording still need verification.

Generate the command:

```sh
uv run --locked so101 teleop-command --without-cameras
# Once both views are configured:
uv run --locked so101 teleop-command
```

These commands **print only**. Review the output and run it explicitly when the workspace is clear and the arms are ready. The printed command supplies each calibration directory and ID, sets both arms to degree units, and optionally displays both camera streams through LeRobot's visualization. The gripper still follows LeRobot's gripper normalization; do not treat every channel as a joint angle. Do not pipe the printed output into `eval`.

The generated command runs at **30 Hz** and includes `--robot.max_relative_target=5.0`. This setup's operator confirmed functioning teleoperation at 5 after elbow/wrist movement was ineffective with limits of 1 and 2. The limit caps the requested position relative to each motor's **measured position**: 5 degrees for arm joints and 5 percentage points for the gripper. It is not a speed limit or a guarantee of smooth tracking. The setting is saved as `follower.max_relative_target` in the local configuration and is the project default for older configurations that omit it.

Press **Ctrl+C** in the terminal running teleoperation to stop command streaming. The generated command also includes `--robot.disable_torque_on_disconnect=false`, so the follower stays powered and holds its last target after a normal stop. This preserves the stop behavior used during initial testing. It does not release the arm, and failed communication or a crashed process is not a verified stop. See the [hardware checkpoint](../reports/2026-10-14-teleoperation.md) for completed checks and remaining verification.

Pass: after a supervised test, both arms correspond correctly and both views are usable. The generated command is upstream teleoperation, not the planned autonomous controller/watchdog. The full C2 hardware checks in [PLAN.md](PLAN.md) still apply.

## Move to the other Mac

1. Clone the repository and run setup there. Do not copy `.venv`, `.cache`, or `.python`; rebuild from the lockfile.
2. Copy the ignored `calibration/` folder privately to the new checkout **if using the same physical arms**. Import those files with `calibration-import` to attach them to the new machine configuration. Alternatively, copy `configs/hardware.local.json` too, then correct its `control_host` and device settings.
3. Identify that Mac's serial paths and camera indices again. Keep the calibration/arm IDs associated with the physical arms.
4. Repeat the software check, camera preview, and supervised pose verification. A hardware change may require recalibration; a computer change alone does not.

Git carries the source, setup script, templates, and lockfile. Calibration, device settings, captured images, credentials, datasets, and environments are ignored. Git cloning alone does not transfer calibration.

## Updating dependencies

Routine installs use `uv sync --locked` via the setup script. Do not run `uv lock --upgrade` as part of machine migration. Dependency upgrades are separate changes: revise pins, regenerate the lockfile, rerun software and hardware checks, and retain the last working version.

To test the setup helpers without touching hardware:

```sh
uv run --locked python -m unittest discover -s tests -v
```
