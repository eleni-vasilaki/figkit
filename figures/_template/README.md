# Figure &lt;name&gt;

Human-facing narrative for this figure: what it shows, how it is built, and how to
reproduce it. Filled in per figure. This README, `CAPTION.md`, and the figure's audit
under `audits/` are where provenance lives — in prose, written by a person.

## What This Figure Shows

- **Panel a** — one line per panel.

## Current Command

From the repository root, in a Python ≥ 3.11 environment with numpy, scipy,
and matplotlib:

```bash
python figures/figure_<name>/make_figure.py
```

`make_figure.py` is a pure plotter: it reads only the committed `extracted_data/*.tsv`
tables, so a build is fast and a fresh clone reproduces the figure with no raw data.

### Rebuilding the tables from raw data (optional)

The tables in `extracted_data/` are committed, so the plotter needs no raw data. To
rebuild them from the raw bundle in the repo-root `raw_data/<bundle>/` (kept local /
gitignored), run:

```bash
python figures/figure_<name>/extract_data.py
```

The same environment, plus whatever your extractor itself imports (for example
torch, if it opens saved models).

## Folder Layout

```text
figure_<name>/
  make_figure.py       # only active full-figure builder (pure plotter, reads tables)
  extract_data.py      # reduce the raw_data/ bundle -> extracted_data tables (run once)
  figure.toml          # canvas/layout geometry + selection knobs (config only)
  CAPTION.md           # hand-written caption and known caveats
  panels/              # per-panel render modules and schematic art
    README.md
  extracted_data/      # committed TSV tables, one per data-driven panel
    extraction_log.txt #   what extract_data.py selected, and any under-selection
  outputs/             # PNG/PDF written by this figure's code
  README.md            # this file
```

The raw bundle lives outside the figure, in the repo-root `raw_data/<bundle>/`
(kept local / gitignored) — only `extract_data.py` reads it.

## File Roles

- `make_figure.py` — the only active full-figure builder. It reads the committed
  tables and derives every summary from them. It opens no models, runs no simulation,
  and never reads `raw_data/`.
- `extract_data.py` — reduces the raw bundle to the committed `extracted_data/` tables,
  the individual per-run observations. Run once; re-run when the raw bundle changes.
- `generate_missing_data.py` — add this only when the original experiment never saved
  an input the figure needs. It is a temporary stand-in for missing real data: it writes
  the recovered arrays **into** `raw_data/`, precisely because it stands in for raw data
  that belongs there, and `extract_data.py` then reduces them like any other raw data.
  It is run-once and throwaway. All simulation lives here, never in the plotter.
