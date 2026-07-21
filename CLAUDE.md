# figkit — instructions for AI assistants

A no-install figure framework for research papers. `figkit/` is the library;
`figures/_template/` is the scaffold a new figure copies; `examples/` and
`tests/demo_figure/` are the worked examples. Read the repo README first.

## Hard rules

- **No install step, ever.** No `pip install`, no `pyproject.toml`. Scripts reach
  `figkit` through the `sys.path` header at the top of each file — copy it verbatim
  from `figures/_template/make_figure.py` into any new script.
- **`make_figure.py` is a pure plotter.** It reads only that figure's committed
  `extracted_data/*.tsv` tables. It must never train, simulate, run inference, or
  read raw data. Producing tables is `extract_data.py`'s job, run separately.
- **Tables hold observations, not summaries.** One row per individual run or
  measurement. Means and bands are derived at plot time. Never store a mean, std,
  or other summary in a table.
- **Geometry is declared, not coded.** Canvas and layout live in `figure.toml`,
  authored in inches. Every departure from a default needs a sibling
  `<knob>_reason` in the manifest, or a `reason=` argument at the call site — the
  framework refuses the call otherwise; do not work around the refusal, answer it.
  Never use `bbox_inches="tight"`; the shared width is `figkit.style.FIGURE_WIDTH`.
- **`figure.toml` is config only.** What the data means and where it came from is
  prose written by a person, in the figure's `README.md` and `CAPTION.md`.
- **Real data only in real figures.** Never substitute mock or synthetic data into
  a figure that presents results. If an input is missing, draw the panel empty,
  say so in the caption, and record the gap — a wrong figure is worse than an
  incomplete one.

## Commands

```bash
# self-checking test figure — run after any figkit edit; exits non-zero on failure
python tests/demo_figure/make_figure.py

# the smallest complete figure
python examples/minimal_figure/make_figure.py
```

Environment: Python ≥ 3.11 with numpy, scipy, matplotlib. Nothing else.

## When you add a figkit feature

Add its demonstration to `tests/demo_figure/` in the same change: a panel if it
draws something, a rejection check if it enforces something, a geometry check if
it places something. The demo is the regression suite; a feature it does not
exercise is a feature the next edit can silently break.
