"""Manifest loader: read a figure's figure.toml into a plain, validated dict.

This is the single gate every figure passes through. It reads the TOML, fills
framework defaults, checks required fields, enforces that spacing/aspect/height
knobs which depart from the default carry a reason, and raises clear errors that
name the field and the fix. Figures and figkit then work with the returned dict;
nothing else re-reads the raw file. There is deliberately NO spec object or config
class — dictionaries only (see FIGURE_SYSTEM_PLAN.md, "Loading The Manifest").

Public API:
- ``load(figure_dir)``               -> validated config dict
- ``require(section, key)``          -> value, or a clear error listing valid keys
- ``resolve_runs(folder, regex, e)`` -> {size: [run file paths]} for a file series
- ``write_extraction_log(out_dir)``  -> persist what resolve_runs selected
- ``report_runs(named_counts)``      -> print runs-per-point, flag non-uniform series

The run-selection helpers are manifest-driven: they select the sizes/runs the
manifest declares. ``sizes``/``runs`` may be the literal ``"auto"``.
"""

from __future__ import annotations

import re
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any

from .bootstrap import REPO_ROOT
from .style import FIGURE_WIDTH

MM_PER_IN = 25.4

# Framework defaults. A figure overrides these in [canvas] / [layout]; the width
# defaults to the shared house width so every figure is authored at one width.
_CANVAS_DEFAULTS: dict[str, Any] = {
    "width_in": FIGURE_WIDTH,
    "height": "auto",           # "auto" (computed) or a height in inches (escape hatch)
}
_LAYOUT_DEFAULTS: dict[str, Any] = {
    "rows": 1,
    "cols": 1,
    "panel_aspect": 1.33,        # panel_width / panel_height, about 4:3
    "margin_left_in": 0.70,
    "margin_right_in": 0.20,
    "margin_top_in": 0.45,
    "margin_bottom_in": 0.55,
    "wspace_in": 0.60,
    "hspace_in": 0.70,
    "col_ratios": None,          # None -> uniform [1, 1, ...]; else one weight per column
    "row_ratios": None,          # None -> uniform [1, 1, ...]; else one weight per row
    "row_heights_in": None,      # None -> rows sized by ratios; else physical inches per
                                 # row, and the canvas height is DERIVED to honour them
                                 # exactly (the height dual of wspace_in/hspace_in).
}
# Knobs whose departure from the default must be justified with a sibling reason.
# (col_ratios/row_ratios are reason-checked separately, against a uniform default.)
_REASONED = {
    "panel_aspect", "wspace_in", "hspace_in",
    "margin_left_in", "margin_right_in", "margin_top_in", "margin_bottom_in",
}


class ConfigError(ValueError):
    """A figure.toml problem, phrased to name the field and the fix."""


def _merge(defaults: dict, given: dict, section: str) -> dict:
    """Overlay ``given`` onto ``defaults``; reject keys that are not known knobs."""
    known = (set(defaults) | {f"{k}_reason" for k in _REASONED}
             | {"height_reason", "col_ratios_reason", "row_ratios_reason",
                "row_heights_in_reason"})
    out = dict(defaults)
    for key, val in given.items():
        if key not in known:
            valid = ", ".join(sorted(defaults))
            raise ConfigError(
                f"[{section}] has unknown field {key!r}. valid fields: {valid}")
        out[key] = val
    return out


def _check_reasons(layout: dict) -> None:
    """Every reasoned knob that departs from its default needs a sibling reason."""
    for key in _REASONED:
        if key in layout and layout[key] != _LAYOUT_DEFAULTS[key]:
            if not layout.get(f"{key}_reason"):
                raise ConfigError(
                    f"[layout] {key} = {layout[key]} departs from the default "
                    f"{_LAYOUT_DEFAULTS[key]} but has no {key}_reason. "
                    f"Add {key}_reason = \"...\" saying why.")


