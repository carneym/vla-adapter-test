# Task definitions

User intent: the original five task groups plus a separate tissue put-away action, represented as eight instruction labels. Details and thresholds below are proposals awaiting confirmation, not observed capabilities.

| ID | Instruction | Proposed success definition | Needs confirmation |
| --- | --- | --- | --- |
| `raise_arm` | Raise your arm. | Reach taught raised pose, hold for 2 seconds | Pose/height and allowed start positions |
| `wave` | Wave. | Reach taught raised pose, perform 3 visible cycles within the taught envelope, return to rest | Side-to-side versus wrist motion; final pose |
| `pick_cup` | Pick up the cup. | Grasp, lift at least 5 cm, hold for 3 seconds | Cup material, size, empty/full, handle/body grasp, destination |
| `pick_pencil` | Pick up the pencil. | Lift at least 5 cm and hold for 3 seconds | Pencil type, surface, orientation range, destination |
| `pick_glasses` | Pick up the glasses. | Lift at least 5 cm and hold for 3 seconds without damage | Confirmed eyeglasses; folded/open and grip point pending |
| `pick_cable` | Pick up the cable. | Lift the agreed segment at least 5 cm and hold for 3 seconds without snagging | Cable type/length, loose or connected, whole cable or one end |
| `present_tissue` | Pull a tissue from the box and hold it up. | Extract one tissue from the box, reach taught raised pose, hold for 3 seconds without tearing/dropping | Box extraction confirmed; raised position and hold duration pending |
| `put_away_tissue` | Put the tissue beside the box. | Lower the held tissue into a marked area beside the box, release, and return to rest | Exact area and final rest pose; beside-box release confirmed |

Use task labels consistently in demonstrations, training, commands, and evaluation. Fix simple prompts at first; add paraphrases after establishing performance. Treat tissue put-away as a separate instruction with a clearly specified held-tissue start state; evaluate the combined sequence after both skills pass individually.

The initial [wave collection recipe](RECORDING.md#teach-wave) uses the lowered start pose, a raised pose visible to the overhead camera, three gentle side-to-side cycles, and a return to rest with a two-second hold. This is the working teaching recipe, not an observed wave-policy capability. Keep the demonstrated style consistent across the first five takes. Local ACT tests use a separate checkpoint per skill; task labels alone do not make ACT respond to language instructions.

A single cup dataset should not be described as general object pickup.

The user permits release. For the other pickups, the exact release location and whether release is part of the pickup instruction remain to be defined. The proposed lift-and-hold criteria above isolate the first grasping milestone; a placement/release stage can follow once its target is taught.

## Demonstration rules

- Define start pose, reachable object region, completion, reset, and abort behavior before recording.
- Record follower observations and commanded follower targets while the leader is operated; retain timing and calibration metadata.
- Keep successful episodes as the initial imitation-learning training set. Retain failed/aborted attempts separately for diagnosis.
- Vary positions, rotations, and start states deliberately. Track session identity so evaluation can use unseen sessions.
- Demonstrate the entire agreed behavior, including the hold or placement. Keep manual reset outside the learned task unless intentionally taught.

## Proposed learning order

Raise arm → wave → cup → pencil → eyeglasses → cable → tissue extraction/presentation → tissue put-away. This gives an early visual success and progressively exercises grasping and deformable objects. The user selected raise-arm first and now uses standard LeLab for collection and policy tests; command-line helpers remain available for diagnostics. Both gestures must be learned; recorded motions are only hardware tests.

## Evaluation record

For each trial record task, object/scene variant, model/dataset version, start condition, success/failure, intervention, elapsed time, and failure category. Categories include wrong object, missed grasp, slip/drop, tissue tear/multiple tissues, missed target, timeout, stale observation, and limit violation.

Choose pose tolerance during C2 using actual units and repeatability; choose task timeouts before evaluation. Report both overall completion and substeps. Count intervention as failure for autonomous success rates. Proposed 80% gates are development milestones; final reliability requirements remain open.
