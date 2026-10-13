# Sources and integration findings

Reviewed 2026-10-13. Upstream branches and documentation may change; concrete revisions must be pinned and tested during implementation.

| Source | Finding / use |
| --- | --- |
| [VLA-Adapter project](https://vla-adapter.github.io/) | Research architecture and benchmark results; benchmark timing/success is not a prediction for these tasks |
| [Official implementation](https://github.com/OpenHelix-Team/VLA-Adapter) | Start from the maintained model implementation, including its Pro option |
| [Installation and training](https://github.com/OpenHelix-Team/VLA-Adapter/blob/main/README.md) | Published CUDA/FlashAttention training environment and GPU memory configurations; use an isolated Linux environment |
| [ALOHA real-world pipeline](https://github.com/OpenHelix-Team/VLA-Adapter/tree/main/experiments/robot/aloha) | Example of real data training and server/client inference; its bimanual robot interface does not establish SO-101 compatibility |
| [Embodiment constants](https://github.com/OpenHelix-Team/VLA-Adapter/blob/main/prismatic/vla/constants.py) | Current code selects LIBERO/CALVIN/BRIDGE/ALOHA and defaults to LIBERO; SO-101 needs an explicit six-channel configuration |
| [LeRobot SO-101 setup](https://huggingface.co/docs/lerobot/so101) | Motor provisioning, leader/follower setup, and manual calibration procedure |
| [LeRobot imitation learning](https://huggingface.co/docs/lerobot/il_robots) | Stable calibration IDs, teleoperation, recording, inspection, and upload controls |
| [Modal GPUs](https://modal.com/docs/guide/gpu) | GPU allocation and hardware choices for the training image |
| [Modal Volumes](https://modal.com/docs/guide/volumes) | Persistent datasets and checkpoints across jobs |

## Integration work that remains

LeRobot collection and VLA-Adapter training are separate systems. We need a verified dataset bridge, matching joint/action conventions, an action head with the right dimensions, stored normalization, camera preprocessing, and a local inference/control client. Changing a robot name in an upstream training command is insufficient.

Apple Silicon policy inference is unverified. CUDA training in Modal is the planned route; policy execution on the Mac is a separate compatibility and latency experiment. Do not present CPU/MPS support or a target frame rate as established until measured with this model and these observations.
