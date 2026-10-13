# MacBook software setup — 2026-10-13

Status: **software setup passed; C1 hardware discovery remains incomplete**.

- Target: M2 MacBook Air, 8 GB RAM, macOS arm64.
- Installed interpreter: Python 3.12.13; the repo supports the 3.12 patch series.
- LeRobot 0.6.1, PyTorch 2.10.0, torchvision 0.25.0, TorchCodec 0.10.0, PyAV 15.1.0; full dependency versions/hashes in `uv.lock`.
- `scripts/setup.sh macbook` installed an isolated `.venv` and created ignored local settings.
- Software smoke test passed: SO-101 configuration imports, Feetech SDK import, CPU tensor operation, OpenCV resize, synthetic H.264 encoding and LeRobot PyAV decoding with frame-order checks.
- Setup tests cover preserving existing settings, calibration source preservation, overwrite rejection, schema validation, separate device identities, shell quoting, and moving calibration between checkout paths.
- The generated teleoperation command is accepted by the pinned LeRobot argument parser. No robot or camera object was connected for this test.
- Upstream teleoperation, recording, and camera discovery help commands load successfully.
- Dependency lock, configuration JSON, shell syntax, and documentation links checked.

The Mac emits duplicate FFmpeg Objective-C class warnings when loading the OpenCV/PyAV wheels together. The synthetic video test passes; actual camera capture and the TorchCodec decoding path are unverified. No policy inference or GPU training was tested.

One USB serial controller was listed without opening it. Several existing calibration variants were found; none were automatically selected or modified. Both arm port mappings, the working calibration pair, and the two camera indices still need selection, followed by supervised physical verification.

No Modal jobs ran. Raw calibration, local configuration, environments, and captured images remain outside Git.
