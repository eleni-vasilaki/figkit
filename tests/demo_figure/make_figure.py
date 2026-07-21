#!/usr/bin/env python3
"""figkit demo/test figure: the framework exercised on synthetic distributions.

NOT a manuscript figure. This is figkit's regression test: it builds a
multi-panel figure purely through the framework, from seeded made-up data, and
then CHECKS itself two ways:
  1. known-answer checks — the statistics helpers are run on tiny inputs whose
     correct output is computed by hand (e.g. mean_band([1,2,3]) must be
     2.0 +- 0.8165, the population std);
  2. geometry checks — after drawing, the rendered axes are measured and must
     sit at exactly the margins/gaps/width the manifest declares, in inches.
Run it after editing figkit; read the printed PASS/FAIL lines and look at the
output PNG. Any FAIL exits non-zero.

  conda run -n myml python tests/demo_figure/make_figure.py

Panels (each exercises one figkit feature):
  a  mean +- std bands vs size, log-x      — config.resolve_runs over generated
                                             .npy run files + plotting.mean_band
  b  geometric bands on lognormal "MSE"    — plotting.gmean_band, log-y
  c  two overlaid histograms               — palette roles on plain axes
  d  noisy signal + exponential smoothing  — plotting.exp_average
  e  Gaussian-bump heatmap with colorbar   — plotting.attach_colorbar in its own
                                             subgrid column (reasoned non-uniform split)
  f  random walk, full | zoom pair         — uniform layout.subgrid split
  g  full-width pipeline diagram           — every figkit.schematic drawing primitive
                                             (box, curve_in, connect, node_circle,
                                             draw_network, arrow, open_axes_miniplot),
                                             plus schematic.preview standalone render

Beyond the panels, the script also checks the framework's REFUSALS: a handful of
deliberately bad manifests and layout calls must each be rejected with the clear
error message figkit promises (the reason-enforcement contract), and figkit.modload
must load a module by path and register it in sys.modules.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
from pathlib import Path

FIGURE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = FIGURE_DIR.parents[1]
if not ((_REPO_ROOT / "figkit").is_dir() and (_REPO_ROOT / "figures").is_dir()):
    raise RuntimeError(f"Could not find PhyKAN repository root from {__file__}")
sys.path.insert(0, str(_REPO_ROOT))

# No matplotlib.use() here on purpose: figkit.bootstrap must provide the headless
# Agg backend itself. The interactive macOS backend snaps the canvas to integer
# screen pixels (8.19 in instead of 8.2), so if bootstrap ever stops setting the
# backend, the exact geometry checks below fail — that is part of the test.
from figkit import config, layout, plotting, schematic, style  # noqa: E402
from figkit.modload import load_module  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

DATA = FIGURE_DIR / "data"
OUT = FIGURE_DIR / "outputs" / "demo_figure.png"

TEAL = style.COLORS["primary"]     # featured series
ORANGE = style.COLORS["accent"]    # highlight series
SLATE = style.COLORS["baseline"]   # comparison series
INK = style.COLORS["axis"]

CONFIG = config.load(FIGURE_DIR)
RUN_REPORT: "dict[str, dict[int, int]]" = {}

SIZES = [4, 8, 16, 32, 64, 128]
N_RUNS = 5
WIDE_RX = r"demo wide, N=(?P<n>\d+), Run=(?P<run>\d+)\.npy"
NARROW_RX = r"demo narrow, N=(?P<n>\d+), Run=(?P<run>\d+)\.npy"

_failures: "list[str]" = []


def expect(name: str, got: float, want: float, tol: float = 5e-3) -> None:
    """One PASS/FAIL line; failures are collected and fail the run at the end."""
    ok = abs(got - want) <= tol
    if not ok:
        _failures.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got:.4f} (expected {want:.4f})")


# ── known-answer checks: the statistics helpers on hand-computed inputs ───────
def check_stats() -> None:
    print("known-answer checks (statistics helpers):")
    m, lo, hi = plotting.mean_band([1.0, 2.0, 3.0])
    s = np.sqrt(2.0 / 3.0)                       # population std (ddof=0) by hand
    expect("mean_band centre", m, 2.0, 1e-9)
    expect("mean_band lower", lo, 2.0 - s, 1e-9)
    expect("mean_band upper", hi, 2.0 + s, 1e-9)

    g, glo, ghi = plotting.gmean_band([1.0, 100.0])
    expect("gmean_band centre (gmean of 1,100)", g, 10.0, 1e-9)
    expect("gmean_band multiplicative symmetry", g / glo, ghi / g, 1e-9)
    g1, glo1, ghi1 = plotting.gmean_band([5.0])
    expect("gmean_band single sample: no band", ghi1 - glo1, 0.0, 1e-12)

    y = plotting.exp_average([1.0, 1.0, 1.0], tau=10.0)  # a=0.1: y = 0, 0.1, 0.19
    expect("exp_average y[0] (starts at 0)", y[0], 0.0, 1e-12)
    expect("exp_average y[1]", y[1], 0.1, 1e-12)
    expect("exp_average y[2]", y[2], 0.19, 1e-12)


def expect_rejection(name: str, fn, fragment: str) -> None:
    """The framework must REFUSE this call, naming the problem (``fragment``)."""
    try:
        fn()
    except Exception as err:
        ok = fragment in str(err)
        detail = "" if ok else f" (error does not mention {fragment!r}: {err})"
    else:
        ok, detail = False, " (accepted — no error raised)"
    if not ok:
        _failures.append(f"rejects {name}")
    print(f"  {'PASS' if ok else 'FAIL'}  rejects {name}{detail}")


# ── rejection checks: bad manifests must be refused with a clear message ──────
BAD_MANIFESTS = {
    "an unknown [layout] field": ("[layout]\nfoo = 3\n", "unknown field"),
    "a reasoned knob without its reason": ("[layout]\nwspace_in = 0.9\n",
                                           "no wspace_in_reason"),
    "a fixed height without a reason": ("[canvas]\nheight = 5.0\n", "escape hatch"),
    "non-uniform col_ratios without a reason": (
        "[layout]\ncols = 2\ncol_ratios = [2.0, 1.0]\n", "no col_ratios_reason"),
    "row_heights_in combined with row_ratios": (
        '[layout]\nrows = 2\nrow_ratios = [1.0, 2.0]\nrow_ratios_reason = "demo"\n'
        'row_heights_in = [1.0, 1.0]\nrow_heights_in_reason = "demo"\n', "not both"),
}


def check_config_rejections() -> None:
    print("rejection checks (config: bad manifests must be refused):")
    with tempfile.TemporaryDirectory() as tmp:
        bad_dir = Path(tmp)
        expect_rejection("a folder with no figure.toml",
                         lambda: config.load(bad_dir), "no figure.toml")
        for name, (toml_text, fragment) in BAD_MANIFESTS.items():
            (bad_dir / "figure.toml").write_text(toml_text)
            expect_rejection(name, lambda: config.load(bad_dir), fragment)
    expect_rejection("a mistyped section key (config.require)",
                     lambda: config.require({"phykan": 1}, "phykan_typo"), "valid fields")


def check_layout_rejections(fig, parent_cell, ax) -> None:
    """Reason-enforced layout/schematic exceptions must refuse reason-less calls.
    Each call raises before touching anything, so the built figure is unaffected."""
    print("rejection checks (layout/schematic: exceptions need a reason):")
    expect_rejection("a non-uniform subgrid without a reason",
                     lambda: layout.subgrid(fig, parent_cell, 1, 2, col_ratios=[2.0, 1.0]),
                     "needs reason")
    expect_rejection("adjust_frame with an empty reason",
                     lambda: layout.adjust_frame(ax, dx_in=0.1, reason=""), "needs reason")
    expect_rejection("a grid override without a reason",
                     lambda: layout.grid(fig, CONFIG["layout"], wspace_in=0.9),
                     "add reason=")
    expect_rejection("a shifted panel letter without a reason",
                     lambda: layout.place_panel_letters(fig, {"a": ax},
                                                        shifts={"a": (0.1, 0.0)}),
                     "add reason=")
    scratch = plt.figure(figsize=(1, 1))
    sax = scratch.add_subplot()
    expect_rejection("framed art scaled without a reason",
                     lambda: schematic.place_framed_image(sax, np.zeros((4, 4, 3)), scale=1.3),
                     "needs")
    plt.close(scratch)


# ── under-selection: a declared run count that is not met must be loud and logged ──
def check_under_selection() -> None:
    """A `runs = N` the data does not meet must warn, be logged, and not fail the build.

    The real figures declare explicit run counts (cartpole `runs = 20`, memkan `runs = 10`),
    and a silently short series would weaken a band without changing anything visible. So
    the contract is checked here on synthetic files: N=4 is complete, N=8 is missing run 1.
    The log is the artifact that matters — the raw bundle is gitignored, so it is the only
    record a fresh clone gets of what went into the tables.
    """
    print("under-selection checks (a declared runs = N that is not met):")
    regex = r"under, N=(?P<n>\d+), Run=(?P<run>\d+)\.npy"
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        for n, present in ((4, (0, 1, 2)), (8, (0, 2))):     # N=8 is missing run 1
            for run in present:
                (folder / f"under, N={n}, Run={run}.npy").write_bytes(b"")

        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            runs = config.resolve_runs(folder, regex, {"sizes": "auto", "runs": 3})
            log = config.write_extraction_log(folder / "log_dir")
        warning, text = printed.getvalue(), log.read_text()

        expect("complete size keeps all 3 runs", len(runs[4]), 3, 0)
        expect("short size returns only what exists", len(runs[8]), 2, 0)
        for name, ok in (
            ("warns on stdout", "UNDER-SELECTED" in warning),
            ("warning names the missing run", "missing run(s) [1]" in warning),
            ("log records the shortfall", "UNDER-SELECTED SERIES (1)" in text),
            ("log names the short size", "N=8: declared 3, found 2" in text),
            ("log records the complete size too", "{4: 3, 8: 2}" in text),
            ("log path is repo-relative or absolute, never blank", "folder:" in text),
        ):
            if not ok:
                _failures.append(name)
            print(f"  {'PASS' if ok else 'FAIL'}  {name}")

        # Writing DRAINS the record: a second log must not repeat the first one's series.
        with contextlib.redirect_stdout(io.StringIO()):
            second = config.write_extraction_log(folder / "log_dir_2")
        drained = "All declared run counts were met." in second.read_text()
        if not drained:
            _failures.append("write_extraction_log drains its record")
        print(f"  {'PASS' if drained else 'FAIL'}  write_extraction_log drains its record "
              f"(a second log repeats nothing)")


def check_modload() -> None:
    print("modload checks:")
    with tempfile.TemporaryDirectory() as tmp:
        mod_path = Path(tmp) / "demo_mod.py"
        mod_path.write_text("VALUE = 42\n")
        mod = load_module("figkit_demo_mod", mod_path, register=True)
        registered = sys.modules.get("figkit_demo_mod") is mod
        ok = mod.VALUE == 42 and registered
        if not ok:
            _failures.append("modload")
        print(f"  {'PASS' if ok else 'FAIL'}  load_module by path "
              f"(VALUE={mod.VALUE}, registered in sys.modules={registered})")
        del sys.modules["figkit_demo_mod"]


# ── panel a data: seeded per-run .npy files, one file per (series, N, run) ────
def generate_run_files() -> None:
    if DATA.is_dir() and any(DATA.iterdir()):
        return
    DATA.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    for n in SIZES:
        for run in range(N_RUNS):
            wide = rng.normal(2.0 + 8.0 / np.sqrt(n), 0.6, size=50)
            narrow = rng.normal(1.0 + 4.0 / np.sqrt(n), 0.2, size=50)
            np.save(DATA / f"demo wide, N={n}, Run={run}.npy", wide)
            np.save(DATA / f"demo narrow, N={n}, Run={run}.npy", narrow)
    print(f"generated seeded demo run files in {DATA}")


def draw_panel_a(ax) -> None:
    """Bands vs size through the real pipeline: resolve_runs -> mean_band -> draw_band."""
    for key, regex, color in (("wide", WIDE_RX, ORANGE), ("narrow", NARROW_RX, TEAL)):
        entry = config.require(CONFIG["panel_a"], key)
        runs_by_n = config.resolve_runs(DATA, regex, entry)
        xs, c, lo, hi = [], [], [], []
        for n in sorted(runs_by_n):
            m, l, h = plotting.mean_band([float(np.load(p).mean()) for p in runs_by_n[n]])
            xs.append(n); c.append(m); lo.append(l); hi.append(h)
        plotting.draw_band(ax, xs, c, lo, hi, color=color, label=key)
        RUN_REPORT[f"panel_a {key}"] = {n: len(f) for n, f in runs_by_n.items()}
    plotting.style_log_axes(ax, xlabel="Size N", ylabel="Sample mean",
                            title="mean_band over runs")
    ax.legend(**style.LEGEND)


def draw_panel_b(ax) -> None:
    """Geometric bands on a lognormal, MSE-like decreasing series."""
    rng = np.random.default_rng(1)
    xs, c, lo, hi = [], [], [], []
    for n in SIZES:
        vals = rng.lognormal(mean=np.log(1.0 / n), sigma=0.5, size=6)
        g, l, h = plotting.gmean_band(vals)
        xs.append(n); c.append(g); lo.append(l); hi.append(h)
    plotting.draw_band(ax, xs, c, lo, hi, color=TEAL, label="lognormal")
    plotting.style_log_axes(ax, xlabel="Size N", ylabel="Synthetic MSE",
                            title="gmean_band, log-y")
    ax.set_yscale("log")


def draw_panel_c(ax) -> None:
    """Two overlaid histograms in the palette roles."""
    rng = np.random.default_rng(2)
    bins = np.linspace(-4, 7, 45)
    ax.hist(rng.normal(0.0, 1.0, 4000), bins=bins, color=TEAL, alpha=0.75, label="N(0, 1)")
    ax.hist(rng.normal(2.5, 1.4, 4000), bins=bins, color=ORANGE, alpha=0.65, label="N(2.5, 1.4)")
    ax.set_title("histograms", pad=4, weight="semibold")
    ax.set_xlabel("Value"); ax.set_ylabel("Count")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(**style.LEGEND)


def draw_panel_d(ax) -> None:
    """Noisy learning-curve-like signal with the RL scripts' exponential smoothing."""
    rng = np.random.default_rng(3)
    raw = rng.normal(np.linspace(0.0, 1.0, 400), 0.15)
    ax.plot(raw, color=SLATE, linewidth=0.6, alpha=0.45, label="raw")
    ax.plot(plotting.exp_average(raw), color=TEAL, linewidth=1.6, label="exp_average")
    ax.set_title("exp_average", pad=4, weight="semibold")
    ax.set_xlabel("Step"); ax.set_ylabel("Signal")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(**{**style.LEGEND, "loc": "upper left"})


