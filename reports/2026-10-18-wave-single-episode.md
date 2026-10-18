# Wave target audit and single-episode ACT fit — 2026-10-18

## Target audit

The previous [1,000-update run](2026-10-18-wave-act-1000.md) still predicted almost constant pan targets. The follow-up checks the actual pinned LeRobot training data path, then fits a separate copy of one episode. No robot or live camera is used.

`scripts/audit_act_targets.py` recreates the dataset through LeRobot's `make_dataset`, collates samples as training does, converts decoded uint8 RGB frames to float32 [0, 1], and applies the saved processors. It compares targets directly against the recorded table rather than deriving expected values from the loader.

The audit covered 50 observations across all five original episodes, including wave segments and episode ends:

- Targets have shape `[1, 100, 6]` and contain the current target followed by 99 future targets in the correct order.
- Episode-end targets repeat the final value and are masked as padding; no target crosses into the next episode.
- Action normalization preserves the wave: inverse normalization agrees with the raw table to within **0.00000573 action units**.
- Both image channels have the expected `[1, 3, 480, 640]` shape and finite processed values.
- Selecting episode 0 yields exactly **556 frames**, all belonging to that episode.

There is a concrete state-normalization problem in the original data. The gripper state is exactly **2.178217887878418** throughout all 2,393 rows. The saved mean is **2.1782219409942627** and standard deviation is **1.1479738759589964e-7**. After division by the standard deviation plus epsilon, that unchanged channel becomes approximately **−32.48**, while the other state channels have maximum absolute normalized values between 1.45 and 3.27. The action targets themselves are not flattened by normalization.

## Separate diagnostic dataset

`scripts/prepare_act_episode.py` uses LeRobot's upstream dataset-copy/filter operation to keep source episode 0 in a new dataset, `local/wave-ep0-audited_20261018`, under `data/lelab/`. The original five-episode dataset and previous checkpoints are preserved. SHA-256 checks before/after extraction confirm the source files are unchanged.

The copy has one 18.53-second episode (556 frames). Its state and action rows exactly match the source episode. Both re-encoded camera videos decode to 556 frames. Vector means and standard deviations are recomputed in float64 from these rows. Exactly constant channels—wrist-roll state and gripper state in this episode—use the exact mean and a deliberate **unit normalization scale of 1**, mapping their recorded values to zero without magnifying rounding noise. This scale is a preprocessing convention, not an estimate of nonzero variance. Both global and per-episode metadata are updated consistently, only in the copy.

A second audit of the new training processors passed target order, padding, finite inputs, and action round-trip checks (maximum error **0.00000763 action units**). The two constant state channels normalize to zero. The experiment changes both the training subset and its vector statistics, so it is not an isolated causal test of the gripper issue.

## Motion direction and observations

Frames **200** and **234** of episode 0 (6.67 and 7.80 seconds) have exactly the same five body-joint positions. Their next half-second shoulder-pan target changes are **−12.66°** and **+20.92°**, respectively. Standard ACT here uses one observation instant (`n_obs_steps=1`); joint position alone cannot distinguish those directions. Camera images may contain extra cues. This is evidence of ambiguity in the state channel, not proof that the complete image/state observations are indistinguishable or that ambiguity alone caused the failed fit.

## Single-episode experiment

Job: `act_local_wave-ep0-audited_20261018_2026-10-18_15-59-53`.

The standard LeLab UI launches a fresh ACT initialization with the pretrained ResNet18 visual backbone, seed 1000, MPS, batch size 1, workers 0, PyAV decoding, 2,000 updates, logging every 50, and complete saves at 1,000 and 2,000. The policy training preset remains AdamW at 1e-5 with weight decay 1e-4 and gradient clipping 10. AMP, W&B, Hub upload, and resume remain off. This is a local fitting diagnostic, not held-out validation or physical wave acceptance.

The job finished successfully with exit code 0 in **11 minutes 59 seconds** (including startup/save/shutdown). Both complete checkpoints are saved at `run/checkpoints/001000` and `run/checkpoints/002000`. Each contains **619,561,312 bytes** across its model, processor, configuration, and training-state files. Offline checks restored the weights strictly, all 153 optimizer parameter states at the correct step, and RNG state; parameters, optimizer tensors, and predictions were finite. File hashes were recorded locally. The saved processors use unit scales for the two constant state channels, confirming the corrected copy's statistics reached training.

