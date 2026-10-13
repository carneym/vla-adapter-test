# Decisions and open questions

Updated 2026-10-13.

## Confirmed by the user

- Base the project on VLA-Adapter.
- Use an SO-ARM101 leader and follower for demonstration training.
- Cover pickup of a pencil/glasses/cable, raise-arm, wave, tissue presentation, and cup pickup.
- Make calibration as simple as possible.
- Provide checkpoints that can be tested during development.
- Create a GitHub repository.
- Use either the M2 MacBook or M4 Mac mini to control the arms; Modal is available for training.
- Cameras: one wrist camera and one overhead 4K camera.
- “Glasses” means eyeglasses.
- Pull the tissue from a box, raise and hold it, then put it away; put-away may be a separate trained action.
- Both raise-arm and wave must be learned. Recorded motions are only for hardware tests.
- Use a command-line interface and start with raise-arm.
- Both arms are assembled and already moving through software.
- The M2 MacBook Air has 8 GB RAM; the M4 Mac mini has 16 GB RAM.
- Put the tissue down beside the box and release it. Release is permitted; exact destinations for other pickups remain open.
- The arms are already controlled with LeRobot; reuse the working setup and calibration.
- Initial Modal budget: USD 20 total, not USD 20 per job.
- Offline operation is not required. Online inference is an option, subject to measured latency and local stopping behavior.
- Start on the M2 MacBook Air (8 GB); make the repository portable to the Mac mini.

## Proposed defaults

- LeRobot for SO-101 hardware, calibration, and recording.
- Separate Mac control and Linux/CUDA training environments.
- Keep raw recordings and checkpoints out of Git; uploads off during initial collection.
- Persist calibration by arm identity and verify it on startup.
- Use both camera views with consistent preprocessing; measure capture modes and throughput.
- Start with raise-arm; evaluate eight tasks individually before a combined policy.
- Use guided prompts inside the command-line setup.
- Keep the 16 GB Mac mini as a later option; the MacBook is the initial controller.
- Inspect the existing working robot environment and preserve its calibration before making changes.

## Awaiting answers

1. Existing LeRobot version/environment, calibration location, arm vendor/version, controller and power supply details.
2. Camera models, USB connectivity, modes, and existing mounts.
3. Exact object/task details listed in [TASKS.md](TASKS.md), particularly pickup destination/hold behavior, cable, cup load, tissue presentation position, and exact beside-box put-away area.
4. Desired final success rate, object/scene variation, and whether human handoff is in scope.

These questions do not block repository planning. Hardware-specific implementation and training settings should use the answers rather than guessed device configurations.

## Implemented environment

The control environment pins LeRobot 0.6.1 with hardware/recording extras and Feetech support, Python 3.12, and the compatible PyTorch/torchvision versions in `uv.lock`. It is isolated from other LeRobot installations. `so101` helpers manage ignored local configuration and explicitly selected calibration copies. The tested video decoding path is PyAV; no system FFmpeg install is required for that path. See [SETUP.md](SETUP.md).

## Repository destination

The GitHub setup tab showed the newly created, empty public repository `carneym/vla-adapter-test`; its identity, visibility, and write access were verified through the GitHub connector. Use it for this workspace rather than create a second repository.