def draw_panel_e(fig, cell) -> "tuple":
    """Gaussian-bump heatmap; the colorbar gets its OWN subgrid column."""
    sub = layout.subgrid(fig, cell, 1, 2, col_ratios=[1.0, 0.07], wspace_in=0.08,
                         reason="demo: colorbar column, exercising the reasoned non-uniform split")
    ax, cax = fig.add_subplot(sub[0, 0]), fig.add_subplot(sub[0, 1])
    x = np.linspace(-2, 2, 80)
    X, Y = np.meshgrid(x, x)
    Z = np.exp(-((X - 0.5) ** 2 + (Y + 0.3) ** 2)) - 0.6 * np.exp(-2 * ((X + 1) ** 2 + Y ** 2))
    im = ax.imshow(Z, extent=(-2, 2, -2, 2), origin="lower", aspect="auto", cmap="viridis")
    plotting.attach_colorbar(cax, im, label="Amplitude")
    ax.set_title("attach_colorbar", pad=4, weight="semibold")
    ax.set_xlabel("x"); ax.set_ylabel("y")
    return ax, cax


def draw_panel_f(fig, cell) -> "tuple":
    """Random walk as a full | zoom pair, the cartpole-style uniform subgrid."""
    sub = layout.subgrid(fig, cell, 1, 2, wspace_in=0.18)
    ax_full, ax_zoom = fig.add_subplot(sub[0, 0]), fig.add_subplot(sub[0, 1])
    rng = np.random.default_rng(4)
    walk = np.cumsum(rng.normal(0.0, 1.0, 500))
    span = float(np.abs(walk).max()) * 1.1
    for ax, end in ((ax_full, 500), (ax_zoom, 100)):
        ax.axvspan(0, 100, color=ORANGE, alpha=0.18, lw=0, zorder=0)
        ax.plot(walk[:end], color=INK, linewidth=1.0)
        ax.set_xlim(0, end)
        ax.set_ylim(-span, span)   # shared scale: the zoom's hidden ticks match the full walk
        ax.set_title("full walk" if end == 500 else "first 100", pad=4, weight="semibold")
        ax.set_xlabel("Step")
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    ax_full.set_ylabel("Position")
    ax_zoom.tick_params(labelleft=False)
    return ax_full, ax_zoom


