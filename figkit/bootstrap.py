"""Central startup: set MPLCONFIGDIR before Matplotlib is imported anywhere.

Imported first by ``figkit/__init__.py`` so a repo-local Matplotlib config
directory is in place before any submodule imports Matplotlib. Keeping the config
dir inside the repo makes builds reproducible and avoids touching the user's home
Matplotlib cache. See FIGURE_SYSTEM_PLAN.md.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MPLCONFIG_DIR = REPO_ROOT / ".mplconfig"


def init() -> None:
    """Point Matplotlib at the repo-local config dir and the Agg backend, unless set."""
    MPLCONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))
    # Headless Agg backend: the build scripts only save files, and the interactive
    # macOS backend snaps the canvas to whole screen pixels on the first draw
    # (8.2 in became 8.1889 in), so the saved size would depend on the machine.
    # Agg renders at exactly the requested size everywhere. setdefault, so the
    # environment can still override (caught by the tests/demo_figure geometry check).
    os.environ.setdefault("MPLBACKEND", "Agg")


init()
