# First supervised ACT follower test — 2026-10-17

**Result: successful initial raise-arm trial and three successful repeats, assessed by the operator.** The first five-second standard LeLab rollout exited normally. On 2026-10-18, the operator reported that it "worked very well, raising the arm to the top," then confirmed that all three requested repeats worked. This records four operator-reported successes and passes the initial three-repeat check. Broader start-pose coverage and the full C5/C6 gates remain open.

The user requested running the checkpoint, confirmed being beside the powered arm in its lowered starting pose with the workspace clear, and asked to use standard LeLab where possible. The test used the successful training job `act_local_raise-arm-c3_20261014_175556_2026-10-14_18-50-52`, checkpoint `000050`, trained for only 50 updates on the five local episodes.

## Configuration and preflight

The standard **Run on robot → Configure Inference → Start Inference** flow launched upstream `lerobot.scripts.lerobot_rollout`, base strategy, synchronous ACT inference on MPS. Duration was five seconds at a target 30 Hz. Camera bindings matched the checkpoint: overhead Logi 4K Pro at index 0 and wrist USB2.0_CAM1 at index 1, 640×480, 0° rotation. No dataset recording, Hub upload, or paid compute occurred.

The inference subprocess originally did not inherit this project's in-process teleoperation/recording adapters. The project launcher now passes native flags for the saved calibration directory, `use_degrees=true`, `max_relative_target=5.0`, `disable_torque_on_disconnect=false`, `return_to_initial_position=false`, and `fps=30`; native camera arguments include `warmup_s=5`. The standard LeLab interface and upstream rollout implementation remain in use. The live process command was inspected to confirm these exact settings.

A read-only motor preflight verified follower USB serial `5AB0157563`, matching motor/file calibration, all six torque flags enabled, and all six status registers zero. No position or torque commands were sent by the preflight. An initial diagnostic lookup used an unavailable register name; it was corrected to the pinned driver's `Status` register before the successful check.

## Observed execution

- Policy loaded on MPS; both cameras and the follower connected.
- Setup took about 24 seconds before the five-second control loop began.
- Six relative-target clamp warnings occurred for shoulder lift. These show the configured target-error cap being applied.
- Two slow-loop warnings occurred, reporting 1.1 Hz on the first update and 3.8 Hz near the end. Those rates describe individual slow iterations, not an average rate for the run. No sustained 30 Hz performance claim is made.
- The duration limit ended the loop. The inference engine stopped; the log explicitly confirmed that automatic return motion was skipped. Both cameras and the follower disconnected, and LeLab recorded process exit code 0 and displayed **Inference finished — Run completed**.
- No camera timeout or fatal rollout error appeared in the log. A separate read-only postflight confirmed unchanged calibration, all six status registers zero, and torque still enabled.

Joint readings before/after the run (body joints in degrees; gripper normalized 0–100):

| Joint | Before | After | Change |
| --- | ---: | ---: | ---: |
| Shoulder pan | -21.934 | -21.934 | 0.000 |
| Shoulder lift | -53.978 | -45.099 | +8.879 |
| Elbow flex | -1.934 | -2.198 | -0.264 |
| Wrist flex | 22.769 | 22.769 | 0.000 |
| Wrist roll | -0.044 | 4.264 | +4.308 |
| Gripper | 2.178 | 2.178 | 0.000 |

These are two snapshots, not a recorded trajectory, and do not measure peak speed, smoothness, or goal completion. Normal disconnect holds the last target; the 5° cap bounds target error rather than velocity. Deliberate Stop/power-disconnect testing and a separate local watchdog remain open.

The operator's later observation supplies the task-outcome assessment: the arm reached the top and the movement worked very well. Retain that assessment alongside the original numeric snapshots; no continuous trajectory or independent endpoint measurement was collected.

## Evidence and checks

The upstream rollout log is `~/.cache/huggingface/lerobot/inference_logs/1792253930.log`. Local pre/postflight readings are `.cache/inference-preflight.json` and `.cache/inference-postflight.json`; the idle post-run UI screenshot is `.cache/lelab-inference-finished.png`. These artifacts and the checkpoint remain outside Git.

All 21 project tests and seven LeLab integration tests passed. The new integration check verifies the inference argument adapter, saved calibration path, motion settings, camera index translation, and warmup while leaving caller camera settings unchanged. The real rollout additionally exercised the generated flags through the upstream parser and hardware.

On 2026-10-18, the operator confirmed: "yes all three worked" and requested moving on to wave collection in LeLab. The requested repeat protocol used the same checkpoint, cameras, 5° cap, demonstrated starting pose, and teleoperated resets. No separate logs, trajectories, intervention counts, or timing measurements were inspected for these three repeats; their outcomes are operator reports. The measurements above remain evidence from the first run only.

Next: collect five wave demonstrations using the [wave recording recipe](../docs/RECORDING.md#teach-wave), review them, then train and test a separate ACT wave checkpoint. Retain the working raise-arm policy. The broader ten-attempt evaluation in C6, stop/watchdog checks, and timing measurements remain open. No full C5/C6 acceptance is claimed.