def draw_panel_g(ax) -> None:
    """Every schematic drawing primitive once, composed as a little pipeline:
    box + curve_in -> connect (with a node_circle waypoint) -> dashed box around
    draw_network -> arrow -> open_axes_miniplot."""
    S = style.SCHEMATIC_STYLE
    ax.set_xlim(0, 11)
    ax.set_ylim(-0.05, 2.35)
    ax.set_aspect("equal")
    ax.set_axis_off()
    schematic.box(ax, 0.35, 0.45, 1.9, 1.1)
    t = np.linspace(0.0, 4.0 * np.pi, 120)
    schematic.curve_in(ax, 0.35, 0.45, 1.9, 1.1, t, np.sin(t), logx=False, symmetric=True)
    schematic.text(ax, 1.3, 1.8, "box + curve_in", S["box_text_size"])
    schematic.connect(ax, 2.35, 1.0, 3.3, 1.0, dashed=True)
    schematic.node_circle(ax, 2.83, 1.0, 0.07, color=style.SCHEMATIC["active"])
    schematic.box(ax, 3.4, 0.3, 2.9, 1.4, dashed=True)
    schematic.draw_network(ax, [3.95, 4.85, 5.75],
                           [[0.7, 1.3], [0.55, 1.0, 1.45], [1.0]], 0.12,
                           node_color=[style.SCHEMATIC["passive"],
                                       style.COLORS["primary"], style.COLORS["primary"]])
    schematic.text(ax, 4.85, 1.95, "draw_network", S["box_text_size"])
    schematic.arrow(ax, 6.6, 7.4, 1.0)
    f = np.logspace(0, 3, 90)
    resp = np.exp(-0.5 * ((np.log10(f) - 1.5) / 0.35) ** 2)
    schematic.open_axes_miniplot(ax, 7.7, 0.5, 2.6, 1.0, f, resp, title="open_axes_miniplot")


