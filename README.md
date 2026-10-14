# VLA-Adapter for SO-101

Build a language-conditioned policy for one SO-101 follower arm, using an SO-101 leader for demonstrations and [VLA-Adapter](https://vla-adapter.github.io/) for learning.

Repository: [carneym/vla-adapter-test](https://github.com/carneym/vla-adapter-test).

**Status: functioning teleoperation confirmed on the MacBook, with a 5° relative target limit.** Setup helpers, machine-local settings, calibration import, teleoperation command generation, and a simultaneous camera check are available. See the [teleoperation checkpoint](reports/2026-10-14-teleoperation.md) for evidence and remaining hardware checks. VLA-Adapter data conversion, training, and inference remain planned.

Both cameras passed the 60-second capture timing test at 640×480 / 30 fps. Overhead framing still needs adjustment before demonstrations; see the [camera checkpoint](reports/2026-10-14-cameras.md).

## Set up this Mac

```sh
bash scripts/setup.sh macbook
uv run --locked so101 ports
uv run --locked so101 calibrations
```

The setup installs the pinned dependencies into `.venv`, preserves existing local settings, and runs a software/video smoke test without accessing cameras or motors. On a new Mac mini checkout, use `bash scripts/setup.sh mac-mini`. See [SETUP.md](docs/SETUP.md) for selecting the working calibration, camera discovery, and migration between computers.

## Target tasks

- Pick up a pencil, eyeglasses, or a cable (three separate task labels).
- Raise the arm.
- Wave.
- Pull a tissue from a box, raise it, and hold it at a taught position.
- Put the held tissue away as a separate task.
- Pick up a cup.

## Intended setup

| Component | Responsibility |
| --- | --- |
| M2 MacBook Air (8 GB), initial host; M4 Mac mini (16 GB), later option | Setup, calibration, camera capture, leader/follower teleoperation, recording, and local motor control |
| Modal GPU | VLA-Adapter training, with a USD 20 total initial experiment budget |
| Inference host | Local or online; select after measuring compatibility, latency, and cost. Offline operation is not required |
| Cameras | USB2.0_CAM1 wrist camera and Logi 4K Pro overhead camera; initial capture mode 640×480 at 30 fps |

Keep the robot interface separate from the CUDA training environment. Use LeRobot's SO-101 hardware support, retain its calibration, and add an explicit six-channel SO-101 adapter to VLA-Adapter.

Both arms are assembled and already moving through an existing LeRobot setup. This repository installs a separate pinned environment and imports chosen calibration files without changing the originals; motor provisioning should normally be skipped.

## Start here

1. Review the [checkpoint plan](docs/PLAN.md).
2. Confirm the [task definitions](docs/TASKS.md) and [open decisions](docs/DECISIONS.md).
3. Read the [simple calibration workflow](docs/CALIBRATION.md).
4. Run the software checks in the project environment:

   ```sh
   uv run --locked so101 doctor --check
   ```

The check does not open serial ports, turn on motors, access cameras, upload data, or start Modal jobs. A passing software check can still list missing hardware configuration as `PENDING`.

## Checkpoints

| Gate | What you can test |
| --- | --- |
| C0 | Hardware/compute inventory and task definitions |
| C1 | Detect both arms and preview cameras |
| C2 | Validate saved calibration, reconnect, and verify leader/follower movement; recalibrate only if needed |
| C3 | Record and inspect five demonstrations |
| C4 | Train a tiny VLA-Adapter run on Modal and verify the six-channel data contract |
| C5 | Measure inference and prove stopping behavior without sending policy actions to the arm |
| C6 | Learn and test raise-arm and wave |
| C7 | Learn and test each pickup task |
| C8 | Learn tissue extraction/presentation and put-away; evaluate all tasks together |

Every gate produces evidence and a repeatable test. A failed gate stays open; improving a model must not erase earlier failures from the evaluation record.

## Project layout

```text
configs/hardware.example.json    Unconfigured hardware inventory template
pyproject.toml / uv.lock         Pinned Apple Silicon control environment
scripts/setup.sh                Repeatable setup for either Mac
src/so101_setup/                Local config, calibration import, checks, command generation
docs/SETUP.md                   Install, verify, and move between Macs
docs/PLAN.md                    Architecture, implementation work, and test gates
docs/CALIBRATION.md             First setup and daily startup design
docs/TASKS.md                   Task labels and proposed success criteria
docs/DECISIONS.md               Confirmed decisions and unanswered questions
docs/SOURCES.md                 Upstream references and integration findings
scripts/doctor.py               Legacy read-only inventory for any Python
reports/checkpoint-template.md  Evidence template for each completed gate
```

Datasets, camera recordings, model weights, local hardware settings, and credentials stay out of Git. The USD 20 budget is recorded but spending controls are not yet implemented; no paid jobs have run. Dataset sharing will be configured explicitly. Licensing for this project's original code is undecided; upstream components retain their own licenses.
