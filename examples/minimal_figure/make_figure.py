#!/usr/bin/env python3
"""The smallest complete figkit figure: one panel, one table, a mean +- std band.

This is the starting point to copy. It shows the whole shape of a figure in one
screenful — manifest, committed table, derived statistics, exact-size save — with
nothing else in the way. Run it:

    conda run -n myml python examples/minimal_figure/make_figure.py

Then read tests/demo_figure/README.md for everything this leaves out (subgrids,
schematics, colorbars, run selection over per-run files, geometry assertions).

The three rules it demonstrates, which every real figure follows:
  1. Geometry is declared in figure.toml, not in this file. The canvas width comes
     from the house width and the height is derived from the layout.
  2. The committed table holds one row per OBSERVATION. The mean and the band are
     derived here, at plot time, so the reduction is visible in the plotting code.
  3. The figure saves at its exact declared size — never bbox_inches="tight",
     which would silently change the width the manuscript was designed around.
"""

from __future__ import annotations

# ---- PhyKAN no-install import header. Keep before figkit imports. ----
import sys
from pathlib import Path

FIGURE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = FIGURE_DIR.parents[1]
if not ((_REPO_ROOT / "figkit").is_dir() and (_REPO_ROOT / "figures").is_dir()):
    raise RuntimeError(f"Could not find PhyKAN repository root from {__file__}")
sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------

from figkit import config, layout, plotting, style  # noqa: E402

TABLE = FIGURE_DIR / "extracted_data" / "measurements.tsv"
OUT = FIGURE_DIR / "outputs" / "minimal_figure.png"

CONFIG = config.load(FIGURE_DIR)          # validated dict; refuses a bad manifest
style.apply_matplotlib_style()            # house typography, colours, rcParams


def read_observations(path):
    """{x: [per-run y]} from a TSV whose first line is a `#` provenance comment."""
    rows = {}
    lines = [ln for ln in path.read_text().splitlines() if not ln.startswith("#")]
    header = lines[0].split("\t")
    for line in lines[1:]:
        record = dict(zip(header, line.split("\t")))
        rows.setdefault(float(record["x"]), []).append(float(record["y"]))
    return rows


def draw_panel(ax):
    """Mean +- std over runs, derived from the individual observations."""
    observations = read_observations(TABLE)
    x = sorted(observations)
    bands = [plotting.mean_band(observations[k]) for k in x]
    plotting.draw_band(ax, x, [c for c, _, _ in bands], [lo for _, lo, _ in bands],
                       [hi for _, _, hi in bands],
                       color=style.COLORS["primary"], label="Example series")
    plotting.style_log_axes(ax, xlabel="Trainable parameters", ylabel="Score")
    ax.legend(**style.LEGEND)

    # Runs per point, so an uneven series is visible at build time rather than
    # hidden inside a band. Nothing is declared here, so every point reads "auto".
    config.report_runs({"example": {int(k): len(observations[k]) for k in x}})


def main():
    fig = layout.new_figure(CONFIG)               # width + auto-derived height
    grid = layout.grid(fig, CONFIG["layout"])     # margins/gaps in inches
    ax = fig.add_subplot(grid[0, 0])

    draw_panel(ax)
    layout.place_panel_letters(fig, {"a": ax})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor="white")           # exact declared size, no "tight"
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
