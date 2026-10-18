"""Audit the pinned LeRobot ACT data path without cameras, motors, or training."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True, help='pretrained_model directory')
    parser.add_argument('--dataset-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repo-id', help='Override the dataset ID for a prepared copy')
    parser.add_argument('--fresh-processors', action='store_true', help='Audit newly created dataset processors')
    args = parser.parse_args()

    import numpy as np
    import pyarrow.parquet as pq
    import torch
    from torch.utils.data import default_collate
    from safetensors.torch import load_file
    from lerobot.configs.train import TrainPipelineConfig
    from lerobot.datasets.factory import make_dataset
    from lerobot.policies.factory import make_pre_post_processors

    cfg = TrainPipelineConfig.from_pretrained(args.checkpoint, local_files_only=True)
    cfg.dataset.root = args.dataset_root.resolve()
    if args.repo_id:
        cfg.dataset.repo_id = args.repo_id
    cfg.dataset.video_backend = 'pyav'
    cfg.dataset.episodes = None
    cfg.policy.device = 'cpu'
    ds = make_dataset(cfg)
    names = ds.meta.features['action']['names']
    assert ds.meta.features['observation.state']['names'] == names, 'State/action joint ordering differs.'
    assert list(cfg.policy.output_features['action'].shape) == [len(names)]
    if args.fresh_processors:
        pre, post = make_pre_post_processors(cfg.policy, dataset_stats=ds.meta.stats)
    else:
        pre, post = make_pre_post_processors(cfg.policy, pretrained_path=str(args.checkpoint),
            preprocessor_overrides={'device_processor': {'device': 'cpu'}})
    table = pq.read_table(sorted((args.dataset_root / 'data').rglob('*.parquet'))).sort_by([('index','ascending')])
    assert table.column('index').to_pylist() == list(range(len(table)))
    arrays = {k: np.asarray(table.column(k).to_pylist(), dtype=np.float64)
              for k in ('action', 'observation.state')}
    if args.fresh_processors:
        stats = {key+'.'+stat: torch.as_tensor(value, dtype=torch.float32)
                 for key, feature_stats in ds.meta.stats.items() for stat, value in feature_stats.items()}
    else:
        stats = load_file(str(args.checkpoint / 'policy_preprocessor_step_3_normalizer_processor.safetensors'))
    result = {'dataset': cfg.dataset.repo_id, 'joint_names': ds.meta.features['action']['names'],
              'frames': len(table), 'chunk_size': cfg.policy.chunk_size, 'robot_connected': False,
              'statistics': {}, 'samples': []}
    for key, values in arrays.items():
        assert np.isfinite(values).all()
        mean, std = stats[key+'.mean'].numpy(), stats[key+'.std'].numpy()
        normalized = (values-mean)/(std+1e-8)
        result['statistics'][key] = {'stored_mean': mean.tolist(), 'stored_std': std.tolist(),
            'computed_float64_mean': values.mean(axis=0).tolist(),
            'computed_float64_std': values.std(axis=0).tolist(),
            'min': values.min(axis=0).tolist(), 'max': values.max(axis=0).tolist(),
            'normalized_abs_max': np.abs(normalized).max(axis=0).tolist()}
    episodes = []
    for p in sorted((args.dataset_root / 'meta/episodes').rglob('*.parquet')):
        episodes.extend(pq.read_table(p).to_pylist())
    for ep in episodes:
        start, end = ep['dataset_from_index'], ep['dataset_to_index']
        expected_times = np.arange(end-start)/ds.meta.fps
        actual_times = np.asarray(table['timestamp'].to_pylist()[start:end])
        assert np.allclose(actual_times, expected_times, atol=2e-6, rtol=0)
        offsets = sorted(set([0, 90, 150, 210, 270, 330, 390, end-start-100, end-start-2, end-start-1]))
        for offset in offsets:
            idx = start+offset
            raw = default_collate([ds[idx]])
            assert int(raw['index'][0]) == idx
            assert int(raw['episode_index'][0]) == ep['episode_index']
            assert int(raw['frame_index'][0]) == offset
            expected_indices = np.minimum(idx + np.arange(cfg.policy.chunk_size), end-1)
            expected = torch.tensor(arrays['action'][expected_indices], dtype=torch.float32).unsqueeze(0)
            assert raw['action'].shape == expected.shape
            assert torch.equal(raw['action'], expected), f'Wrong future targets at {idx}'
            expected_pad = torch.tensor(idx + np.arange(cfg.policy.chunk_size) >= end).unsqueeze(0)
            assert torch.equal(raw['action_is_pad'], expected_pad), f'Wrong pad mask at {idx}'
            camera_stats = {}
            for key in ds.meta.camera_keys:
                assert raw[key].dtype == torch.uint8
                raw[key] = raw[key].float()/255.0  # Exact conversion in lerobot_train.py.
                camera_stats[key] = {'shape': list(raw[key].shape), 'min': float(raw[key].min()),
                                     'max': float(raw[key].max())}
            batch = pre(raw)
            assert all(torch.isfinite(batch[k]).all() for k in cfg.policy.input_features)
            reconstructed = post(batch['action']).cpu()
            assert torch.allclose(reconstructed, expected, atol=1e-4, rtol=0)
            actual_state = torch.tensor(arrays['observation.state'][idx], dtype=torch.float32)
            state_expected = (actual_state-stats['observation.state.mean'])/(stats['observation.state.std']+1e-8)
            assert torch.allclose(batch['observation.state'][0], state_expected, atol=1e-5)
            result['samples'].append({'episode': ep['episode_index'], 'frame': offset,
                'valid_targets': int((~batch['action_is_pad']).sum()),
                'target_shape': list(batch['action'].shape),
                'pan_range_deg': float(torch.max(expected[0,:,0])-torch.min(expected[0,:,0])),
                'normalized_pan_range': float(torch.max(batch['action'][0,:,0])-torch.min(batch['action'][0,:,0])),
                'normalized_state': batch['observation.state'][0].tolist(),
                'target_roundtrip_max_error': float(torch.max(torch.abs(reconstructed-expected))),
                'cameras': camera_stats})
    cfg.dataset.episodes = [0]
    single = make_dataset(cfg)
    assert len(single) == episodes[0]['length']
    assert {int(value) for value in single.hf_dataset['episode_index']} == {0}
    result['single_episode'] = {'episodes': single.episodes, 'frames': len(single)}
    result['target_alignment_passed'] = True
    result['padding_passed'] = True
    result['normalization_roundtrip_passed'] = True
    result['joint_order_passed'] = True
    result['timestamps_passed'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'}, indent=2))


if __name__ == '__main__':
    main()
