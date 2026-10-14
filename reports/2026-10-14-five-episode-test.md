# Five-episode LeLab test — 2026-10-14

**Result: the physical recording/reset loop and saved-file integrity passed.** The dataset is retained for pipeline testing; acceptance as the five-demonstration training set remains open because the final pose is partly outside the overhead image and hold duration varies.

Dataset: `local/raise-arm-c3_20261014_175556`, task `Raise your arm.` The operator ran the session. Review used local files and logs without opening cameras, replaying actions on the robot, uploading data, or starting training.

## Saved data

- Five episode metadata rows and 1,227 data rows. Both H.264 videos decode 1,227 frames at 640×480 with strictly increasing presentation timestamps.
- Video episode offsets match the data timeline; the maximum numerical difference is below 1e-12 seconds. This establishes encoded alignment, not hardware synchronization or actual capture latency.
- Per-episode frame indices and nominal 30 Hz timestamps are correct. All six state and action channels are finite, with the expected joint order and task label.
- Logs show all five takes explicitly ended and saved, with reset phases between takes. Both cameras and both arms disconnected cleanly. The observed reset intervals were approximately 15 seconds.
- No camera-read error, camera timeout, or fatal recorder error occurred. One 25.3 Hz loop warning occurred during the initial reset. Repeated relative-target clamping warnings show the saved cap being exercised; they are not camera errors. No new smoothing or motion-limit setting was introduced.

| Episode | Frames | Nominal duration | Final settled suffix* |
| --- | --- | --- | --- |
| 1 | 302 | 10.07 s | 3.07 s |
| 2 | 213 | 7.10 s | 1.03 s |
| 3 | 251 | 8.37 s | 1.83 s |
| 4 | 220 | 7.33 s | 2.20 s |
| 5 | 241 | 8.03 s | 1.93 s |

*Contiguous final samples within one unit of each final measured joint position, divided by the configured 30 Hz. This is a numerical review aid, not a validated success metric or wall-clock measurement.

## Demonstration review

Six evenly spaced frames per episode from each camera were inspected alongside numeric joint trajectories. Each take starts in a similar lowered pose and ends raised; reset-to-rest occurs between saved episodes. The upper arm/gripper reaches beyond the top of the overhead frame near the raised endpoint. The wrist stream remains readable. End poses also vary, and four final settled suffixes are shorter than the proposed three-second hold.

Keep the current camera placement. For future accepted training takes, use a consistent, lower bent-elbow target that stays in the image, then hold for three seconds before pressing End Episode. These five tests can support converter/loader validation now; they do not establish policy success or a sufficiently varied training dataset.

## Storage, upload, and provenance

The dataset remains under `data/lelab/local/raise-arm-c3_20261014_175556/`. A separate upload attempt after finalization failed with Hugging Face `401 Unauthorized`; this did not undo local saving. No upload was retried by the agent. Hub upload is not needed for the next local data-validation step.

The integration ran from project commit `6b2df58b72a4e6fed83d83e2756fb2a70e6a9175`, with the pinned LeLab runtime. Detailed review JSON, per-file SHA-256 digests, current calibration/configuration hashes, and contact sheets are stored privately in `.cache/episode-review/raise-arm-c3_20261014_175556/`. Those configuration hashes were captured after the run and must not be presented as a start-of-session provenance snapshot. Raw videos, calibration files, and contact sheets remain outside Git.

Next: validate the six-channel VLA-Adapter data conversion offline using this smoke fixture, retain the desired-target/relative-cap semantics explicitly, and prepare a bounded Modal smoke-training plan. C3 training acceptance, full hardware stop/reconnect evidence, and automated provenance still have outstanding checks. No paid training has run.