def load(figure_dir: Path) -> dict:
    """Read ``<figure_dir>/figure.toml`` into a validated config dict."""
    figure_dir = Path(figure_dir)
    toml_path = figure_dir / "figure.toml"
    if not toml_path.is_file():
        raise ConfigError(f"no figure.toml in {figure_dir}")
    with open(toml_path, "rb") as fh:
        raw = tomllib.load(fh)

    raw_canvas = dict(raw.get("canvas", {}))
    if "width_mm" in raw_canvas:                     # allow mm, store inches
        raw_canvas["width_in"] = float(raw_canvas.pop("width_mm")) / MM_PER_IN
    canvas = _merge(_CANVAS_DEFAULTS, raw_canvas, "canvas")
    height = canvas["height"]
    if height != "auto":
        if not isinstance(height, (int, float)):
            raise ConfigError(f"[canvas] height must be \"auto\" or a number, got {height!r}")
        if not canvas.get("height_reason"):
            raise ConfigError(
                "[canvas] a fixed height is an escape hatch; add "
                "height_reason = \"...\" saying why auto-height is not used.")

    layout = _merge(_LAYOUT_DEFAULTS, raw.get("layout", {}), "layout")
    for key in ("rows", "cols"):
        if not isinstance(layout[key], int) or layout[key] < 1:
            raise ConfigError(f"[layout] {key} must be a positive integer, got {layout[key]!r}")
    _check_reasons(layout)

    # col_ratios/row_ratios: default uniform; a non-uniform grid needs a reason.
    for key, n, what in (("col_ratios", layout["cols"], "column"),
                         ("row_ratios", layout["rows"], "row")):
        val = layout.get(key)
        if val is None:
            layout[key] = [1.0] * n
            continue
        if len(val) != n:
            raise ConfigError(f"[layout] {key} must have {n} numbers (one per {what}), got {len(val)}")
        val = [float(x) for x in val]
        if val != [1.0] * n and not layout.get(f"{key}_reason"):
            raise ConfigError(
                f"[layout] {key} = {val} is non-uniform but has no {key}_reason. "
                f"Add {key}_reason = \"...\" saying why (e.g. giving a schematic panel more room).")
        layout[key] = val

    # row_heights_in: physical inches per row (opt-in). When present, the canvas height is
    # DERIVED to honour them exactly (layout._geometry), so it cannot be combined with a
    # fixed [canvas] height or with row_ratios, and it needs a reason like the ratio knobs.
    rh = layout.get("row_heights_in")
    if rh is not None:
        if height != "auto":
            raise ConfigError(
                "[layout] row_heights_in derives the canvas height, so [canvas] height "
                "must be \"auto\" (remove the fixed height).")
        if raw.get("layout", {}).get("row_ratios") is not None:
            raise ConfigError(
                "[layout] give row_heights_in OR row_ratios, not both — row_heights_in "
                "sets the heights directly.")
        if len(rh) != layout["rows"]:
            raise ConfigError(
                f"[layout] row_heights_in must have {layout['rows']} numbers (one per row), "
                f"got {len(rh)}")
        rh = [float(x) for x in rh]
        if any(x <= 0 for x in rh):
            raise ConfigError(f"[layout] row_heights_in must be positive inches, got {rh}")
        if not layout.get("row_heights_in_reason"):
            raise ConfigError(
                "[layout] row_heights_in departs from the default (ratio row sizing); add "
                "row_heights_in_reason = \"...\" saying why each row's height is what it is.")
        layout["row_heights_in"] = rh

    cfg = dict(raw)                    # keep the data sections (panel_*) as declared
    cfg["canvas"] = canvas
    cfg["layout"] = layout
    return cfg


def require(section: dict, key: str) -> Any:
    """Read ``section[key]``, or raise naming the bad key and the valid ones.

    Use instead of a bare ``section[key]`` so a mistyped key fails with a readable
    message rather than a plain KeyError.
    """
    if key not in section:
        valid = ", ".join(sorted(map(str, section))) or "(none)"
        raise ConfigError(f"no field {key!r}; valid fields: {valid}")
    return section[key]


# ── manifest-driven run selection (per-run file series) ──────────────────────
# resolve_runs appends to these as a figure's extract_data.py resolves each series;
# write_extraction_log drains them to a committed log beside the extracted tables.
_SELECTION_LOG: "list[str]" = []
_SELECTION_WARNINGS: "list[str]" = []


def _repo_relative(path: Path) -> str:
    """Path relative to the repo root, so the committed log is machine-independent."""
    path = Path(path).resolve()
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _discover(folder: Path, regex: str) -> "dict[int, dict[int, Path]]":
    """Group files in ``folder`` by (size, run) using a full-match regex with
    named groups ``n`` and ``run``."""
    rx = re.compile(regex)
    found: "dict[int, dict[int, Path]]" = defaultdict(dict)
    for path in Path(folder).iterdir():
        match = rx.fullmatch(path.name)
        if match is not None:
            found[int(match.group("n"))][int(match.group("run"))] = path
    return found


