# First raise-arm recording

The camera position has been accepted by the operator. The next step is **one local 15-second commissioning episode**, followed by review. This is not an accepted training dataset or a completed C3 gate. The remaining pose, stop, and reconnect checks in [C2](PLAN.md#c2--calibrate-teleoperate-and-reconnect) still apply before collecting the training set.

## Prepare

1. Keep the camera and follower base fixed. Stop the live camera preview and any other teleoperation process so the recorder can use the devices.
2. Use the working calibrated setup, with the leader and follower in corresponding starting poses and the follower's workspace clear. The generated command enables teleoperation when run.
3. Generate a command from the saved settings:

   ```sh
   uv run --locked so101 record-command --session raise-arm-smoke-001
   ```

   This prints a command without executing it. Review it, then copy and run the printed `uv run --locked lerobot-record ...` line in your terminal. No Hugging Face login or Modal job is needed. An existing dataset folder is refused; for another attempt use a new session name, or omit `--session` to generate a UTC timestamp.

## Demonstrate once

When the terminal announces **Recording episode 0**, smoothly raise the arm with the leader to the chosen reachable pose, then hold it for at least two seconds. Keep the gripper state consistent. Press **n** (or Right arrow) to end the episode after the hold, or let the 15-second timer finish. Keep any return-to-rest movement outside the recorded episode.

Keep the recording terminal focused for keyboard controls. If the demonstration is wrong, **r** (or Left arrow) requests a retry; the recorder provides a 10-second reset interval with teleoperation still active before retrying. **q** (or Esc) stops recording but can still save the partial episode. Ctrl+C interrupts the process; inspect any partial output before reusing it. A stopped or failed attempt must not be treated as a successful demonstration.

The follower uses the working relative target cap of **5** and remains powered at the last target after a normal disconnect (`disable_torque_on_disconnect=false`). This is the same hold behavior as the teleoperation command. Recording itself does not implement the planned autonomous watchdog.

## Output and review

The dataset is written under `data/raise-arm-smoke-001/`, which is ignored by Git. Uploading and resuming are disabled. Both configured cameras are included at 640×480 / 30 fps with the current machine settings. H.264 video is encoded through PyAV while recording, using two encoder threads per camera and bounded queues. Visualization is disabled to reduce load on the 8 GB MacBook; the terminal announces episode transitions.

After the test, inspect both videos without replaying motor actions. Check that the entire raise and hold are visible, timestamps and episode boundaries are valid, both videos have the same number of frames as the state/action table, and all six state/action channels are finite. Record actual throughput and any slow-loop or encoder-drop warnings; logical dataset timestamps alone do not establish wall-clock capture speed. If the raised position leaves the image, adjust the camera before collecting more data.

The command generator and codec setup have software checks; simultaneous camera capture, motor control, and dataset writing still require this physical test. After reviewing it and completing the remaining C2 checks, prepare the five-episode C3 collection with explicit acceptance/rejection and calibration/configuration provenance.

Software verification on 2026-10-14: all 17 automated tests passed, including parsing this command through pinned LeRobot and refusing existing dataset folders. A two-stream synthetic encoder check produced and decoded 60 frames per stream at 640×480 using the selected H.264 settings, with matching frame counts and increasing timestamps. No arms or cameras were accessed by that encoder check.

## Action meaning in the pinned recorder

In installed LeRobot 0.6.1, the default recording pipeline saves the leader's requested position targets as `action`. The SO-101 follower subsequently caps target error relative to its measured position inside `send_action`. The recorder receives the capped targets as `_sent_action` but does not save that return value as `action`. Therefore the test dataset's action column must not be labelled as the exact target sent to each motor.

This test preserves upstream behavior. Before accepting a training dataset, explicitly choose and validate the action contract: either retain desired targets with the same cap at inference, or add recording of the actual sent targets. Also add per-session calibration/configuration provenance and explicit rejection of aborted episodes. The C4 data contract remains pending until that decision is implemented and tested; do not train on the commissioning episode by accident.
