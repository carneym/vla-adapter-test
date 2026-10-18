# Inspect ACT predictions before moving the arm

We can give a saved model a recorded observation and inspect the actions it proposes. This uses the normal inference path, with no serial ports, live cameras, or motor commands. It is a useful first check when a policy raises the arm but does not wave.

## What one prediction contains

For this model, one input contains the overhead RGB image, the wrist RGB image, and six measured joint positions at the same recorded moment. The saved preprocessor adds a batch dimension, normalizes those inputs, and moves them to the selected compute device.

The original ACT checkpoint predicts a tensor of shape **`[1, 100, 6]`**. A checkpoint trained with chunk size 30 instead produces **`[1, 30, 6]`**:

| Dimension | Meaning |
| --- | --- |
| 1 | One input observation |
| 100 | The current action target and 99 future targets, spaced at 1/30 second |
| 6 | Shoulder pan, shoulder lift, elbow flex, wrist flex, wrist roll, gripper |

The saved postprocessor converts the output back to action units. The first five joints use degrees in this project; the gripper uses its 0–100 convention. Look up column names in dataset metadata rather than assuming every robot uses this order.

For a wave, the shoulder-pan column should change direction across time. Plot it against the targets recorded after the same observation. **The future recorded targets are not passed into `predict_action_chunk`; they are used only to score and plot the answer afterward.**

## Minimal example on the first episode

Run this with `.cache/lelab/venv/bin/python` in the repository root. This example was verified on MPS using the completed single-episode job. Change the checkpoint path to inspect another saved model. The dataset is the separate audited copy of the first wave take.

```python
from pathlib import Path
import torch
from lerobot.configs import PreTrainedConfig
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.factory import make_pre_post_processors

checkpoint = (
    Path.home() / '.cache/huggingface/lerobot/outputs/train'
    / 'act_local_wave-ep0-audited_20261018_2026-10-18_15-59-53'
    / 'run/checkpoints/002000/pretrained_model'
)
cfg = PreTrainedConfig.from_pretrained(checkpoint, local_files_only=True)
cfg.device = 'mps'  # Use 'cpu' for a CPU-only inspection.
cfg.pretrained_backbone_weights = None  # All trained weights come from the checkpoint.
model = ACTPolicy.from_pretrained(
    checkpoint, config=cfg, local_files_only=True, strict=True
).eval()
pre, post = make_pre_post_processors(
    cfg, pretrained_path=str(checkpoint),
    preprocessor_overrides={'device_processor': {'device': cfg.device}},
)
dataset = LeRobotDataset(
    'local/wave-ep0-audited_20261018',
    root=Path('data/lelab/local/wave-ep0-audited_20261018'),
    video_backend='pyav',
)

observation = dataset[7 * 30]  # Seven seconds into episode 0.
inputs = {name: observation[name] for name in cfg.input_features}
with torch.inference_mode():
    normalized_chunk = model.predict_action_chunk(pre(inputs))
    actions = post(normalized_chunk[0]).cpu().numpy()  # [100, 6]

pan_column = dataset.meta.features['action']['names'].index('shoulder_pan.pos')
pan = actions[:, pan_column]
print('action shape:', actions.shape)
print('first ten pan targets:', pan[:10])
print('predicted pan range in degrees:', pan.max() - pan.min())
```

`torch.inference_mode()` disables gradient tracking, and evaluation mode disables training dropout. These calls do not update the model. `predict_action_chunk` exposes the whole sequence; the normal `select_action` interface returns one queued action at a time, which makes the sequence harder to inspect.

## Repeatable comparison and plots

[`scripts/check_act_wave.py`](../scripts/check_act_wave.py) performs the complete check, including strict checkpoint loading, optimizer/RNG/step restoration, finite-value checks, inverse normalization, and comparison against the raw action table. It clips comparisons at episode boundaries so targets from another episode cannot enter the score.

```sh
wave_run="$HOME/.cache/huggingface/lerobot/outputs/train/act_local_wave-ep0-audited_20261018_2026-10-18_15-59-53"
HF_HUB_OFFLINE=1 .cache/lelab/venv/bin/python scripts/check_act_wave.py \
  --checkpoint "$wave_run/run/checkpoints/001000" \
  --checkpoint "$wave_run/run/checkpoints/002000" \
  --dataset-root data/lelab/local/wave-ep0-audited_20261018 \
  --repo-id local/wave-ep0-audited_20261018 \
  --stride-frames 30 \
  --output .cache/my-wave-comparison.json

MPLCONFIGDIR=.cache/matplotlib uv run --no-project --python 3.12 --with matplotlib \
  python scripts/plot_act_wave.py \
  --comparison .cache/my-wave-comparison.json \
  --output .cache/my-wave-comparison.png \
  --joint all
```

`--joint all` writes six four-panel charts (observations at 5, 7, 9, and 11 seconds) plus an all-joint overview at second 7. Use `--joint elbow_flex.pos` to inspect only the elbow, or change `--overview-seconds` to another sampled observation. Each joint uses its own labeled vertical scale; gripper units differ from joint angles. Stationary channels get a minimum one-unit vertical span so tiny numerical differences are not visually inflated.

Each plot starts from a fresh recorded observation. Black is the demonstrated future target; colored curves are model predictions. A flat predicted line means the model proposes holding approximately the same joint target over that chunk. The reported range is `max − min` within each chunk, averaged over the selected observations. It is not motor speed or the follower's separate 5° relative-target cap.

Look at both **trajectory shape** and **error**: a large oscillation with the wrong timing can still fail. Useful questions include whether direction reversals occur at the right times, whether motion is too small, whether a particular joint dominates the error, and whether the model works across different observations rather than one convenient frame.

## Compare different chunk sizes

Add `--horizon-frames 30` to `check_act_wave.py` when comparing 30-action and 100-action policies. Both policies still generate their complete native chunks, but scoring and plotting use only the first 30 targets from each. Near the episode end, both are clipped to the remaining recorded targets. The checker rejects a horizon longer than any checkpoint's chunk size and verifies that decoded images are float32 RGB in [0, 1].

This prevents a longer chunk from appearing to have better movement simply because it covers more time. Inspect error and direction against the same targets, at the same observations. Prediction ranges alone do not establish success. The output records each checkpoint's native `chunk_size`, `n_action_steps`, and endpoint pan change.

The [chunk-30 experiment](../reports/2026-10-18-wave-act-chunk30.md) uses the same audited episode and a fresh model. Its portable training settings are in [`configs/training/wave-ep0-chunk30.json`](../configs/training/wave-ep0-chunk30.json).

These are recorded training observations. They can expose failure to fit data, but a good fit does not prove success from new scenes or during a physical rollout, where the model's own actions change subsequent observations. This check also does not reveal a model's internal reasoning. It directly measures the output of its inference computation.

See the [target audit and single-episode experiment](../reports/2026-10-18-wave-single-episode.md) for this project's evidence and limitations.
