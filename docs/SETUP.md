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

The [first camera checkpoint](../reports/2026-10-14-cameras.md) measured 29.97 fps overhead and 30.02 fps wrist with both connected through the hub. The operator subsequently accepted the adjusted placement. Visibility through the full task motion and throughput during demonstration recording still need verification.

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

## Collect with LeLab

```sh
bash scripts/lelab.sh
```

This installs/uses the separate locked environment in `.cache/lelab/venv` and opens [LeLab](https://github.com/huggingface/leLab) at `http://127.0.0.1:8000`. Choose the prefilled **SO101** robot. See [Recording with reset loops](RECORDING.md) for the first five-episode session and controls. Opening the UI does not connect the arms; starting teleoperation or recording does.

The launcher reads `configs/hardware.local.json` and uses the existing calibration files. It applies the 5° target cap, degree units, hold-on-disconnect setting, five-second camera warmup, and bounded H.264 encoding. At connection, it verifies motor calibration against the selected files instead of rewriting it. If those differ, inspect/import the correct calibration with the existing setup tools before collecting; this launcher is for the already calibrated pair.

LeLab is pinned to commit `9b5afaee33baa1d773e499937564f3831d25de22`; its upstream dependency is LeRobot **v0.6.0**, separate from the original **0.6.1** CLI environment. Its transitive dependencies are locked in `integrations/lelab/uv.lock`. The first launch downloads dependencies and builds the UI; later launches reuse them. Both environments target Apple Silicon/Python 3.12. No model or paid training job is started by this command. Use this project launcher so the saved motion settings are applied.

Run `bash scripts/lelab.sh --check` to validate generated settings without opening devices or a server. For software integration checks:

```sh
UV_PROJECT_ENVIRONMENT="$PWD/.cache/lelab/venv" UV_CACHE_DIR="$PWD/.cache/uv" \
  uv run --project integrations/lelab --locked python -m unittest discover -s integrations/lelab/tests -v
```

GUI camera edits persist locally. Changing camera settings in `hardware.local.json` refreshes the seeded cameras on the next launch; ports and calibration selection always follow that file. Browser camera identities differ from USB identities, so confirm overhead/wrist views after changing USB connections. Move the local config and calibration files privately to the Mac mini, reselect its ports/camera indices, and run the same launcher. Do not copy virtual environments between machines.

New GUI datasets live under `data/lelab/<namespace>/<timestamped-name>/`. Existing CLI recordings remain in `data/`; the GUI does not automatically migrate them. LeLab state lives under `.cache/lelab/state/`. These directories and calibration files remain outside Git. Stop a recording through the UI and wait for saving to finish before closing the server with Ctrl+C.

## Short local ACT training in LeLab

The MacBook can run a small ACT experiment using its Apple GPU. This is a separate baseline from the planned VLA-Adapter/Modal implementation. Start LeLab with the project launcher above, open **Training**, and use:

| Setting | MacBook smoke run |
| --- | --- |
| Compute target | Local — your machine (free) |
| Dataset | Select the local five-episode dataset |
| Policy | ACT |
| Training steps / batch size | 50 / 1 |
| Advanced → Device | MPS (Apple Silicon) |
| Number of workers | 0 |
| Log frequency / save frequency | 10 / 50 |
| Save checkpoints / use policy training preset | On / on |
| AMP / W&B / resume | Off / off / off |

For the initial test, the dataset ID is `local/raise-arm-c3_20261014_175556`. If it is absent from the dropdown, use **Use custom repo ID** with that exact ID. Local training reads the files under `data/lelab/`; it does not require a Hugging Face upload or token. The cloud-token banner does not apply to this local job. The project launcher explicitly selects PyAV decoding for local macOS training because the pinned TorchCodec package can be installed while its FFmpeg libraries cannot load.

Free several GB before starting (aim for at least 5 GB on this 8 GB Mac, including room for swap). A stock ACT policy is about 197 MiB, and its optimizer state needs roughly another 394 MiB. Jobs are saved by LeLab under `~/.cache/huggingface/lerobot/outputs/train/<job-id>/`, outside the repository. The model, configuration, and normalization files are in `run/checkpoints/<step>/pretrained_model/`; exact training resume also requires the complete `training_state/` directory. Transfer these privately if needed on another Mac.

The [local ACT rerun](../reports/2026-10-14-act-smoke.md#successful-checkpoint-rerun) completed 50 updates, exited cleanly, and saved a complete checkpoint. Model, optimizer, RNG, and step restoration passed, plus offline prediction checks. Use the successful job ending `18-50-52`; the earlier job ending `18-26-58` has incomplete optimizer state from disk exhaustion. Fifty updates on five demonstrations establish that the training path works; they do not establish a reliable raise-arm policy.

The same settings also completed a [separate wave smoke run](../reports/2026-10-18-wave-act-smoke.md) on dataset `local/wave-c6_20261018_150106`. Job `act_local_wave-c6_20261018_150106_2026-10-18_15-07-09`, step 50, has a complete checkpoint with offline restoration and prediction checks passed. Its first reported physical trial raised the arm but did not wave, and offline sequence checks confirmed almost constant predicted pan targets. A [1,000-step follow-up](../reports/2026-10-18-wave-act-1000.md) with log frequency 50 and save frequency 500 completed successfully under job `act_local_wave-c6_20261018_150106_2026-10-18_15-37-57`. Both checkpoints restore completely, but offline predictions still do not reproduce the wave. Keep further arm trials on hold; the report includes the repeatable offline comparison command. The raise-arm job remains a separate skill. The subsequent [single-episode diagnostic](../reports/2026-10-18-wave-single-episode.md) saved complete checkpoints at 1,000 and 2,000 updates but still predicted almost flat wave targets. Use the [offline ACT inspection guide](INSPECTING_ACT.md) to compare recorded and predicted trajectories for all six joints before another arm trial. A [chunk-30 run](../reports/2026-10-18-wave-act-chunk30.md) under job `act_local_wave-ep0-audited_20261018_2026-10-18_16-36-00` completed with both requested saves, but its predictions still do not reproduce the wave. The pinned ACT form lacks chunk controls; this run uses LeLab’s native `config_path` API support and the portable `configs/training/wave-ep0-chunk30.json` configuration.

## Supervised ACT test in standard LeLab

From the successful training job, choose **step 50 → Run on robot**. Select **SO101**, set the first test to **5 seconds**, and bind `overhead` to **#0 Logi 4K Pro** and `wrist` to **#1 USB2.0_CAM1**, both at 640×480 and 0° rotation. Confirm these identities again if USB connections have changed. Put the follower in the demonstrated starting pose, clear the workspace, remain beside the power switch, then use **Start Inference**. LeLab provides **Stop** while the run is active.

The project launcher uses LeLab's standard inference UI and upstream `lerobot_rollout` process. Because inference runs in a separate process, it passes native CLI flags for the saved calibration directory, degree units, 5° relative-target cap, hold-on-disconnect behavior, 30 Hz target rate, and no automatic return motion on exit. Both cameras receive the same five-second warmup used for collection. The relative-target cap bounds target error from the measured position; it is not a velocity limit. The follower stays powered at its last target after normal completion or Stop.

The [first physical test](../reports/2026-10-17-act-inference.md) completed its five-second loop and exited cleanly. Setup took about 24 seconds before that timer began. The operator subsequently confirmed that it worked very well and raised the arm to the top, then reported success on all three requested repeats. The initial three-repeat check has passed; broader start-pose coverage remains untested. Two slow control updates were logged in the first run; this is not acceptance of sustained 30 Hz control or the full C5 watchdog/stop checks. Continue with the [separate wave recording session](RECORDING.md#teach-wave).

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
