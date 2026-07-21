#!/usr/bin/env python3
"""Template figure build entry point. Copy this folder to start a new figure.

Scaffold only. The real build code is added per figure; see
specs/CODE_SPECIFICATION.md and examples/minimal_figure/.

This file is a PURE PLOTTER. It reads the committed extracted_data/*.tsv tables and
derives every summary (mean, band) from them. It must not train, simulate, roll out,
or run inference, and it never reads raw_data/. Reducing the raw bundle to those
tables is extract_data.py's job; recovering an input the experiment never saved is
generate_missing_data.py's.

Where code goes (keep this figure a pure plotter where possible):
- model / simulation code used by >1 benchmark -> src/shared/
- model / simulation code for this benchmark only -> src/<benchmark>/
- task-specific model/env classes for this figure -> this figure's own folder
- code exclusively for data processing (e.g. example selection) -> this figure folder
When a script unpickles a model whose pickled module name differs from the file name,
load it via importlib and register it in sys.modules under that name, and guard
spec_from_file_location against None (see the ported figures).
"""

# ---- PhyKAN no-install import header. Keep before figkit imports. ----
import sys
from pathlib import Path

FIGURE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = FIGURE_DIR.parents[1]
if not ((_REPO_ROOT / "figkit").is_dir() and (_REPO_ROOT / "figures").is_dir()):
    raise RuntimeError(f"Could not find PhyKAN repository root from {__file__}")
sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------------------------------------------------

from figkit import config, layout, plotting, style  # noqa: E402, F401


def main() -> None:
    """Build the figure. Filled in per figure during migration."""
    raise NotImplementedError("Template: copy this folder and write the build.")


if __name__ == "__main__":
    main()
