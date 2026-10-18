# MacBook wave ACT smoke run — 2026-10-18

**Result: all 50 updates completed and a complete checkpoint passed offline reload checks.** LeLab reports **done**, exit code **0**. The run took **43.6 seconds**, including initialization and saving. Wave-policy performance on the arm remains untested.

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

Next checkpoint: a supervised wave-policy test through standard LeLab, followed by additional demonstrations or training based on the observed behavior. This run verifies the training/checkpoint pipeline and does not complete C6's physical success evaluation.
