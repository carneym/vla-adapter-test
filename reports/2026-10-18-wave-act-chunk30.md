# ACT wave experiment: 30-action chunks — 2026-10-18

## Request and setup

Train a fresh ACT policy on the MacBook through LeLab, using the same audited episode as the [100-action experiment](2026-10-18-wave-single-episode.md). Set `chunk_size=30` and `n_action_steps=30`, run 2,000 updates, save complete checkpoints at 1,000 and 2,000, and compare predictions before any arm test.

Job: `act_local_wave-ep0-audited_20261018_2026-10-18_16-36-00`.

The native LeLab job API starts and manages this run. The pinned UI does not expose ACT chunk settings, and its command builder forwards the similarly named request fields only for GR00T. We therefore use LeLab's supported `config_path` field with [`configs/training/wave-ep0-chunk30.json`](../configs/training/wave-ep0-chunk30.json). No installed package, training code, or server adapter was changed. A dry parse of the exact generated command verified the effective settings before submission; the actual training log independently confirms both values are 30.

The dataset is still `local/wave-ep0-audited_20261018`: one episode, 556 frames, 30 fps, two recorded camera streams. Training uses MPS, batch size 1, workers 0, seed 1000, PyAV, logging every 50 updates, and saving every 1,000. The policy preset remains AdamW at 1e-5, weight decay 1e-4, gradient clipping 10, VAE enabled, KL weight 10, dropout 0.1, and the pretrained ResNet18 backbone. Resume, Hub upload, and W&B are disabled. This is fresh policy initialization, not a conversion of the old checkpoint.

A fresh target audit with the 30-action configuration passed ordering, padding, timestamps, joint order, and normalization round trips on ten observations, including episode-end samples. Target shape is `[1, 30, 6]`; the largest inverse-normalization error is 0.00000191 action units.

The JSON configuration is portable: it contains no Mac-specific output path, dataset root, or checkpoint path. The local request resolves the configuration file to an absolute path on the machine running LeLab. LeLab's normal runner assigns a new output directory and displays the job in its UI. The generated model architecture differs in chunk-dependent shapes, so using the same seed does not imply all initial tensors are identical.

The first saved checkpoint confirms the effective configuration differs from the old run only in chunk size, action steps, job name, and output directory. Its saved normalizer tensors are identical to the old run's tensors. This checks the actual saved settings, not just the submitted request.

## Evaluation protocol

The comparison uses the first **30 targets** from each policy's native prediction, not the full 100-action prediction against a 30-action prediction. Both old checkpoints and both new checkpoints see the same recorded observation frames, with their own saved processors. CPU inference keeps the evaluation backend consistent. No future targets enter the inference inputs.

`scripts/check_act_wave.py --stride-frames 30 --horizon-frames 30` samples each second plus the last frame: 20 observations in total. Wave statistics cover seconds 5 through 11 inclusive (seven observations). Targets are clipped at the end of the episode. The demonstrated mean pan range on these windows is **26.788°**. The original chunk-100 model's 2,000-update checkpoint predicts a mean range of **0.0246°**, with **13.957°** pan mean absolute error on this matching horizon. These values differ from the earlier full-chunk report because the evaluation horizon changed.

An independent check confirmed that all 40 baseline windows (20 per old checkpoint) equal the first 30 predictions from the earlier full-chunk evaluation, match the raw recorded targets, and have correctly recomputed errors. Dataset file hashes match the preparation manifest, and both old checkpoint manifests remain unchanged.

The native LeLab job finished with exit code 0 in **11 minutes 33 seconds**. Both requested complete checkpoints are present and selectable in LeLab. Each checkpoint contains **618,987,865 bytes** across model, processors, configuration, and training state. Strict weight loading passed; all 153 optimizer parameter states restored at the correct step, RNG state restored, and model, optimizer, and prediction tensors were finite. The final saved configuration and normalization also passed the comparison described above.

