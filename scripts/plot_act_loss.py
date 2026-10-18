"""Plot exact training steps from LeLab JSONL logs, including resumed runs.

Requires matplotlib. Repeat --run LOG START_STEP to join successive runs.
Uses the exact progress counter; LeRobot's human-readable step field is rounded.
"""

import argparse
import json
import math
import re
from pathlib import Path


def read_run(path, offset):
    current = None
    points = []
    for line in Path(path).read_text().splitlines():
        message = json.loads(line)["message"]
        progress = re.search(r"Training:.*\|\s*(\d+)/(\d+)\s", message)
        if progress:
            current = int(progress.group(1)) + offset
        loss = re.search(r"\bloss:([0-9.eE+-]+)", message)
        if loss:
            if current is None:
                raise ValueError("A loss was logged without an exact progress counter.")
            value = float(loss.group(1))
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Expected finite positive loss for logarithmic plotting.")
            points.append({"step": current, "loss": value})
    return points


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", nargs=2, action="append", metavar=("LOG", "START_STEP"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    points = [p for path, offset in args.run for p in read_run(path, int(offset))]
    steps = [p["step"] for p in points]
    losses = [p["loss"] for p in points]
    # This plot's smoothing and labels assume equal, nonoverlapping 50-update bins.
    if len(points) < 20 or any(b - a != 50 for a, b in zip(steps, steps[1:])):
        raise ValueError("Expected contiguous logged averages every 50 updates.")
    smooth = [sum(losses[i-9:i+1]) / 10 if i >= 9 else float('nan') for i in range(len(losses))]
    low = min(losses)
    minima = [p for p in points if p["loss"] == low]
    last = steps[-1]
    previous = [p["loss"] for p in points if last - 2000 < p["step"] <= last - 1000]
    final = [p["loss"] for p in points if last - 1000 < p["step"] <= last]
    previous_mean, final_mean = sum(previous)/len(previous), sum(final)/len(final)
    summary = dict(points=points, minimum_logged_loss=low, minimum_steps=[p['step'] for p in minima],
                   final_logged_loss=losses[-1], final_1000_mean=final_mean,
                   preceding_1000_mean=previous_mean,
                   final_block_improvement_percent=100*(1-final_mean/previous_mean),
                   logging_interval=50, smoothing_window_updates=500)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix('.json').write_text(json.dumps(summary, indent=2) + '\n')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), layout='constrained')
    fig.suptitle('ACT wave training loss · 30-action chunks · 15,000 total updates', fontsize=16)
    for ax in axes:
        ax.plot(steps, losses, color='#9db7ce', lw=1.2, label='Logged loss (50-update average)')
        ax.plot(steps, smooth, color='#00659b', lw=2, label='Trailing 500-update mean')
        ax.grid(alpha=.2)
        ax.set_xlabel('Total training updates')
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.set_ylabel('Training loss')
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_yscale('log')
    axes[0].set_title('Full history (logarithmic loss axis)', fontsize=12, pad=12)
    axes[0].set_xlim(0, last+300)
    axes[0].axvline(2000, color='#818995', ls=':', lw=1)
    axes[0].text(2200, 12, 'Resumed from\n2,000 updates', fontsize=9, color='#57616f')
    checkpoints = [p for p in points if p['step'] in (5000, 10000, 15000)]
    for p in checkpoints:
        axes[0].scatter(p['step'], p['loss'], color='#7c3872', s=30, zorder=4)
        axes[0].annotate(f"{p['loss']:.3f}", (p['step'], p['loss']), xytext=(-7, 14),
                         textcoords='offset points', ha='right', fontsize=9, color='#7c3872')
    axes[0].legend(loc='upper right', fontsize=8, frameon=False)
    axes[1].set_title('Final 5,000 updates (linear loss axis)', fontsize=12, pad=12)
    axes[1].set_xlim(last-5000, last+100)
    zoom = [p['loss'] for p in points if p['step'] >= last-5000]
    axes[1].set_ylim(min(zoom)-.04, max(zoom)+.03)
    axes[1].scatter([p['step'] for p in minima], [low]*len(minima), color='#b43c59', s=34, zorder=4)
    axes[1].annotate(f"Lowest logged: {low:.3f}\nUpdates " + ' and '.join(f"{p['step']:,}" for p in minima),
                     (minima[0]['step'], low), xytext=(last-4400, low+.025), fontsize=10,
                     color='#8e2e47', arrowprops={'arrowstyle':'->', 'color':'#8e2e47'})
    fig.supxlabel('Training observations only · each logged point averages 50 updates · no validation loss recorded',
                  fontsize=10, color='#59616a')
    fig.savefig(args.output, dpi=160, facecolor='white')
    plt.close(fig)
    print(json.dumps({k:v for k,v in summary.items() if k != 'points'}, indent=2))
    print(args.output.resolve())


if __name__ == '__main__':
    main()
