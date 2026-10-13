# VLA-Adapter for SO-101

Build a language-conditioned policy for one SO-101 follower arm, using an SO-101 leader for demonstrations and [VLA-Adapter](https://vla-adapter.github.io/) for learning.

Repository: [carneym/vla-adapter-test](https://github.com/carneym/vla-adapter-test).

**Status: planning and repository bootstrap.** Robot control, the guided command-line setup, data conversion, training, and inference are not implemented yet. No hardware checkpoint has passed.

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
| M4 Mac mini (16 GB), preferred; M2 MacBook Air (8 GB), alternative | Setup, calibration, camera capture, leader/follower teleoperation, recording, and local motor control |
| Modal GPU | VLA-Adapter training, with a USD 20 total initial experiment budget |
| Inference host | Local or online; select after measuring compatibility, latency, and cost. Offline operation is not required |
| Cameras | One wrist camera and one overhead 4K camera; modes and frame rates to be measured |

Keep the robot interface separate from the CUDA training environment. Use LeRobot's SO-101 hardware support, retain its calibration, and add an explicit six-channel SO-101 adapter to VLA-Adapter.

Both arms are assembled and already moving through LeRobot. Begin by inspecting that working setup and preserving its calibration; motor provisioning should normally be skipped. Run the inventory from the existing LeRobot environment so it reports the packages used by the arms.

## Start here

1. Review the [checkpoint plan](docs/PLAN.md).
2. Confirm the [task definitions](docs/TASKS.md) and [open decisions](docs/DECISIONS.md).
3. Read the [simple calibration workflow](docs/CALIBRATION.md).
4. Run the read-only computer inventory:

   ```sh
   python3 scripts/doctor.py
   ```

The inventory does not open serial ports, turn on motors, access cameras, upload data, or start Modal jobs. Missing robot software is expected at this stage.

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
docs/PLAN.md                    Architecture, implementation work, and test gates
docs/CALIBRATION.md             First setup and daily startup design
docs/TASKS.md                   Task labels and proposed success criteria
docs/DECISIONS.md               Confirmed decisions and unanswered questions
docs/SOURCES.md                 Upstream references and integration findings
scripts/doctor.py               Read-only local inventory, standard library only
reports/checkpoint-template.md  Evidence template for each completed gate
```

Datasets, camera recordings, model weights, local hardware settings, and credentials stay out of Git. The USD 20 budget is recorded but spending controls are not yet implemented; no paid jobs have run. Dataset sharing will be configured explicitly. Licensing for this project's original code is undecided; upstream components retain their own licenses.
