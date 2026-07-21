"""Schematic panel support: framed art placement and standalone panel previews.

``preview`` renders ONE panel on its own — its real grid cell drawn as a box at the
real figure size, the art inside, the panel letter at its true position, and a little
space around — so a schematic can be sized and placed against its real boundary without
building the whole figure. Cell size, box and letter come from the figure's own layout,
so they match the assembled figure. See FIGURE_SYSTEM_PLAN.md, "Schematic Panels".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, PathPatch, Rectangle
from matplotlib.path import Path as MplPath

from . import layout
from .plotting import panel_label
from .style import COLORS, SCHEMATIC, SCHEMATIC_STYLE, apply_matplotlib_style


def place_framed_image(
    ax: Axes,
    img,
    *,
    scale: float = 1.0,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    anchor: str = "N",
    clip: bool = False,
    reason: str | None = None,
) -> None:
    """Place schematic/image art relative to its aligned panel frame.

    The axes is the *frame*: panel letters and row/column alignment attach to it.
    The image is the *art*: it may be scaled and shifted relative to that frame for
    visual balance. This is the normal way to make a schematic read larger or sit
    better without moving the panel letter or perturbing neighbouring panels.

    The shared knob logic for schematic art:
      scale     size multiplier — 1.0 fills the cell, 1.3 = 30% bigger. Scaling is
                about the image centre, so changing scale never moves the image.
      x_offset  horizontal shift in cell-width fractions (+ = right).
      y_offset  vertical shift in cell-height fractions (+ = up).
      clip      False lets enlarged art extend beyond the frame; the frame itself
                remains aligned. True clips the art inside the frame.

    ``anchor`` top-aligns the art in its cell by default so it lines up with a
    neighbouring data panel. To make the whole PANEL bigger, use the grid ratios
    (figkit.layout / figure.toml), not this scale — this composes art within the cell.

    Any non-default art transform should carry ``reason=``. That keeps the visual
    adjustment explicit while preserving the reusable frame/art distinction.
    """
    if (scale != 1.0 or x_offset != 0.0 or y_offset != 0.0 or clip) and not reason:
        raise ValueError(
            "schematic.place_framed_image: non-default art placement needs "
            "reason='...' so the visual adjustment is documented"
        )
    h, w = img.shape[:2]
    ar = w / h
    ax.set_xlim(0, ar)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.set_anchor(anchor)
    ax.set_axis_off()
    cx = ar / 2 + x_offset * ar
    cy = 0.5 + y_offset
    iw, ih = ar * scale, scale
    ax.imshow(img, extent=(cx - iw / 2, cx + iw / 2, cy - ih / 2, cy + ih / 2),
              aspect="auto", zorder=1, clip_on=clip)


def place_image(ax: Axes, img, *, scale: float = 1.0, x_offset: float = 0.0,
                y_offset: float = 0.0, anchor: str = "N") -> None:
    """Backward-compatible wrapper for simple framed image placement.

    New figure code should prefer :func:`place_framed_image`, which exposes the
    frame/art rule and requires a reason for non-default placement.
    """
    place_framed_image(
        ax,
        img,
        scale=scale,
        x_offset=x_offset,
        y_offset=y_offset,
        anchor=anchor,
        clip=False,
        reason="legacy place_image wrapper",
    )


def preview(cfg: Mapping[str, Any], draw_fn: Callable[[Axes], None], out_path: Path, *,
            letter: "str | None" = None, row: int = 0, col: int = 0,
            pad_in: float = 0.5, apply_style: bool = True) -> Path:
    """Preview one panel on its own, in its REAL cell.

    Draws the panel's true grid cell — outlined as a box, at its real figure size — with
    ``draw_fn``'s art inside and the panel ``letter`` at its real top-left position, plus
    ``pad_in`` inches of space all round so slight overflow is visible. Cell size, box and
    letter come from the figure's own layout (``cfg``), so they match the assembled
    figure; only the neighbouring panels' data is absent (build the whole figure for that).
    """
    if apply_style:
        apply_matplotlib_style()
    cell_w, cell_h = layout.cell_size_in(cfg, row, col)
    fig_w, fig_h = cell_w + 2 * pad_in, cell_h + 2 * pad_in
    rect = (pad_in / fig_w, pad_in / fig_h, cell_w / fig_w, cell_h / fig_h)
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes(rect)
    draw_fn(ax)
    fig.add_artist(Rectangle(rect[:2], rect[2], rect[3], transform=fig.transFigure,
                             fill=False, edgecolor="0.55", linewidth=1.0, zorder=5))
    if letter is not None:
        panel_label(fig, letter, rect[0] - 0.15 / fig_w, rect[1] + rect[3] + 0.07 / fig_h)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor="white")
    plt.close(fig)
    return out_path


# ── shared schematic DRAWING primitives (ported from v1 common/schematic.py) ──
# House style is figure_robotics (panel b); all constants live in figkit.style
# (COLORS, SCHEMATIC, SCHEMATIC_STYLE). These primitives only draw — each figure
# composes its own diagram from them. curve_in / open_axes_miniplot exist for
# figures that plot curves inside schematic boxes (filter_kan); robotics has none.
INK = SCHEMATIC["ink"]          # outlines, text and arrows
ORANGE = SCHEMATIC["active"]    # active / signal / edge-response accent
GREY = SCHEMATIC["passive"]     # passive / input-side nodes
TEAL = COLORS["primary"]         # network / architecture nodes
WHITE = SCHEMATIC["fill"]       # box / node fill
MUTED = "#7A828C"               # de-emphasised axis labels

S = SCHEMATIC_STYLE             # line weights / glyph sizes (single source of truth)


def text(ax: Axes, x, y, s, size, *, weight="normal", color=INK, ha="center", va="center", rot=0):
    ax.text(x, y, s, ha=ha, va=va, fontsize=size, fontweight=weight, color=color,
            rotation=rot, linespacing=S["line_spacing"], zorder=6)


def arrow(ax: Axes, x0, x1, y, *, color=ORANGE):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>", mutation_scale=9,
                                 lw=S["arrow_lw"], color=color, shrinkA=0, shrinkB=0, zorder=4))


def node_circle(ax: Axes, cx, cy, r, *, color=WHITE, lw=None):
    ax.add_patch(Circle((cx, cy), r, lw=S["node_lw"] if lw is None else lw,
                        edgecolor=INK, facecolor=color, zorder=2))


def box(ax: Axes, x, y, w, h, *, dashed=False, fill=WHITE, lw=None):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={S['box_rounding']}",
        linewidth=(S["dash_lw"] if dashed else (S["box_lw"] if lw is None else lw)),
        edgecolor=INK, facecolor="none" if dashed else fill,
        linestyle=(0, (4, 3)) if dashed else "solid", joinstyle="round", zorder=1))


def bezier(ax: Axes, p0, p1, p2, p3, *, color=INK, lw=None, alpha=1.0, dashed=False, zorder=2):
    path = MplPath([p0, p1, p2, p3], [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4])
    ax.add_patch(PathPatch(path, facecolor="none", edgecolor=color, lw=lw or S["axis_lw"],
                           alpha=alpha, linestyle=(0, (2.5, 2)) if dashed else "solid", zorder=zorder))


def connect(ax: Axes, x0, y0, x1, y1, *, color=INK, lw=None, alpha=1.0, dashed=False, bow=0.5, zorder=2):
    """Smooth bezier link with horizontal tangents at both ends (box connectors)."""
    dx = (x1 - x0) * bow
    bezier(ax, (x0, y0), (x0 + dx, y0), (x1 - dx, y1), (x1, y1),
           color=color, lw=lw, alpha=alpha, dashed=dashed, zorder=zorder)


def draw_network(ax: Axes, xs, ys_per_layer, r, *, node_color=TEAL, edge_color=INK,
                 bend=None, inset=None, node_lw=None, edge_lw=None, edge_alpha=0.80):
    """The robotics fully-connected node-layer glyph (the shared NN look).

    Vertical-bend cubic-bezier edges between every node of adjacent columns, plus
    filled circular nodes — robotics' ``draw_neural_network`` scheme generalised to
    arbitrary columns. ``xs`` = per-column x; ``ys_per_layer`` = per-column node ys;
    ``r`` = node radius; ``node_color`` one colour or one per column. ``bend``/``inset``
    default to robotics' per-radius ratios so the curve matches at any scale.
    """
    bend = (S["node_curve_bend"] / 0.105) * r if bend is None else bend
    inset = S["node_edge_inset"] * r if inset is None else inset
    elw = S["network_lw"] if edge_lw is None else edge_lw
    nlw = S["node_lw"] if node_lw is None else node_lw
    for a in range(len(xs) - 1):
        xa, xb = xs[a] + inset, xs[a + 1] - inset
        gap = xb - xa
        for yl in ys_per_layer[a]:
            for yr in ys_per_layer[a + 1]:
                tb = bend if yr >= yl else -bend
                bezier(ax, (xa, yl), (xa + gap * 0.42, yl + tb),
                       (xa + gap * 0.58, yr - tb), (xb, yr),
                       color=edge_color, lw=elw, alpha=edge_alpha)
    colors = node_color if isinstance(node_color, (list, tuple)) else [node_color] * len(xs)
    for x, ys, col in zip(xs, ys_per_layer, colors):
        for y in ys:
            ax.add_patch(Circle((x, y), r, facecolor=col, edgecolor=INK, lw=nlw, zorder=5))


def curve_in(ax: Axes, x, y, w, h, xs, ys, *, logx=True, symmetric=False, lw=None, pad_x=0.08, pad_y=0.12):
    """A curve fitted inside a box (edge-response plots)."""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    xb = np.log10(xs) if logx else xs
    xn = (xb - xb.min()) / (np.ptp(xb) or 1.0)
    if symmetric:
        a = max(abs(ys.min()), abs(ys.max())) or 1.0
        yn = 0.5 + 0.45 * ys / a
    else:
        yn = (ys - ys.min()) / (np.ptp(ys) or 1.0)
    px = x + (pad_x + (1 - 2 * pad_x) * xn) * w
    py = y + (pad_y + (1 - 2 * pad_y) * yn) * h
    ax.plot(px, py, color=ORANGE, lw=lw or S["curve_lw"], solid_capstyle="round",
            solid_joinstyle="round", zorder=4)


def open_axes_miniplot(ax: Axes, x, y, w, h, xs, ys, *, title=None, xlabel="frequency",
                       ylabel="amplitude", logx=True):
    """A tiny labelled axes inset (L-shaped axes + a curve fitted inside)."""
    ax.add_line(Line2D([x, x], [y, y + h], color=INK, lw=S["axis_lw"], zorder=3))
    ax.add_line(Line2D([x, x + w], [y, y], color=INK, lw=S["axis_lw"], zorder=3))
    curve_in(ax, x, y, w, h, xs, ys, logx=logx)
    if title:
        text(ax, x + w / 2, y + h + 0.17, title, S["box_title_size"], weight="semibold")
    if xlabel:
        text(ax, x + w / 2, y - 0.17, xlabel, S["axis_label_size"], color=MUTED)
    if ylabel:
        text(ax, x - 0.14, y + h / 2, ylabel, S["axis_label_size"], color=MUTED, rot=90)
