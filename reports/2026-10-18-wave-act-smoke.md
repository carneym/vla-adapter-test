# MacBook wave ACT smoke run — 2026-10-18

**Training result: all 50 updates completed and a complete checkpoint passed offline reload checks. Physical result: the first reported trial raised the arm but did not wave.** LeLab reports training **done**, exit code **0**. The run took **43.6 seconds**, including initialization and saving. The sequence diagnostic below shows that the checkpoint predicts almost constant shoulder-pan targets during recorded wave observations.

## Dataset and camera recovery

The operator completed five wave demonstrations after restarting the idle LeLab server. This confirms successful recording recovery after the earlier camera startup timeouts. The session ended normally with both cameras and arms disconnected; no camera timeout occurred in this completed session.

- Dataset: `local/wave-c6_20261018_150106`, task `Wave.`
- Five episodes with 556, 438, 436, 485, and 478 frames: **2,393 total**, at 30 fps.
- Both 640×480 H.264 videos decoded completely, each yielding 2,393 frames. Video timestamps, table frame indices, and episode boundaries matched.
- All six state and action channels were finite. Actions retain the leader-requested target semantics documented in [Recording](../docs/RECORDING.md#action-meaning-and-training).
- Sampled images from each episode showed the arm raising, changing its side-to-side position, and returning to rest. This spot check does not certify an exact count of three wave cycles or assess every frame for demonstration quality.

Local validation evidence: `.cache/wave-dataset-validation.json`, `.cache/wave-overhead-review.jpg`, and `.cache/wave-wrist-review.jpg`. Dataset and images remain outside Git.

## Training

Job: `act_local_wave-c6_20261018_150106_2026-10-18_15-07-09`.

The standard LeLab UI launched a fresh ACT policy on the M2 MacBook Air's Apple GPU (`mps`). Settings matched the successful raise-arm smoke run: 50 updates, batch size 1, workers 0, seed 1000, log every 10 updates, save at 50, AMP off, W&B off, and resume off. The policy preset supplies AdamW at learning rate 1e-5, weight decay 1e-4, and gradient clipping 10. The model has 51,597,190 parameters, an ImageNet-initialized ResNet18 backbone, and chunk size 100. The project adapter selects PyAV decoding.

All five episodes were available to the shuffled sampler. Fifty batch-size-one updates cover about 0.021 dataset epochs, not a complete pass through the demonstrations. The existing raise-arm checkpoint was not used as the starting policy and remains available separately. No Hub upload or paid compute was used.

| Update | Training loss, averaged over 10 updates |
| --- | ---: |
| 10 | 46.157 |
| 20 | 19.321 |
| 30 | 17.969 |
| 40 | 12.680 |
| 50 | 11.677 |

Loss combines ACT's action L1 and weighted KL terms. The decline is evidence of optimization, not a measurement of successful waving or generalization.

## Complete checkpoint

Path relative to the user's home directory:

```text
.cache/huggingface/lerobot/outputs/train/
  act_local_wave-c6_20261018_150106_2026-10-18_15-07-09/
    run/checkpoints/000050/
```

The checkpoint contains **619,561,302 bytes** (about 591 MiB): model weights, policy/training configuration, normalization processors, AdamW tensors and parameter groups, RNG state, and step metadata. The `last` symlink resolves to `000050`. About 10 GiB remained free after training and verification.

Verification strictly reloaded the saved model on MPS with its saved pre/postprocessors. Restoring training state returned step 50; all 153 optimizer parameter states were finite with step 50. RNG restoration passed; this ACT preset has no scheduler. A fresh offline prediction from the first frame of each episode returned finite `[1, 6]` actions. Every checkpoint file was hashed in `.cache/wave-act-complete-validation.json`; the full verification log is `.cache/wave-act-complete-validation.log`. No extra gradient update or physical rollout was performed during validation.

## First physical trial and sequence diagnostic

The operator reported: "it raised the arm but didn't do the waving motion." Count this as an unsuccessful wave trial, not a completed gesture.

The matching rollout log, `~/.cache/huggingface/lerobot/inference_logs/1792333818.log`, confirms that the **wave** job's step-50 checkpoint was loaded on MPS. Both cameras connected, the control loop ran for its full **60-second** limit, and teardown finished normally with automatic return disabled. No camera timeout occurred. The missing wave cannot be attributed to selecting the raise-arm checkpoint or stopping before the demonstrated wave phase.

The five demonstrations last 14.5–18.5 seconds. Substantial shoulder-pan motion (more than 8° from each episode's initial pan position) begins 4.6–6.7 seconds into the episodes. Recorded pan excursions span approximately 55–67° per episode. There are repeated direction changes in the recorded state and target data.

An offline diagnostic supplied the model with 35 recorded observations: seconds 0, 3, 5, 7, 9, 11, and 13 from each episode. It predicted each 100-action chunk and applied the saved output normalization. For the 20 wave-phase observations at seconds 5, 7, 9, and 11:

| Shoulder-pan measurement | Result |
| --- | ---: |
| Mean range within recorded target chunks | 58.14° |
| Mean range within predicted chunks | 0.63° |
| Mean absolute chunk prediction error | 16.90° |
| First predicted pan target across these observations | −20.36° to −18.29° |

The model predicts almost stationary pan targets even when given training-set observations from the wave. This is direct evidence that the 50-update checkpoint has not fitted the side-to-side sequence. It supports insufficient training as the next issue to address; it does not prove that more updates alone will solve phase ambiguity, demonstration variation, or closed-loop drift.

The rollout also logged 79 target-clamp warnings and 18 slow iterations (1.4 Hz initially, then 6.1–7.6 Hz). These are individual iteration rates, not the mean control rate. The policy executes chunks of 100 actions, so periodic slow model refreshes need separate timing evaluation. Do not infer that the entire run operated at 7 Hz or remove the 5° target cap to compensate for an almost constant predicted trajectory.

Local evidence: `.cache/wave-first-inference-summary.json`, `.cache/wave-act-sequence-diagnostic.json`, and `.cache/wave-act-sequence-diagnostic.log`. These checks use recorded training observations; they are not held-out evaluation or a simulated physical rollout. No new robot motion or training update was performed during diagnosis.

Follow-up: the requested [1,000-update run and offline comparison](2026-10-18-wave-act-1000.md) is now complete. Both checkpoints are intact, but neither predicts the wave, and no new arm trial was started.

The original next-step proposal was a local **1,000-update** wave run on the same data with batch size 1, MPS, workers 0, and checkpoints at 500 and 1,000. Based on the measured update time, budget roughly 6–8 minutes, not a guaranteed runtime. Compare predicted motion with the recorded sequence before another supervised arm trial. Add or refine demonstrations if a longer run still cannot reproduce the motion. This remains an incremental experiment; the [official ACT guide](https://huggingface.co/docs/lerobot/act) describes much longer training schedules. C6 remains open.
