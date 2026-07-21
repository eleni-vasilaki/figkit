"""Shared plot helpers reused by more than one figure.

Ported from the v1 figure factory's common/plotting.py, defined once so every
figure draws bands, styles log axes, aggregates runs, and draws panel letters the
same way. The v1 ``place_schematic_panel`` helper is deliberately NOT ported: the
new system sizes every panel from the grid (see FIGURE_SYSTEM_PLAN.md, "Knobs"),
so there is no panel-level axes resize that overflows its cell.

Contents:
- ``draw_band``       — mean line with a shaded uncertainty band.
- ``style_log_axes``  — quiet log-x quantitative-panel styling.
- ``mean_band`` / ``gmean_band`` — per-size run aggregation to (centre, lo, hi).
- ``exp_average``     — the RL scripts' exponential trial-length smoothing.
- ``panel_label``     — one house-style panel letter at figure coordinates.
"""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from scipy import stats

from .style import COLORS, PANEL_LABEL


# ── drawing ──────────────────────────────────────────────────────────────────
def draw_band(ax: Axes, x, centre, lower, upper, *, color, label, marker="o") -> None:
    """Central-tendency line with a shaded [lower, upper] band, sorted by x."""
    order = np.argsort(np.asarray(x, float))
    x = np.asarray(x, float)[order]
    ax.fill_between(x, np.asarray(lower, float)[order], np.asarray(upper, float)[order],
                    color=color, alpha=0.16, linewidth=0, zorder=1)
    ax.plot(x, np.asarray(centre, float)[order], color=color, marker=marker, markersize=4.2,
            markeredgewidth=0.9, linewidth=1.45, label=label, zorder=3)


def style_log_axes(ax: Axes, *, xlabel: str = "Trainable parameters",
                   ylabel: str = "", title: str | None = None) -> None:
    """Log-x quantitative panel: y-grid, hidden top/right spines, quiet ticks."""
    ax.set_xscale("log")
    if title:
        ax.set_title(title, pad=4, weight="semibold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which="major", axis="y", color=COLORS["grid"], linewidth=0.55, alpha=0.75)
    ax.grid(False, which="minor")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(colors=COLORS["axis"], pad=2)


def attach_colorbar(cax: Axes, mappable, *, label: str | None = None, outline_lw: float = 0.6):
    """Draw a house-styled colorbar into a dedicated grid cell ``cax``.

    The colorbar has its OWN grid cell: declare its width and the gap before it as
    columns in the layout, so the geometry stays grid-driven (never a post-hoc steal
    of space). Matching the bar's height to a heatmap is the LAYOUT's job, not this
    helper's: give an equal-aspect (square) heatmap a square cell and the colorbar a
    cell of that same height (see figure_feynman), and the bar fills its cell and
    equals the image by construction. ``mappable`` is the image/pcolormesh to map.
    """
    fig = cax.figure
    cb = fig.colorbar(mappable, cax=cax)
    cb.outline.set_linewidth(outline_lw)
    cax.tick_params(colors=COLORS["axis"], width=0.7, length=2.5)
    if label:
        cb.set_label(label)
    return cb


# ── layout ───────────────────────────────────────────────────────────────────
def panel_label(fig, label, x, y, **overrides) -> None:
    """Draw a panel letter (a, b, c, …) at figure coords (x, y) in the house style.

    One shared helper so every figure draws its panel letters identically. The shared
    default (PANEL_LABEL in style.py) uses va="bottom" — the letter rises ABOVE the
    anchor y, clear of the title and top tick. A figure whose layout needs the letter to
    hang from the top passes ``va="top"`` (and should say why at the call site).
    """
    fig.text(x, y, label, **{**PANEL_LABEL, **overrides})


# ── aggregation ──────────────────────────────────────────────────────────────
# Spread conventions (deliberate, see audits/band_statistics.md): the arithmetic band
# uses the POPULATION std (numpy's ddof=0 default) and the geometric band the SAMPLE
# gstd (scipy's ddof=1 default) — each matching the library default the original
# published scripts used, so the plotted bands reproduce the published ones.
def mean_band(values) -> "tuple[float, float, float]":
    """Arithmetic (mean, mean-std, mean+std) over a size's run values (ddof=0)."""
    v = np.asarray(values, float)
    m, s = float(v.mean()), float(v.std())
    return m, m - s, m + s


def gmean_band(values) -> "tuple[float, float, float]":
    """Geometric (gmean, gmean/gstd, gmean*gstd) — for log-distributed metrics
    such as MSE (gstd ddof=1). Multiplicative spread, no band for one sample."""
    v = np.asarray(values, float)
    g = float(stats.gmean(v))
    gs = float(stats.gstd(v)) if v.size > 1 else 1.0
    return g, g / gs, g * gs


def exp_average(signal, tau: float = 10.0, dt: float = 1.0) -> np.ndarray:
    """Exponentially-smoothed copy of a 1-D signal: y[i] = (1-a)·y[i-1] + a·x[i], a = dt/tau.

    The RL scripts' trial-length smoothing, verbatim (y[0] = 0 as in the originals);
    its peak is the per-run "best upright duration" the CartPole panels reduce to.
    Defined once here — previously duplicated by the cartpole and memkan builds."""
    out = np.zeros_like(signal, dtype=float)
    alpha = dt / tau
    for i in range(1, len(signal)):
        out[i] = (1 - alpha) * out[i - 1] + alpha * signal[i]
    return out
