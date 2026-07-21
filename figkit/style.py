"""Shared visual style for PhyKAN manuscript figures.

Ported verbatim from the v1 figure factory's common/style.py: colours, the shared
canvas width, panel-letter and legend styling, and the Nature-style Matplotlib
defaults. This is the single source of truth for figure typography and palette.
"""

from __future__ import annotations

import matplotlib as mpl


# Nature-style palette, role-named (science-free): muted tones chosen per the
# Nature-family figure principles (colour used semantically; few, strong colours).
# Keys say what each colour IS FOR, not which project series happens to use it;
# figures bind roles to their own series at the call site
# (e.g. TEAL = COLORS["primary"]  # PhyKAN). Hex values unchanged from v1.
COLORS = {
    "primary": "#007A7A",     # teal — the featured method/series (PhyKAN here)
    "accent": "#D95F45",      # warm orange — experimental/highlight series
    "accent2": "#A36F18",     # ochre — reserve second accent (currently unused)
    "baseline": "#30343B",    # dark slate — comparison/baseline series (MLP here)
    "axis": "#20242A",
    "grid": "#D8DEE6",
    "panel_label": "#111111",
    "paper": "#F3EFE8",   # light warm neutral; midpoint of the diverging heatmap colormap
}

# Palette for hand-drawn schematic panels (e.g. the panel B pipeline diagram).
# Kept separate from COLORS because schematic node/outline semantics do not map
# onto the data-series palette, but defined here so all colour lives in one place.
SCHEMATIC = {
    "active": "#D95F45",   # active / output-side nodes
    "passive": "#C9C9C9",  # passive / input-side nodes
    "ink": "#050A12",      # outlines, text and arrows
    "fill": "#FFFFFF",     # box fill
}

# Line weights and glyph sizes for hand-drawn schematic panels. THE BASELINE IS
# figure_robotics (panel b): these values are taken from its STYLE so the whole
# figure set reads in robotics' house style. Single source of truth shared by
# figkit/schematic.py and every figure's schematic panels. Point-based, tuned for
# the panels' final size in the grid; a panel may pass a per-call override.
SCHEMATIC_STYLE = {
    # --- from robotics panel_b STYLE (the baseline) ---
    "title_size": 9.5,        # row / block headings
    "box_text_size": 7.0,     # text inside a box
    "legend_text_size": 7.0,
    "box_lw": 0.9,            # robotics box_linewidth
    "arrow_lw": 0.9,         # robotics arrow_linewidth
    "dash_lw": 0.8,          # robotics dash_linewidth
    "network_lw": 0.3,       # robotics network_linewidth (the dense net edges)
    "node_lw": 0.5,          # robotics node_linewidth
    "box_rounding": 0.11,    # robotics box_rounding
    "line_spacing": 1.05,    # robotics line_spacing
    "node_curve_bend": 0.16, # robotics node_curve_bend (per node_radius 0.105)
    "node_edge_inset": 0.90, # robotics node_edge_inset (fraction of node radius)
    # --- extra keys only the figures that draw curves/mini-plots need (filter_kan);
    #     robotics has no equivalent, so these don't change the baseline ---
    "sublabel_size": 8.0,    # filter_kan sub-labels
    "box_title_size": 7.5,   # filter_kan mini-plot titles
    "axis_label_size": 6.0,  # filter_kan mini-plot axis labels
    "axis_lw": 0.7,          # filter_kan box connectors / mini-plot axes
    "curve_lw": 1.1,         # filter_kan edge-response curves
}

# Shared canvas WIDTH for every figure. All figures are placed in the manuscript at one
# common \includegraphics width, so they must be authored at one common width too — then
# the central point sizes (title/label/tick/panel letter) render at the SAME apparent size
# in every figure. Only each figure's HEIGHT varies (per its layout); the width is always
# this constant. Do NOT hardcode a width in a figure and do NOT save with
# bbox_inches="tight" (tight derives the size from content, breaking the shared width).
FIGURE_WIDTH = 8.2

PANEL_LABEL = {
    "fontsize": 17,
    "fontweight": "bold",
    "ha": "left",
    # va="bottom" is the shared default: the letter sits ABOVE its anchor y, clear of the
    # panel's title and top tick number. Draw labels with plotting.panel_label, which
    # applies this style. A figure whose layout needs the letter to hang from the top passes
    # va="top" as an override and marks why (currently robotics and filter_kan).
    "va": "bottom",
    "color": COLORS["panel_label"],
}

LEGEND = {
    "loc": "upper right",
    "frameon": False,
    "handlelength": 1.8,
    "borderaxespad": 0.2,
    "labelspacing": 0.34,
}


def apply_matplotlib_style() -> None:
    """Apply the shared Nature-style Matplotlib defaults."""
    mpl.rcParams.update(
        {
            # Nature names Helvetica/Arial for figure text; Arial is used when
            # present and falls back to bundled DejaVu Sans for reproducibility.
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 9,
            "axes.linewidth": 0.7,
            "axes.edgecolor": COLORS["axis"],
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "xtick.major.size": 3,
            "ytick.major.size": 3,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "legend.fontsize": 7.2,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 450,
        }
    )
