"""Offline ACT checkpoint/sequence checks using recorded wave observations only.

Run with the pinned LeLab Python. No robot or live-camera connection is made.
Outputs stay local; these training-set checks do not establish rollout success.
"""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, action="append", required=True,
                        help="Step directory containing pretrained_model/ and training_state/; repeat to compare")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("mps", "cpu"), default="mps")
    args = parser.parse_args()

    import numpy as np
    import pyarrow.parquet as pq
    import torch
    from lerobot.common.train_utils import load_training_state
    from lerobot.configs import PreTrainedConfig
    from lerobot.configs.train import TrainPipelineConfig
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.optim.factory import make_optimizer_and_scheduler
    from lerobot.policies.act.modeling_act import ACTPolicy
    from lerobot.policies.factory import make_pre_post_processors

    root = args.dataset_root.resolve()
    info = json.loads((root / "meta/info.json").read_text())
    if info["fps"] != 30:
        raise ValueError("This wave comparison protocol expects a 30 fps dataset.")
    names = info["features"]["action"]["names"]
    pan_index = names.index("shoulder_pan.pos")
    episodes = []
    for path in sorted((root / "meta/episodes").rglob("*.parquet")):
        episodes.extend(pq.read_table(path).to_pylist())
    episodes.sort(key=lambda e: e["episode_index"])
    table = pq.read_table(sorted((root / "data").rglob("*.parquet")))
    # Sort by the dataset index so file/chunk enumeration cannot reorder targets.
    table = table.sort_by([("index", "ascending")])
    if table.column("index").to_pylist() != list(range(info["total_frames"])):
        raise ValueError("Dataset row indices are incomplete or duplicated.")
    actions = np.asarray(table.column("action").to_pylist())
    if not np.isfinite(actions).all():
        raise ValueError("Dataset actions contain nonfinite values.")
    dataset = LeRobotDataset(args.repo_id, root=root, video_backend="pyav")
    result = {
        "dataset": args.repo_id,
        "evaluation": "Recorded training observations, not held-out or closed-loop evaluation.",
        "protocol_seconds": [0, 3, 5, 7, 9, 11, 13],
        "wave_phase_seconds": [5, 7, 9, 11],
        "joint_names": names,
        "robot_connected": False,
        "extra_training_updates": 0,
        "checkpoints": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    for step_dir in args.checkpoint:
        step_dir = step_dir.resolve()
        pretrained = step_dir / "pretrained_model"
        expected_step = json.loads((step_dir / "training_state/training_step.json").read_text())["step"]
        config = PreTrainedConfig.from_pretrained(pretrained, local_files_only=True)
        config.device = args.device
        config.pretrained_backbone_weights = None
        policy = ACTPolicy.from_pretrained(pretrained, config=config, local_files_only=True, strict=True)
        if not all(torch.isfinite(p).all().item() for p in policy.parameters()):
            raise ValueError(f"Nonfinite model parameters in {step_dir}")
        train_config = TrainPipelineConfig.from_pretrained(pretrained, local_files_only=True)
        optimizer, scheduler = make_optimizer_and_scheduler(train_config, policy)
        step, optimizer, scheduler = load_training_state(step_dir, optimizer, scheduler)
        if step != expected_step or not optimizer.state:
            raise ValueError(f"Training state did not restore at step {expected_step}")
        optimizer_steps = set()
        for state in optimizer.state.values():
            optimizer_steps.add(int(state["step"].item()))
            for value in state.values():
                if isinstance(value, torch.Tensor) and not torch.isfinite(value).all().item():
                    raise ValueError("Nonfinite optimizer state")
        if optimizer_steps != {expected_step}:
            raise ValueError(f"Unexpected optimizer steps: {optimizer_steps}")
        optimizer_count = len(optimizer.state)
        del optimizer, scheduler
        pre, post = make_pre_post_processors(config, pretrained_path=str(pretrained))
        checks = []
        for ep in episodes:
            start, end = ep["dataset_from_index"], ep["dataset_to_index"]
            if end - start != ep["length"] or ep["tasks"] != ["Wave."]:
                raise ValueError("Unexpected wave episode metadata")
            for sec in result["protocol_seconds"]:
                index = start + sec * info["fps"]
                if index >= end:
                    raise ValueError(f"Episode {ep['episode_index']} is too short for the fixed protocol")
                sample = dataset[index]
                policy.reset()
                pre.reset()
                post.reset()
                with torch.inference_mode():
                    chunk = post(policy.predict_action_chunk(
                        pre({k: sample[k] for k in config.input_features})
                    )[0]).cpu().numpy()
                if chunk.ndim != 2 or chunk.shape[1] != len(names) or not np.isfinite(chunk).all():
                    raise ValueError("Invalid action chunk")
                n = min(len(chunk), end - index)
                true = actions[index:index + n]
                checks.append({
                    "episode": ep["episode_index"], "seconds": sec, "index": index,
                    "target_pan_deg": float(true[0, pan_index]),
                    "predicted_pan_deg": float(chunk[0, pan_index]),
                    "target_pan_chunk_range_deg": float(np.ptp(true[:, pan_index])),
                    "predicted_pan_chunk_range_deg": float(np.ptp(chunk[:n, pan_index])),
                    "pan_chunk_mae_deg": float(np.abs(chunk[:n, pan_index] - true[:, pan_index]).mean()),
                    "per_joint_chunk_mae": np.abs(chunk[:n] - true).mean(axis=0).tolist(),
                    "pan_target": true[:, pan_index].tolist(),
                    "pan_prediction": chunk[:n, pan_index].tolist(),
                })
        active = [c for c in checks if c["seconds"] in result["wave_phase_seconds"]]
        manifest = []
        for path in sorted(step_dir.rglob("*")):
            if path.is_file():
                with path.open("rb") as handle:
                    digest = hashlib.file_digest(handle, "sha256").hexdigest()
                manifest.append({"path": str(path.relative_to(step_dir)), "bytes": path.stat().st_size,
                                 "sha256": digest})
        entry = {
            "checkpoint": str(step_dir), "step": step, "device": str(next(policy.parameters()).device),
            "sample_count": len(checks), "strict_weights_load": True,
            "optimizer_parameter_states": optimizer_count, "optimizer_steps": sorted(optimizer_steps),
            "optimizer_state_finite": True, "rng_restored": True,
            "checkpoint_bytes": sum(f["bytes"] for f in manifest),
            "wave_phase": {
                "samples": len(active),
                "mean_pan_chunk_mae_deg": float(np.mean([c["pan_chunk_mae_deg"] for c in active])),
                "mean_predicted_chunk_pan_range_deg": float(np.mean([c["predicted_pan_chunk_range_deg"] for c in active])),
                "mean_recorded_chunk_pan_range_deg": float(np.mean([c["target_pan_chunk_range_deg"] for c in active])),
                "per_joint_chunk_mae": np.mean([c["per_joint_chunk_mae"] for c in active], axis=0).tolist(),
            },
            "samples": checks, "files": manifest,
        }
        result["checkpoints"].append(entry)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({k: v for k, v in entry.items() if k not in ("samples", "files")}, indent=2), flush=True)
        del policy, pre, post
        if args.device == "mps":
            torch.mps.empty_cache()


if __name__ == "__main__":
    main()
