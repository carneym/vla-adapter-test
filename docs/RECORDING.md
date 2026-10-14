# First raise-arm recording

The camera position has been accepted by the operator. The next step is **one local 15-second commissioning episode**, followed by review. This is not an accepted training dataset or a completed C3 gate. The remaining pose, stop, and reconnect checks in [C2](PLAN.md#c2--calibrate-teleoperate-and-reconnect) still apply before collecting the training set.

## Prepare

1. Keep the camera and follower base fixed. Stop the live camera preview and any other teleoperation process so the recorder can use the devices.
2. Use the working calibrated setup, with the leader and follower in corresponding starting poses and the follower's workspace clear.
3. Start a test from the saved settings:

   ```sh
   uv run --locked so101 record-test
   ```

   This starts a **15-second setup countdown**, then connects the cameras and arms and starts the upstream recorder. Ctrl+C during the countdown cancels without opening any devices. Each invocation chooses a new timestamped dataset name with a random suffix; no copying of a generated command is needed. No Hugging Face login or Modal job is needed.

   For more setup time:

   ```sh
   uv run --locked so101 record-test --setup-seconds 30
   ```

   The setup countdown happens before device connection, so it does not enable teleoperation for repositioning. Use the leader to reset the follower with the teleoperation command first if needed. After setup, each camera has a five-second warmup/read allowance. Begin the demonstration only when **Recording episode 0** is announced. The episode itself lasts up to 15 seconds.

To inspect without starting anything, add `--dry-run`. The older `record-command` helper still prints an upstream command for manual review, but that printed command keeps a fixed output name; prefer `record-test` for retries.

### If the output folder already exists

`FileExistsError` during `LeRobotDataset.create` means the selected output folder already exists. LeRobot requires a new folder even when the existing one contains only metadata from an interrupted attempt. Do not create the dataset directory in advance. Preserve the old attempt and run `so101 record-test` for a fresh name. Do not use `--resume=true` on an incomplete dataset merely to suppress this error.

### If a camera times out

The initial recorder used LeRobot's one-second camera warmup default. The helpers now explicitly use five seconds, including camera previews and checks. A successful camera-only test after the change measured 30.07 fps overhead and 30.09 fps wrist; recording with arm control still requires verification. If startup still fails, stop other preview/recording processes and run `so101 camera-check --duration 5` to isolate camera access before another motor session. The TorchCodec warning followed by a PyAV fallback is separate from a camera frame timeout; PyAV successfully passed the local dataset save test.

## Demonstrate once

When the terminal announces **Recording episode 0**, smoothly raise the arm with the leader to the chosen reachable pose, then hold it for at least two seconds. Keep the gripper state consistent. Press **n** (or Right arrow) to end the episode after the hold, or let the 15-second timer finish. Keep any return-to-rest movement outside the recorded episode.

Keep the recording terminal focused for keyboard controls. If the demonstration is wrong, **r** (or Left arrow) requests a retry; the recorder provides a 10-second reset interval with teleoperation still active before retrying. **q** (or Esc) stops recording but can still save the partial episode. Ctrl+C interrupts the process; inspect any partial output before reusing it. A stopped or failed attempt must not be treated as a successful demonstration.

The follower uses the working relative target cap of **5** and remains powered at the last target after a normal disconnect (`disable_torque_on_disconnect=false`). This is the same hold behavior as the teleoperation command. Recording itself does not implement the planned autonomous watchdog.

## Output and review

The dataset is written under `data/raise-arm-smoke-<UTC timestamp>-<random suffix>/`, which is ignored by Git. Uploading and resuming are disabled. Both configured cameras are included at 640×480 / 30 fps with the current machine settings. H.264 video is encoded through PyAV while recording, using two encoder threads per camera and bounded queues. Visualization is disabled to reduce load on the 8 GB MacBook; the terminal announces episode transitions.

After the test, inspect both videos without replaying motor actions. Check that the entire raise and hold are visible, timestamps and episode boundaries are valid, both videos have the same number of frames as the state/action table, and all six state/action channels are finite. Record actual throughput and any slow-loop or encoder-drop warnings; logical dataset timestamps alone do not establish wall-clock capture speed. If the raised position leaves the image, adjust the camera before collecting more data.

The command generator and codec setup have software checks; simultaneous camera capture, motor control, and dataset writing still require this physical test. After reviewing it and completing the remaining C2 checks, prepare the five-episode C3 collection with explicit acceptance/rejection and calibration/configuration provenance.

Software verification on 2026-10-14: all 17 automated tests passed, including parsing this command through pinned LeRobot and refusing existing dataset folders. A two-stream synthetic encoder check produced and decoded 60 frames per stream at 640×480 using the selected H.264 settings, with matching frame counts and increasing timestamps. No arms or cameras were accessed by that encoder check.

After the first folder-collision report, the original `raise-arm-smoke-001` folder contained only metadata with zero episodes and zero frames; it was preserved. An additional complete synthetic dataset test successfully created a new dataset, saved and finalized one six-frame episode, and decoded six frames from each camera video. The default decoder reported the known TorchCodec library warning and successfully fell back to PyAV. This verified dataset saving without opening hardware, not a physical demonstration.

Launcher verification: all 21 automated tests pass, including countdown ordering, cancellation before device access, fresh retry names, and the pinned LeRobot parser accepting the five-second camera settings. The new launcher was dry-run only; no physical recording was started by the agent.

## Action meaning in the pinned recorder

In installed LeRobot 0.6.1, the default recording pipeline saves the leader's requested position targets as `action`. The SO-101 follower subsequently caps target error relative to its measured position inside `send_action`. The recorder receives the capped targets as `_sent_action` but does not save that return value as `action`. Therefore the test dataset's action column must not be labelled as the exact target sent to each motor.

This test preserves upstream behavior. Before accepting a training dataset, explicitly choose and validate the action contract: either retain desired targets with the same cap at inference, or add recording of the actual sent targets. Also add per-session calibration/configuration provenance and explicit rejection of aborted episodes. The C4 data contract remains pending until that decision is implemented and tested; do not train on the commissioning episode by accident.
