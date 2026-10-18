"""Plot recorded targets and offline ACT action chunks (requires matplotlib).

By default plots shoulder pan at four observation times. --joint all creates one
four-panel plot per joint plus a six-joint overview at --overview-seconds.
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comparison', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True,
                        help='Image path; with --joint all, suffix each output with its joint name')
    parser.add_argument('--episode', type=int, default=0)
    parser.add_argument('--labels', nargs='+', help='One display label per checkpoint, in input order')
    parser.add_argument('--joint', default='shoulder_pan.pos',
                        help='Action column name (e.g. elbow_flex.pos), or all')
    parser.add_argument('--overview-seconds', type=float, default=7)
    args = parser.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.ticker import MaxNLocator

    report = json.loads(args.comparison.read_text())
    checkpoints = report['checkpoints']
    names = report['joint_names']
    units = report.get('joint_units', ['0–100 units' if n == 'gripper.pos' else 'degrees' for n in names])
    fps = report.get('fps', 30)
    labels = args.labels or [
        (f"Chunk {c['chunk_size']} · " if 'chunk_size' in c else '') + f"{c['step']:,} updates"
        for c in checkpoints
    ]
    if len(labels) != len(checkpoints):
        parser.error('Provide exactly one label per checkpoint.')
    if args.joint != 'all' and args.joint not in names:
        parser.error(f'Unknown joint. Choose one of {names}, or all.')
    colors = ['#8b8f97', '#d17b00', '#086fac', '#a23b72']

    def title(name):
        return name.removesuffix('.pos').replace('_', ' ').capitalize()

    def draw(ax, joint, sec):
        col = names.index(joint)
        reference = None
        for j, (entry, label) in enumerate(zip(checkpoints, labels, strict=True)):
            sample = next((s for s in entry['samples']
                           if s['episode'] == args.episode and np.isclose(s['seconds'], sec)), None)
            if sample is None:
                raise ValueError(f'No observation for episode {args.episode} at {sec}s.')
            if 'joint_targets' in sample:
                target = np.asarray(sample['joint_targets'])[:, col]
                prediction = np.asarray(sample['joint_predictions'])[:, col]
            elif joint == 'shoulder_pan.pos':
                target = np.asarray(sample['pan_target'])
                prediction = np.asarray(sample['pan_prediction'])
            else:
                raise ValueError('Re-run check_act_wave.py to export all joint trajectories.')
            if target.shape != prediction.shape or not np.isfinite([target, prediction]).all():
                raise ValueError('Invalid prediction/target arrays.')
            if reference is None:
                reference = target
                ax.plot(np.arange(len(target)) / fps, target, color='#202830', lw=2,
                        label='Demonstration')
            elif reference.shape != target.shape or not np.allclose(reference, target):
                raise ValueError('Checkpoint comparisons use different targets.')
            ax.plot(np.arange(len(prediction)) / fps, prediction,
                    color=colors[j % len(colors)], lw=1.7, label=label)
        ax.set_xlabel('Future time in predicted chunk (s)')
        ax.set_ylabel(f'{title(joint)} ({units[col]})')
        ax.grid(alpha=.2)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        ax.ticklabel_format(axis='y', style='plain', useOffset=False)
        # Avoid making tiny changes in nearly stationary joints look like a wave.
        low, high = ax.get_ylim()
        if high - low < 1:
            center = (low + high) / 2
            ax.set_ylim(center - .5, center + .5)

    def save(fig, axes, heading, path):
        fig.suptitle(heading, fontsize=15, y=.995)
        fig.legend(*axes.flat[0].get_legend_handles_labels(), loc='upper center',
                   bbox_to_anchor=(.5,.955), ncols=2, frameon=False)
        fig.tight_layout(rect=(0, .025, 1, .865))
        footer = 'Recorded training observations · offline prediction, no arm motion'
        if report.get('horizon_frames'):
            footer += f" · first {report['horizon_frames']} targets compared"
        fig.text(.5, .012, footer,
                 ha='center', fontsize=9, color='#50565e')
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, facecolor='white')
        plt.close(fig)
        print(path.resolve())

    for joint in names if args.joint == 'all' else [args.joint]:
        fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), sharey=True)
        for ax, sec in zip(axes.flat, (5, 7, 9, 11), strict=True):
            draw(ax, joint, sec)
            ax.set_title(f'Observation at {sec} seconds')
        path = args.output
        if args.joint == 'all':
            path = path.with_name(f'{path.stem}-{joint.removesuffix(".pos")}{path.suffix}')
        save(fig, axes, f'{title(joint)}: recorded targets and ACT predictions', path)

    if args.joint == 'all':
        fig, axes = plt.subplots((len(names) + 1) // 2, 2, figsize=(11, 10))
        for ax, joint in zip(axes.flat, names):
            draw(ax, joint, args.overview_seconds)
            ax.set_title(title(joint))
        for ax in list(axes.flat)[len(names):]:
            ax.set_visible(False)
        save(fig, axes, f'All joints · observation at {args.overview_seconds:g}s · episode {args.episode}',
             args.output.with_name(f'{args.output.stem}-all-joints{args.output.suffix}'))


if __name__ == '__main__':
    main()
