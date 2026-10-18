"""Copy one episode with stable vector statistics for an offline ACT fit test."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--source-repo-id', required=True)
    parser.add_argument('--episode', type=int, default=0)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--output-repo-id', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()

    import av
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.datasets.dataset_tools import delete_episodes

    source = args.source_root.resolve()
    output = args.output_root.resolve()
    if output.exists() or output == source or source in output.parents:
        raise ValueError('Output must be a new dataset directory outside the source dataset.')
    def manifest(root):
        result = {}
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix in ('.parquet', '.json', '.mp4'):
                with path.open('rb') as handle:
                    result[str(path.relative_to(root))] = hashlib.file_digest(handle, 'sha256').hexdigest()
        return result
    source_hashes = manifest(source)
    ds = LeRobotDataset(args.source_repo_id, root=source, video_backend='pyav')
    if args.episode not in range(ds.num_episodes):
        raise ValueError('Episode is outside the source dataset.')
    # Upstream copy/filter tool creates a new dataset; source files are not edited.
    delete_episodes(ds, [e for e in range(ds.num_episodes) if e != args.episode],
                    output_dir=output, repo_id=args.output_repo_id)
    table = pq.read_table(sorted((output/'data').rglob('*.parquet'))).sort_by([('index','ascending')])
    source_table = pq.read_table(sorted((source/'data').rglob('*.parquet')))
    original = source_table.filter(pc.equal(source_table['episode_index'], args.episode))
    stats_path = output/'meta/stats.json'
    stats = json.loads(stats_path.read_text())
    changes = {}
    for key in ('observation.state', 'action'):
        values = np.asarray(table[key].to_pylist(), dtype=np.float64)
        assert np.array_equal(values, np.asarray(original[key].to_pylist(), dtype=np.float64))
        assert np.isfinite(values).all()
        mean, std = values.mean(axis=0), values.std(axis=0)
        constant = values.min(axis=0) == values.max(axis=0)
        # Unit scale is deliberate for exactly constant channels. This maps the
        # recorded value to zero without amplifying numerical/encoder noise.
        std[constant] = 1.0
        changes[key] = {'old_mean': stats[key]['mean'], 'old_std': stats[key]['std'],
                        'new_mean': mean.tolist(), 'new_std': std.tolist(),
                        'constant_channels': np.flatnonzero(constant).tolist()}
        stats[key]['mean'], stats[key]['std'] = mean.tolist(), std.tolist()
    stats_path.write_text(json.dumps(stats, indent=2)+'\n')
    for path in (output/'meta/episodes').rglob('*.parquet'):
        old = pq.read_table(path)
        rows = old.to_pylist()
        assert len(rows) == 1
        for key, change in changes.items():
            for stat in ('mean', 'std'):
                rows[0][f'stats/{key}/{stat}'] = change['new_'+stat]
        pq.write_table(pa.Table.from_pylist(rows, schema=old.schema), path)
    video_counts = {}
    for path in sorted((output/'videos').rglob('*.mp4')):
        with av.open(str(path)) as container:
            frames = sum(1 for _ in container.decode(video=0))
        assert frames == len(table)
        video_counts[str(path.relative_to(output))] = frames
    assert manifest(source) == source_hashes, 'Source dataset changed during extraction.'
    report = {'source_repo_id': args.source_repo_id, 'source_episode': args.episode,
              'output_repo_id': args.output_repo_id, 'frames': len(table),
              'source_unchanged': True, 'vector_rows_equal_source': True,
              'video_frames': video_counts, 'statistics_changes': changes,
              'source_sha256': source_hashes, 'output_sha256': manifest(output)}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not k.endswith('sha256')}, indent=2))


if __name__ == '__main__':
    main()