| Chunk size | Updates | Mean predicted pan range | Pan mean absolute error |
| --- | ---: | ---: | ---: |
| 100 | 1,000 | 0.0252° | 14.547° |
| 100 | 2,000 | 0.0246° | 13.957° |
| 30 | 1,000 | 0.0532° | 9.407° |
| 30 | 2,000 | 0.1230° | 9.419° |

The demonstration spans **26.788°** on average across these same windows. At 2,000 updates, chunk 30 reduces pan error by about **32.5%** relative to chunk 100, but its mean predicted range is still only **0.123°**—less than 0.5% of the demonstrated range. It has learned closer target positions without reproducing the wave trajectory. Error did not improve between the new 1,000- and 2,000-update checkpoints.

For example, from the observation at second 7 the demonstrated endpoint change is **+40.527°**, while the final model predicts **+0.0026°**. At second 11 the corresponding changes are **−45.538°** and **−0.0462°**. These examples show why lower average position error alone is insufficient.

### Other joints

| Joint | MAE: chunk 100 at 2,000 | MAE: chunk 30 at 2,000 | Demonstrated range | Predicted range: chunk 30 |
| --- | ---: | ---: | ---: | ---: |
| Shoulder pan | 13.9571° | 9.4186° | 26.7881° | 0.12303° |
| Shoulder lift | 0.9004° | 3.0694° | 0.3265° | 0.13785° |
| Elbow flex | 4.0523° | 4.4080° | 0.7786° | 0.13395° |
| Wrist flex | 0.3588° | 0.6114° | 0.1256° | 0.03439° |
| Wrist roll | 0.1695° | 0.1323° | 0.3014° | 0.00308° |
| Gripper | 0.0106 units | 0.0106 units | 0.0336 units | 0.00016 units |

All joint statistics use the same seven wave-phase windows. Shoulder-lift, elbow, and wrist-flex errors are worse than the old model at the same step count, so the pan improvement is not a general improvement across joints. The gripper uses the project’s 0–100 convention.

A second-7 check on MPS returned shape `(30, 6)` and a pan range of **0.13898°**, consistent with CPU evaluation of that observation. The four-panel pan chart and six-joint charts compare identical target windows. These checks use recorded training observations, not held-out data or a closed-loop rollout.

**No arm test was started.** The shorter horizon did not solve the missing wave in this bounded, single-seed comparison. The next focused experiment remains a fixed-observation/fixed-target memorization test, with intermediate prediction checks, to determine whether the sequence decoder can fit a known changing target. That experiment has not been started.

## Local evidence and reproduction

- Portable training configuration: `configs/training/wave-ep0-chunk30.json`.
- Submitted native API payload and returned job: `.cache/wave-chunk30-request.json`, `.cache/wave-chunk30-job.json`.
- Training target audit: `.cache/wave-chunk30-target-audit.json` and matching log.
- Matching-horizon baseline checks: `.cache/wave-chunk100-horizon30.json` and matching log.

After training, compare any selected step directories with:

```sh
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 .cache/lelab/venv/bin/python scripts/check_act_wave.py \
  --checkpoint "$old_step_directory" \
  --checkpoint "$new_step_directory" \
  --dataset-root data/lelab/local/wave-ep0-audited_20261018 \
  --repo-id local/wave-ep0-audited_20261018 \
  --stride-frames 30 --horizon-frames 30 --device cpu \
  --output .cache/chunk-comparison.json
```

`old_step_directory` and `new_step_directory` are complete checkpoint directories containing `pretrained_model/` and `training_state/`. See [Inspecting ACT](../docs/INSPECTING_ACT.md) for plotting commands. All evaluations use recorded training observations; they do not establish generalization or physical rollout success.

Final local evidence: `.cache/wave-chunk30-step1000.json`, `.cache/wave-chunk30-step2000.json`, `.cache/wave-chunk30-comparison.json`, `.cache/wave-chunk30-config-validation.json`, `.cache/wave-horizon30-validation.json`, `.cache/inspect-chunk30-example.log`, `.cache/wave-chunk30-shoulder_pan.png`, and the corresponding all-joint charts. Recordings and checkpoints remain local.
