#!/usr/bin/env python3
"""Template extractor: reduce the raw bundle to this figure's committed tables.

Copy this folder to start a new figure; replace the body below.

The reproducibility step. Raw per-(N, run) bundles live in the repo-root ``raw_data/``
folder (kept local / gitignored), so a fresh clone cannot see them. This script reads
that bundle ONCE and writes the individual observations the figure needs as small,
human-readable TSV tables into this figure's own committed ``extracted_data/`` folder.

``make_figure.py`` then reads only those tables and derives every summary (mean, band)
from them, so the figure regenerates from committed data alone.

Follows specs/scientific_coding_principles.md:
  6  save the per-run observations, not summaries — the band is derived from the table.
  7  numeric tables as TSV, not a binary or config format.
  12 quantities derivable from a declared value (a parameter count from N) are computed
     in make_figure.py, not copied into the table here.

Re-run whenever the source bundle changes; commit the resulting TSV files.
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

from figkit import config  # noqa: E402

SOURCE = _REPO_ROOT / "raw_data" / "<bundle>"
OUT_DIR = FIGURE_DIR / "extracted_data"

CONFIG = config.load(FIGURE_DIR)

# Per-(N, run) filename pattern, as a full-match regex with named groups n and run.
# SERIES = r"Trial Lengths, N=(?P<n>\d+), Run=(?P<run>\d+)\.npy"


# ── TSV writer (full float precision so plotted values round-trip exactly) ────
def _cell(v):
    return repr(v) if isinstance(v, float) else str(v)


def write_tsv(name, comment, columns, rows):
    lines = [f"# {comment}", "\t".join(columns)]
    lines += ["\t".join(_cell(v) for v in row) for row in rows]
    path = OUT_DIR / name
    path.write_text("\n".join(lines) + "\n")
    print(f"  {name}: {len(rows)} rows")
    return path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing {OUT_DIR}")

    # One table per data-driven panel; one row per individual observation. Select
    # run files with config.resolve_runs(folder, regex, CONFIG["panel_b"]["phykan"]),
    # then reduce each run to its observation. The first line of every table is a
    # `#` comment saying what a row is and how make_figure reduces it.
    raise NotImplementedError("Template: copy this folder and write the extraction.")

    # Persist what was selected beside the tables, so a fresh clone sees any
    # under-selection warning without access to raw_data/.
    config.write_extraction_log(OUT_DIR)


if __name__ == "__main__":
    main()
