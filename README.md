# figkit

A small figure-making framework for research papers, built around one idea: a
manuscript figure should regenerate, at its exact published size, from committed
human-readable data — and every departure from the house style should carry its
reason at the point where it happens.

figkit was extracted from the PhyKAN paper repository, where it builds all the
manuscript figures. Source docstrings that cite `FIGURE_SYSTEM_PLAN.md` or a
`figure_...` panel refer to the design document and figures of that original repo;
the rules they encode are all present here, in `specs/` and the examples.

## Requirements

There is no install step — clone and run. Every script reaches `figkit` through a
small `sys.path` header at the top of the file (copy it from the template). The
environment needs:

- **Python ≥ 3.11** — `figkit` reads `figure.toml` with the standard-library `tomllib`.
- **numpy, scipy, matplotlib** — that is all; figkit has no other dependencies.

Verify a fresh setup end to end with the self-checking test figure:

```bash
python tests/demo_figure/make_figure.py
```

It builds a seven-panel figure, checks the statistics helpers against hand-computed
values, measures the rendered axes against the inches its manifest declares, and
confirms the framework refuses reason-less exceptions. Any failure exits non-zero.

## Where to start

1. **Read `examples/minimal_figure/`** — the smallest complete figure (~40 lines):
   one panel, one committed table, a mean ± std band, and the three rules every
   figure follows.
2. **Run `tests/demo_figure/`** — the fullest worked example. Its README maps each
   panel to the feature it demonstrates (subgrids, schematics, colorbars, geometric
   bands, run selection over per-run files).
3. **Copy `figures/_template/`** to `figures/figure_<name>/` when starting a real
   figure. The template is the full shape: manifest, extractor, pure plotter,
   caption, panels.

## The shape of a figure

```text
figures/figure_<name>/
  figure.toml          # geometry + selection knobs; every departure from a
                       #   default needs a sibling <knob>_reason
  extract_data.py      # reduce your raw data ONCE into committed TSV tables
  extracted_data/      # one row per individual observation, never a summary
    extraction_log.txt #   what was selected, and any shortfall vs the declared runs
  make_figure.py       # pure plotter: reads only the tables, derives every
                       #   mean/band at plot time, saves at the exact declared size
  CAPTION.md           # hand-written caption; provenance is prose, not config
  panels/              # per-panel render modules and schematic art
  outputs/             # the PNG + PDF this figure's code wrote
```

Raw data stays outside the figures (the convention is a repo-root `raw_data/`,
gitignored), so a fresh clone rebuilds every figure from the committed tables alone.

## Design rules, in one paragraph

All figures share one physical width (`figkit.style.FIGURE_WIDTH`); height derives
from the declared layout. Geometry is authored in inches in `figure.toml`, never in
plotting code, and never saved with `bbox_inches="tight"`. Tables hold individual
observations; statistics are derived at plot time so the reduction is visible in
code. Any call that departs from the house layout — a grid override, a non-uniform
subgrid, a shifted panel letter, a moved frame — must say why with a `reason=`, and
the framework refuses the call otherwise. `specs/CODE_SPECIFICATION.md` holds the
full house rules; `specs/scientific_coding_principles.md` the principles behind them.

Designed and specified by the author; implemented with Claude, with critical
review by Codex.
