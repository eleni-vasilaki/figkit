"""Figure creation and grid layout with auto-height.

The panel's overall size comes from the grid, uniformly across figures. Geometry is
authored in inches (canvas width, margins, inter-panel gaps) and converted to the
Matplotlib fractions internally, so a figure declares physical intent and the height
follows from the layout unless it is explicitly fixed. See FIGURE_SYSTEM_PLAN.md.

Public API:
- ``new_figure(cfg)``                 -> a Figure sized from cfg["canvas"]/["layout"]
- ``grid(fig, layout, **overrides)``  -> a GridSpec with margins/gaps from the layout
- ``subgrid(fig, cell, rows, cols)``  -> a nested grid inside one outer-grid cell (inch gaps)
- ``place_panel_letters(fig, axes)``  -> house-style letters at each panel's top-left
- ``adjust_frame(ax, ...)``           -> reasoned post-draw frame exception
"""

from __future__ import annotations

from typing import Any, Mapping

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec, SubplotSpec

from .plotting import panel_label

MM_PER_IN = 25.4


def _geometry(canvas: Mapping[str, Any], layout: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve per-cell and canvas sizes (inches) from the canvas/layout declarations.

    Column widths and row heights follow the ``col_ratios``/``row_ratios`` knobs
    (uniform ``[1, 1, ...]`` by default). ``panel_aspect`` ties the reference (mean)
    column width to the reference row height, so auto-height still follows from width.
    """
    W = float(canvas["width_in"])
    rows, cols = int(layout["rows"]), int(layout["cols"])
    L, R = layout["margin_left_in"], layout["margin_right_in"]
    T, B = layout["margin_top_in"], layout["margin_bottom_in"]
    wsp, hsp = layout["wspace_in"], layout["hspace_in"]
    aspect = layout["panel_aspect"]
    cr = list(layout.get("col_ratios") or [1.0] * cols)
    rr = list(layout.get("row_ratios") or [1.0] * rows)

    usable_w = W - L - R - (cols - 1) * wsp
    ref_w = usable_w / cols                     # mean column width (aspect reference)
    ref_h = ref_w / aspect                      # mean row height
    col_w = [usable_w * c / sum(cr) for c in cr]

    # Row heights. Two paths:
    #  - row_heights_in given (opt-in): rows are AUTHORED in inches, the canvas height is
    #    derived to honour them exactly, and the inter-row gap is converted against the true
    #    mean row height (sum/rows). This is the correct, physical path.
    #  - otherwise (default, unchanged): rows scale from panel_aspect via ref_h, and the gap
    #    is converted against ref_h. Kept identical so existing figures do not move.
    row_heights_in = layout.get("row_heights_in")
    if row_heights_in:
        rh = [float(x) for x in row_heights_in]
        rr = rh                                          # height_ratios (proportional)
        row_h = rh                                       # actual physical row heights
        hspace_ref = sum(rh) / rows                      # matplotlib gap = hspace_frac * mean cell
        H = T + B + sum(rh) + (rows - 1) * hsp
    else:
        row_h = [ref_h * r / (sum(rr) / rows) for r in rr]
        hspace_ref = ref_h
        H = T + B + sum(row_h) + (rows - 1) * hsp if canvas["height"] == "auto" else float(canvas["height"])
    return {"W": W, "H": H, "L": L, "R": R, "T": T, "B": B,
            "rows": rows, "cols": cols, "ref_w": ref_w, "ref_h": ref_h,
            "hspace_ref": hspace_ref,
            "col_w": col_w, "row_h": row_h, "col_ratios": cr, "row_ratios": rr,
            "wsp": wsp, "hsp": hsp}


def new_figure(cfg: Mapping[str, Any]) -> Figure:
    """Create the figure at the width from cfg, with height auto-computed (or fixed).

    Reports the final physical size at build time, so the actual width and
    auto-derived height are visible.
    """
    g = _geometry(cfg["canvas"], cfg["layout"])
    fig = plt.figure(figsize=(g["W"], g["H"]))
    print(f"figure canvas: {g['W']:.3f} x {g['H']:.3f} in "
          f"({g['W'] * MM_PER_IN:.1f} x {g['H'] * MM_PER_IN:.1f} mm)")
    return fig


def grid(fig: Figure, layout: Mapping[str, Any], *, reason: str | None = None,
         **overrides: Any) -> GridSpec:
    """Build a GridSpec from a layout dict, converting inch margins/gaps to fractions.

    ``**overrides`` (e.g. ``wspace_in=0.9``) win over the layout for this figure. An
    override is a departure from the manifest's declared geometry, so it must carry a
    ``reason=`` at the call site — the same rule ``config.load`` enforces on a knob that
    departs from its default, and ``subgrid`` on a non-uniform split. A plain
    ``grid(fig, layout)`` needs no reason.
    """
    if overrides and not reason:
        knobs = ", ".join(sorted(overrides))
        raise ValueError(
            f"layout.grid: overriding {knobs} departs from the manifest layout; add "
            f"reason='...' saying why this figure needs a value its figure.toml does not "
            f"declare (or move the value into figure.toml with its _reason).")
    lay = {**layout, **overrides}
    W, H = fig.get_size_inches()
    g = _geometry({"width_in": W, "height": H}, lay)
    return fig.add_gridspec(
        g["rows"], g["cols"],
        left=g["L"] / W, right=1 - g["R"] / W,
        top=1 - g["T"] / H, bottom=g["B"] / H,
        width_ratios=g["col_ratios"], height_ratios=g["row_ratios"],
        wspace=(g["wsp"] / g["ref_w"]) if g["cols"] > 1 else 0.0,
        hspace=(g["hsp"] / g["hspace_ref"]) if g["rows"] > 1 else 0.0,
    )


def subgrid(fig: Figure, parent: SubplotSpec, rows: int, cols: int, *,
            col_ratios: "list[float] | None" = None, row_ratios: "list[float] | None" = None,
            wspace_in: float = 0.0, hspace_in: float = 0.0,
            reason: str | None = None) -> GridSpecFromSubplotSpec:
    """Split one cell of an outer grid into a nested grid, inch gaps like ``grid``.

    ``parent`` is a cell (or cell range) of an outer grid, e.g. ``outer[0]`` or
    ``outer[1:]``. Gaps are given in inches and converted to fractions using the parent
    cell's own physical size, so a nested grid reads the same as the top-level ``grid``.

    A nested grid is a layout exception (FIGURE_SYSTEM_PLAN.md, "How Exceptions Work"):
    a NON-UNIFORM split (unequal ``col_ratios``/``row_ratios``) must carry a ``reason=``
    at the call site; a plain uniform split does not.
    """
    cr = [float(x) for x in (col_ratios or [1.0] * cols)]
    rr = [float(x) for x in (row_ratios or [1.0] * rows)]
    if (cr != [1.0] * cols or rr != [1.0] * rows) and not reason:
        raise ValueError(
            "layout.subgrid: a non-uniform nested split needs reason='...' saying why "
            "(e.g. the robot raster is narrower than the learning diagram).")
    W, H = fig.get_size_inches()
    box = parent.get_position(fig)
    cell_w, cell_h = box.width * W, box.height * H         # parent cell size, inches
    mean_w = (cell_w - (cols - 1) * wspace_in) / cols      # mean sub-axis width (gap ref)
    mean_h = (cell_h - (rows - 1) * hspace_in) / rows
    return parent.subgridspec(
        rows, cols,
        width_ratios=cr, height_ratios=rr,
        wspace=(wspace_in / mean_w) if cols > 1 else 0.0,
        hspace=(hspace_in / mean_h) if rows > 1 else 0.0,
    )


def cell_size_in(cfg: Mapping[str, Any], row: int = 0, col: int = 0) -> "tuple[float, float]":
    """Physical size (inches) of grid cell (row, col) — a schematic panel's design size.

    Defaults to the top-left cell. A schematic's standalone preview renders at this
    size so it matches the panel placed in the figure (see figkit.schematic.preview).
    """
    g = _geometry(cfg["canvas"], cfg["layout"])
    return (g["col_w"][col], g["row_h"][row])


def place_panel_letters(fig: Figure, axes: Mapping[str, Axes], *,
                        dx_in: float = 0.15, dy_in: float = 0.07,
                        shifts: "Mapping[str, tuple[float, float]] | None" = None,
                        reason: str | None = None, **overrides: Any) -> None:
    """Draw a panel letter at each panel's grid-cell top-left, inset by fixed physical amounts.

    The anchor is the axes' **grid cell** (``get_position(original=True)``), NOT its drawn
    box. This matters for aspect-locked schematic panels: matplotlib shrinks such an axes
    inside its cell to preserve the aspect ratio and (by default) centres it, so two
    schematics of different aspect in the same band would otherwise put their letters at
    different heights. Anchoring to the cell keeps every letter aligned regardless of each
    panel's aspect or art anchor. A frame moved with ``adjust_frame`` updates
    the original position too, so the letter still follows a deliberately relocated frame —
    place letters AFTER any such adjustment. Physical insets keep letters at the same
    apparent position and size in every figure.

    A single letter can be nudged from that auto-aligned position with
    ``shifts={"a": (dx_in, dy_in)}`` (inches; + = right / up). This is an opt-in *local*
    adjustment for the rare case where one letter collides with a tall title or busy panel;
    every un-shifted letter stays auto-aligned, so the default never drifts. A non-empty
    ``shifts`` breaks the house alignment for those letters, so it must carry a ``reason=``
    at the call site, like every other exception in this module.
    """
    if shifts and not reason:
        raise ValueError(
            f"layout.place_panel_letters: shifting letter(s) {sorted(shifts)} breaks the "
            f"house alignment; add reason='...' saying why (e.g. panel c's letter collides "
            f"with a tall title).")
    W, H = fig.get_size_inches()
    fig.canvas.draw()
    shifts = shifts or {}
    for label, ax in axes.items():
        p = ax.get_position(original=True)
        sx, sy = shifts.get(label, (0.0, 0.0))
        panel_label(fig, label, p.x0 - dx_in / W + sx / W, p.y1 + dy_in / H + sy / H, **overrides)


def adjust_frame(
    ax: Axes,
    *,
    dx_in: float = 0.0,
    dy_in: float = 0.0,
    dwidth_in: float = 0.0,
    dheight_in: float = 0.0,
    reason: str,
) -> None:
    """Move or resize a panel's alignment frame after drawing.

    This is the rare frame-level exception, used when the panel itself needs a
    redistributed layout slot, as in the robotics top row. Panel letters should be
    placed *after* all frame adjustments, so they attach to the final frame.

    For ordinary schematic tuning, prefer ``schematic.place_framed_image`` so only
    the art moves and the frame/letters remain aligned.
    """
    if not reason:
        raise ValueError("layout.adjust_frame needs reason='...' for the frame exception")
    fig = ax.figure
    W, H = fig.get_size_inches()
    p = ax.get_position()
    ax.set_position(
        (
            p.x0 + dx_in / W,
            p.y0 + dy_in / H,
            p.width + dwidth_in / W,
            p.height + dheight_in / H,
        ),
        which="both",
    )