All three checkpoints below were evaluated on the **same episode-0 observations**, using CPU inference and the checkpoint's own saved normalization. There are 20 sampled observations (one per second plus the final frame); the wave summary uses seven observations at seconds 5–11 inclusive. Every predicted chunk is compared against the recorded future targets and clipped at the episode end. This sampling differs from the previous report's five-episode protocol, so its averages should not be compared directly.

| Model | Mean predicted pan range | Mean demonstrated pan range | Pan mean absolute error |
| --- | ---: | ---: | ---: |
| Previous five-episode model, 1,000 updates | 0.101° | 51.830° | 15.564° |
| Audited single episode, 1,000 updates | 0.033° | 51.830° | 15.768° |
| Audited single episode, 2,000 updates | **0.026°** | **51.830°** | **15.494°** |

The 2,000-update model still does **not** fit the demonstrated wave. Predictions remain nearly constant within each chunk. Reducing the dataset and correcting normalization did not produce the alternating pan motion within this bounded experiment. This does not establish that ACT can never fit this episode, and the cause of the remaining failure is unresolved. No further arm trial was started.

### Other joints

| Joint | Demonstrated chunk range | Predicted chunk range, 2,000 updates | Mean absolute error, 1,000 → 2,000 updates |
| --- | ---: | ---: | ---: |
| Shoulder pan | 51.830° | 0.026° | 15.768° → 15.494° |
| Shoulder lift | 1.683° | 0.064° | 2.133° → 0.955° |
| Elbow flex | 2.386° | 0.115° | 7.538° → 3.670° |
| Wrist flex | 0.553° | 0.031° | 0.628° → 0.364° |
| Wrist roll | 0.440° | 0.00090° | 0.146° → 0.124° |
| Gripper | 0.112 units | 0.00017 units | 0.00971 → 0.00972 units |

All values are averages over the same seven wave-phase chunks. The error comparison in the final column uses the two **single-episode** checkpoints. The gripper uses the project's 0–100 convention. These are commanded action targets, not measured follower positions: a constant measured state channel can still have small changes in its demonstrated action targets.

Separate four-panel charts for all six joints compare predictions at seconds 5, 7, 9, and 11. A combined overview shows all six joints from the observation at second 7. Charts use each joint's own scale, with a minimum vertical span of one action unit to avoid exaggerating tiny variations. The all-joint JSON preserves every predicted and target value, with named columns and units.

The executable example in [Inspecting ACT](../docs/INSPECTING_ACT.md) also passed using the final checkpoint on **MPS**: its action array has shape `(100, 6)`, and its second-7 pan range is **0.02153°**, consistent with the CPU check's flat trajectory. There was no training or hardware motion during these inspections.

A useful next controlled diagnostic is to compare ACT's training-time reconstruction with its deployment-time prediction on the same fixed samples, then test whether chunk length or temporal observation information is limiting the fit. Those experiments have not been started. Preserve the successful raise-arm policy and keep wave acceptance open.

## Reproduction and local evidence

Use the pinned LeLab Python, `.cache/lelab/venv/bin/python`. The new audit/preparation scripts accept `--help`. Preparation requires a new output dataset directory and refuses to overwrite one. `scripts/check_act_wave.py --stride-frames 30` samples each second and the final frame of each episode; its wave summary covers observations from seconds 5 through 11 inclusive. `scripts/plot_act_wave.py` renders the resulting comparison JSON using matplotlib; `--joint all` creates six four-panel charts and an overview. See [Inspecting ACT](../docs/INSPECTING_ACT.md) for runnable commands and the input/output explanation.

Local artifacts remain outside Git: `.cache/wave-target-audit.json`, `.cache/wave-ep0-preparation.json`, `.cache/wave-ep0-target-audit.json`, and `.cache/wave-ep0-pose-ambiguity.json`, with matching audit/preparation logs. Recordings and checkpoints are not uploaded.

Final local evidence: `.cache/wave-ep0-all-joints.json`, `.cache/wave-ep0-all-joints.log`, `.cache/wave-ep0-all-joints.png`, the six `.cache/wave-ep0-<joint>.png` charts, and `.cache/inspect-act-example.log`.
