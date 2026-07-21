"""figkit: reusable, science-free figure framework for PhyKAN.

Importing figkit first runs ``bootstrap`` so MPLCONFIGDIR is set before any
submodule imports Matplotlib. Submodules (config, layout, modload, plotting,
schematic, style) are imported explicitly by each figure's make_figure.py.

See FIGURE_SYSTEM_PLAN.md.
"""

from __future__ import annotations

from . import bootstrap  # noqa: F401  (sets MPLCONFIGDIR before Matplotlib imports)
