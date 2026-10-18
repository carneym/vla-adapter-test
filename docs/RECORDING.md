# Recording with reset loops

Use [LeLab](https://github.com/huggingface/leLab) to collect repeated demonstrations in one session. Keep the accepted camera placement fixed and the complete gesture visible. Five raise-arm episodes produced the first working local ACT checkpoint; the operator has reported a successful initial run and three successful repeats. A separate [five-episode wave session and 50-update local ACT run](../reports/2026-10-18-wave-act-smoke.md) have now completed. The first physical wave test raised the arm but did not wave; further training and sequence checks are the next proposed step.

## Teach wave

For wave collection, use `wave-c6`, task **`Wave.`**, **5 episodes**, **30 seconds per episode**, and **15 seconds for initial setup and each reset**, as requested on 2026-10-18. Use the existing `overhead` and `wrist` cameras at 640×480 and 30 fps, with streaming encoding enabled. The form does not create recordings until you click **Start Recording**; LeLab will append a session timestamp to the dataset name.

For this first batch, use the same lowered starting pose and repeat one consistent gesture:

1. Click **Start Recording** when ready. During the initial **Resetting** interval, use the leader to settle the follower into the lowered pose. Click **Start Next Episode** to begin.
2. Raise to a comfortable pose that remains in the overhead view. Make **three gentle side-to-side cycles** with the leader, keeping the wave size and pace similar across takes and leaving slack in the wrist-camera cable.
3. Return to the lowered rest pose and hold for about two seconds. Click **End Episode** to save the complete gesture before the recording timer expires.
4. Use **Resetting** to prepare the next take. Use **Re-record** for an interrupted or incomplete gesture. Save five accepted takes.

For wave, the return to rest is intentionally part of the learned gesture and belongs inside the recording. Extra repositioning between takes belongs in the reset interval. This is the initial teaching recipe; choose one consistent wave style rather than mixing different styles within this small batch.

Checkpoints: review the first saved take for the full three-cycle gesture in the overhead view and a working wrist view; after five takes, inspect both video streams, episode boundaries, and state/action data. Then train a **separate local ACT wave policy**, starting with a short training/checkpoint check before a supervised rollout. Five takes and a short training run are a first test, not a guarantee of a successful wave. Add demonstrations or training based on the observed failures. Keep the successful raise-arm dataset and checkpoint available.

The wave ACT run will use a fresh policy initialization with the standard pretrained vision backbone, not resume the raise-arm checkpoint. Standard ACT uses images and robot state, not the task text, to select actions. Simply mixing raise and wave demonstrations from the same starting scene does not provide a reliable way to select the gesture. For now, select each skill's checkpoint in LeLab. A combined model that selects skills from language instructions belongs to the planned VLA-Adapter work and will need demonstrations of both skills; fine-tuning only on the new task can degrade the old skill.

## Raise-arm session reference

1. Stop other teleoperation, recording, and camera-preview processes. Put the leader and follower in corresponding starting poses, with the workspace clear.
2. From this checkout, run:

   ```sh
   bash scripts/lelab.sh
   ```

3. Select **SO101**, open the **Dataset** dropdown, and choose **Create new dataset…**. Enter a name such as `raise-arm-c3`. In **Configure Recording**, use:

   | Setting | Value |
   | --- | --- |
   | Task description | `Raise your arm.` |
   | Episodes | `5` |
   | Episode duration | `30` seconds (time allowed to finish and accept a take) |
   | Reset duration | `30` seconds |
   | Cameras | `overhead` and `wrist`, 640×480 at 30 fps |
   | Streaming encoding | Enabled |

4. Check the two camera views, then start when ready. Starting the session connects the arms and enables teleoperation. LeLab first enters **Resetting**, with no frames saved. Use the leader to settle the follower into its starting pose. Click **Start Next Episode** when ready, or wait for the reset timer.
5. During **Recording**, smoothly raise the arm and hold the final pose for about three seconds. Click **End Episode** to save the take before returning to rest. The session enters **Resetting** again, and you use the leader to return the follower to the starting pose. Repeat until five takes have been saved.

The reset is a period of active teleoperation without recording. It does **not** automatically drive the arm to a stored home position. For raise-arm demonstrations, return-to-rest movement belongs in this interval, outside the demonstration.

## Controls

Keep the recording page focused for shortcuts.

| Control | Result |
| --- | --- |
| **End Episode**, Space, or Right arrow during recording | Save the current take and enter reset |
| **Start Next Episode**, Space, or Right arrow during reset | End reset early and begin recording |
| **Re-record**, Left arrow, or Delete/Backspace | Discard the current take, reset, and retry that episode |
| **Stop recording** in the menu, or Escape and confirm | End the session; previously saved episodes are retained |

In the pinned LeLab version, **recording timeout requests a redo, rather than accepting the take**. Press **End Episode** for each successful demonstration. Reset timeout starts the next recording. Stop can discard the in-progress take, so end an episode first if you want to keep it. Wait for saving/finalization to finish before closing the server.

## Settings and files

The project launcher preloads the saved pair and preserves degree units, `max_relative_target=5`, and `disable_torque_on_disconnect=false`. The cap is relative to measured joint position: five degrees for arm joints and five percentage points for the gripper. It is not a velocity limit. The follower continues holding its last target after normal disconnect. The launcher verifies existing motor calibration before configuring control; it does not rewrite calibration during collection.

The seeded camera indices are ready for backend capture. If the setup form says **No browser match**, the browser preview has not been bound to a browser camera ID; this is separate from OpenCV capture. To enable previews, use **Configure → Cameras** to select the same devices in the browser and retain the names `overhead` and `wrist`. Confirm the view identities before collecting after any USB changes.

Both cameras have a five-second startup allowance. H.264 encoding uses two threads per camera and a bounded queue. The existing 500 ms stale-frame failure remains active. A UI cannot fix an intermittent wrist-camera cable/hub fault: if frames time out, preserve saved episodes, inspect the failure, and test camera access before retrying. The TorchCodec-to-PyAV fallback warning is separate from camera acquisition failures.

### Camera connected but startup times out on macOS

A camera appearing in macOS or LeLab's device list does not prove it is delivering frames. If recording reports `Timed out waiting for frame from camera OpenCVCamera(...)` after reconnecting USB devices, stop the idle LeLab server and relaunch `bash scripts/lelab.sh`, then reload the browser page. LeLab's macOS discovery helper uses a fresh process because AVFoundation device references can become stale after hotplug in the long-running server. Restarting refreshes the capture process as well. Stop active recording or teleoperation normally before restarting; do not interrupt a save.

Check camera indices again after changing USB connections. Keep previews and other camera applications closed while recording. If a fresh process also cannot capture frames, investigate the cable, hub/port, or camera rather than repeatedly extending timeouts. The 15-second setup/reset interval is separate from camera startup and frame-freshness checks. Model training reads the saved dataset and does not open these live cameras.

On 2026-10-18, repeated overhead-camera startup timeouts occurred in the existing LeLab recording process. A separate camera-only check using the same LeLab environment captured both cameras simultaneously for 15 seconds: overhead 30.04 fps / 66.8 ms maximum observed gap; wrist 30.04 fps / 65.5 ms. Current identities still mapped to overhead index 0 and wrist index 1. After restarting the idle server to clear possible stale references, `local/wave-c6_20261018_150106` completed five recordings with no camera timeout. Both videos decoded fully and matched the 2,393 state/action rows, confirming successful recording recovery for that session.

New datasets are local at `data/lelab/<namespace>/<timestamped-name>/`, ignored by Git. LeLab appends timestamps to new session names, so there is no need to copy a fresh recording command. Recording starts with Hub upload disabled. Use **Datasets** to inspect completed takes and, when appropriate, **Record More Episodes** to append to a completed dataset. Existing CLI smoke recordings remain in their original `data/raise-arm-smoke-*` folders; they are not automatically imported into this browser.

On another Mac, follow [SETUP.md](SETUP.md): clone the repository, privately copy/import the selected calibration and machine settings, update device indices/ports, and launch the same script. The separately locked LeLab environment uses its upstream LeRobot v0.6.0; the CLI environment remains at 0.6.1.

## Checkpoints

1. **Software:** `bash scripts/lelab.sh --check` validates the configured arms, cameras, encoder, and reset parameters without opening devices. Integration tests exercise native record/reset/redo handlers with fake devices and a real two-camera encoded dataset.
2. **First UI take:** collect one raise-and-hold, explicitly end it, reset, and verify the saved videos. This is the first physical test of the LeLab integration; software tests do not prove motor or camera reliability.
3. **Five accepted takes:** inspect both camera views, all six finite state/action channels, episode boundaries, and matching video/table frame counts. Reject cropped motion, reset movement inside an episode, aborted takes, or camera failures. Logical dataset timestamps alone do not establish wall-clock capture throughput. Complete the remaining pose, stop, and reconnect checks in [C2](PLAN.md#c2--calibrate-teleoperate-and-reconnect) before accepting the collection gate.

## Action meaning and training

The default LeRobot recording pipeline saves the leader's desired position targets as `action`. The follower applies the relative target cap inside `send_action`; the returned capped `_sent_action` is not saved as the action column. This applies to both pinned environments. Do not label these actions as exact motor commands.

Before training, choose and validate either desired targets with the same cap at inference, or explicit recording of actual sent targets. Per-session calibration/configuration provenance and episode acceptance also remain part of C4. LeLab supplies the collection interface; VLA-Adapter conversion and the USD 20 Modal training path still need implementation. No paid training has started.

## One-off CLI diagnostics

`uv run --locked so101 record-test` still records one 15-second commissioning episode with a fresh folder and a 15-second setup countdown. Add `--setup-seconds 30` for more preparation time or `--dry-run` to inspect without devices. The countdown precedes connection and is not a teleoperated reset interval. Prefer LeLab for repeated collection.
