# minimal_figure — the smallest complete figkit figure

A starting point to copy: one panel, one committed table, a mean ± std band. It exists
to show the shape of a figure with nothing else in the way.

```bash
conda run -n myml python examples/minimal_figure/make_figure.py
```

The data are **synthetic and seeded**. This is a framework example, not a scientific
result, and nothing here should be cited or reused as one.

## The shape

```text
minimal_figure/
  figure.toml                        # geometry (and, in a real figure, selection knobs)
  make_figure.py                     # pure plotter: reads the table, derives the band
  extracted_data/
    measurements.tsv                 # one row per observation, committed
  outputs/
    minimal_figure.png
```

A real figure adds `extract_data.py` (raw bundle → this table), `CAPTION.md`, and
`panels/`. Start from [figures/_template/](../../figures/_template/) for that full shape;
start here to understand the mechanism first.

## What it demonstrates

- **Geometry is declared, not coded.** `figure.toml` sets rows, columns, and the panel
  aspect; the width comes from the shared house width and the height is derived. No size
  is hardcoded in `make_figure.py`, and the figure saves at exactly that size — never
  `bbox_inches="tight"`, which would silently change the manuscript width.
- **Departures carry a reason.** `panel_aspect` differs from the default, so it has a
  `panel_aspect_reason`. `config.load` refuses the manifest without one. Try deleting it.
- **The table holds observations, not summaries.** Eight runs per x, one row each. The
  mean and the ±1 SD band are derived at plot time in `draw_panel`, so the reduction is
  visible in the plotting code and can be changed without re-extracting.
- **Run counts are reported.** `config.report_runs` prints how many runs sit behind each
  plotted point, so a thin or uneven series is visible instead of hidden inside a band.
  Here every point reads `auto`, because this example reads one finished table and so has
  nothing to declare. A real figure selects per-run files with `config.resolve_runs` and
  declares `runs = N` in its `figure.toml`; then the count is an *expectation*, and falling
  short of it warns at extraction time and is recorded in `extracted_data/extraction_log.txt`.
  See the selection-knob stub in `figures/_template/figure.toml` for the declaration and
  `tests/demo_figure/make_figure.py` (`check_under_selection`) for what a shortfall looks like.

## Next

[tests/demo_figure/README.md](../../tests/demo_figure/README.md) is the full worked
example: subgrids, schematics, colorbars, geometric bands, run selection over per-run
files, and the geometry and refusal checks. Its table maps each panel to the feature it
demonstrates.