def resolve_runs(folder: Path, regex: str, entry: dict) -> "dict[int, list[Path]]":
    """Select the run files for one file-per-run series, per its manifest entry.

    ``entry['sizes']`` is an explicit list or ``"auto"`` (every size present).
    ``entry['runs']`` is an int (use runs ``0..N-1``) or ``"auto"`` (all present).
    Raises if the manifest asks for a size with no matching files.

    A declared ``runs = N`` is an expectation, so a size that yields fewer than N files
    is under-selected: it warns and records the shortfall rather than failing, because a
    partly-complete series is still worth extracting while the gap is chased. Every
    resolution is recorded either way; ``write_extraction_log`` persists the record
    beside the extracted tables, where a fresh clone can read it without ``raw_data/``.
    """
    available = _discover(folder, regex)
    sizes = entry["sizes"]
    chosen = sorted(available) if sizes == "auto" else list(sizes)
    runs = entry.get("runs", "auto")
    out: "dict[int, list[Path]]" = {}
    short: "list[str]" = []
    for n in chosen:
        runs_map = available.get(n, {})
        if not runs_map:
            raise FileNotFoundError(
                f"figure.toml lists size N={n} but no files match in {folder}")
        if runs == "auto":
            out[n] = [runs_map[r] for r in sorted(runs_map)]
        else:
            want = int(runs)
            out[n] = [runs_map[r] for r in range(want) if r in runs_map]
            if len(out[n]) < want:
                absent = [r for r in range(want) if r not in runs_map]
                short.append(f"N={n}: declared {want}, found {len(out[n])}, "
                             f"missing run(s) {absent}")

    declared = "auto" if runs == "auto" else f"runs = {runs}"
    found = {n: len(paths) for n, paths in out.items()}
    _SELECTION_LOG.append(f"{regex}\n  folder:   {_repo_relative(folder)}\n"
                          f"  declared: {declared}\n  found:    {found}")
    for line in short:
        print(f"WARNING  UNDER-SELECTED  {regex}  {line}")
        _SELECTION_LOG.append(f"  !! {line}")
        _SELECTION_WARNINGS.append(f"{regex}  {line}")
    return out


def write_extraction_log(out_dir: Path, name: str = "extraction_log.txt") -> Path:
    """Write what ``resolve_runs`` selected into ``out_dir``, and return the path.

    Called at the end of a figure's ``extract_data.py``. The raw bundle is local and
    gitignored, so this committed log is the only place a fresh clone can see which
    runs went into the tables — and which were declared but never found. It carries no
    timestamp, so re-running the extractor on unchanged data leaves the file unchanged.

    The record ``resolve_runs`` builds is module-global, so writing it DRAINS it: each
    log covers exactly the series resolved since the previous write. Without that, a
    second call would silently repeat the first log's entries and the committed
    provenance would claim series the tables beside it never used.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# Run selection recorded by figkit.config.resolve_runs.",
             "# Written by this figure's extract_data.py; do not edit by hand.",
             ""]
    if _SELECTION_WARNINGS:
        lines.append(f"UNDER-SELECTED SERIES ({len(_SELECTION_WARNINGS)}) — a declared "
                     "run count was not met:")
        lines += [f"  {w}" for w in _SELECTION_WARNINGS]
    else:
        lines.append("All declared run counts were met.")
    lines += ["", "Series resolved, in extraction order:", ""]
    lines += _SELECTION_LOG
    path = out_dir / name
    path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {path}")
    _SELECTION_LOG.clear()
    _SELECTION_WARNINGS.clear()
    return path


def report_runs(named_counts: "dict[str, dict[int, int]]",
                expected: "dict[str, int] | None" = None) -> None:
    """Print runs-per-point for each series, flagging non-uniform and short series.

    ``named_counts`` is what the plotter actually read, per series, per point.
    ``expected`` optionally maps a series name to the run count its manifest entry
    declares, making "expected vs found" visible at build time as well as in the
    extractor's log. A series with no declared count is marked ``(auto)``: its count is
    whatever the raw bundle held, so there is nothing to check it against.
    """
    expected = expected or {}
    print("Runs per plotted point (from the extracted tables):")
    for series, counts in named_counts.items():
        spread = sorted(set(counts.values()))
        flags = [] if len(spread) <= 1 else [f"NON-UNIFORM {spread}"]
        want = expected.get(series)
        if want is None:
            flags.append("auto")
        else:
            behind = {n: c for n, c in counts.items() if c < want}
            flags.append(f"SHORT of declared {want} at {behind}" if behind
                         else f"declared {want}, all met")
        print(f"  {series}: {counts}  <-- {'; '.join(flags)}")