# ── geometry checks: the rendered axes must equal the declared inches ─────────
def check_geometry(fig, axes: dict) -> None:
    print("geometry checks (rendered axes vs figure.toml, inches):")
    W, H = fig.get_size_inches()
    lay = CONFIG["layout"]
    rows, cols = lay["rows"], lay["cols"]
    a = axes["a"].get_position(original=True)
    b = axes["b"].get_position(original=True)
    c = axes["c"].get_position(original=True)
    d = axes["d"].get_position(original=True)
    g = axes["g"].get_position(original=True)
    expect("canvas width = shared FIGURE_WIDTH", W, style.FIGURE_WIDTH)
    expect("left margin", a.x0 * W, lay["margin_left_in"])
    expect("right margin", (1 - c.x1) * W, lay["margin_right_in"])
    expect("top margin", (1 - a.y1) * H, lay["margin_top_in"])
    expect("bottom margin", g.y0 * H, lay["margin_bottom_in"])
    expect("column gap", (b.x0 - a.x1) * W, lay["wspace_in"])
    expect("row gap", (a.y0 - d.y1) * H, lay["hspace_in"])
    expect("panel g spans the full row", (g.x1 - g.x0) * W,
           W - lay["margin_left_in"] - lay["margin_right_in"])
    # auto height: margins + rows * (mean column width / panel_aspect) + row gaps
    usable_w = (W - lay["margin_left_in"] - lay["margin_right_in"]
                - (cols - 1) * lay["wspace_in"])
    ref_h = (usable_w / cols) / lay["panel_aspect"]
    expect("auto-derived height", H,
           lay["margin_top_in"] + lay["margin_bottom_in"]
           + rows * ref_h + (rows - 1) * lay["hspace_in"])
    cw, ch = layout.cell_size_in(CONFIG)
    expect("cell_size_in width vs rendered panel a", cw, a.width * W)
    expect("cell_size_in height vs rendered panel a", ch, a.height * H)


def main() -> None:
    style.apply_matplotlib_style()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    check_stats()
    check_config_rejections()
    check_under_selection()      # before panel a resolves runs, so it starts from a clean record
    check_modload()
    generate_run_files()

    fig = layout.new_figure(CONFIG)
    grid = layout.grid(fig, CONFIG["layout"])
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[0, 2])
    ax_d = fig.add_subplot(grid[1, 0])

    draw_panel_a(ax_a)
    draw_panel_b(ax_b)
    draw_panel_c(ax_c)
    draw_panel_d(ax_d)
    ax_e, _ = draw_panel_e(fig, grid[1, 1])
    ax_f, _ = draw_panel_f(fig, grid[1, 2])
    ax_g = fig.add_subplot(grid[2, :])
    draw_panel_g(ax_g)

    config.report_runs(RUN_REPORT)
    layout.place_panel_letters(fig, {"a": ax_a, "b": ax_b, "c": ax_c,
                                     "d": ax_d, "e": ax_e, "f": ax_f, "g": ax_g})

    fig.savefig(OUT, facecolor="white")
    print(f"Wrote {OUT}")

    # Standalone panel render through schematic.preview (one grid CELL, so the art
    # shows letterboxed in the narrower single-column box — that is expected here;
    # the check is that preview runs and writes the panel at its real cell size).
    p = schematic.preview(CONFIG, draw_panel_g, OUT.parent / "panel_g_preview.png",
                          letter="g", row=2, col=0)
    print(f"Wrote {p} (schematic.preview)")

    check_geometry(fig, {"a": ax_a, "b": ax_b, "c": ax_c, "d": ax_d, "g": ax_g})
    check_layout_rejections(fig, grid[0, 0], ax_c)
    if _failures:
        raise SystemExit(f"FAILED checks: {', '.join(_failures)}")
    print("all checks passed")


if __name__ == "__main__":
    main()
