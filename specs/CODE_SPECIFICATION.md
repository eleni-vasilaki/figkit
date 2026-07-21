# Figure Factory Code Specification

This document defines how manuscript figures should be built in this project.
It is the starting specification for future figure work.

## Goals

- Produce reproducible, manuscript-ready figures from local assets and copied
  source-format data.
- Keep the active project structure small, readable, and replaceable.
- Make figure generation robust when an updated source bundle is dropped into
  `raw_data/` and the figure is re-extracted.
- Keep schematic design decisions human-controlled when Python is not the best
  drawing tool.

## Directory Structure

Each figure has one active directory:

```text
PhyKAN/
  figkit/                     # reusable framework (see FIGURE_SYSTEM_PLAN.md)
  raw_data/
    copied_source_bundle/     # source-format data, local + gitignored
  figures/
    figure_name/
      README.md
      CAPTION.md
      make_figure.py          # pure plotter: reads the tables below
      extract_data.py         # raw_data/ -> extracted_data (run once)
      figure.toml
      panels/
        README.md
        panel_a/
          source.png
          current.png
      extracted_data/
        panel_b.tsv           # one row per observation, committed
        extraction_log.txt
      outputs/
        figure_name.png
        figure_name.pdf
```

## Common Code

Anything shared by more than one figure or panel is defined once in `figkit/`;
panels specify layout/content only, never re-define style, primitives or physics.

- `figkit/style.py` — single source of truth for palette (`COLORS`,
  `SCHEMATIC`), schematic typography/line-weights (`SCHEMATIC_STYLE`), figure
  width, grid, legend, panel-label style, and `apply_matplotlib_style()`.
- `figkit/config.py`, `layout.py`, `plotting.py`, `schematic.py` — manifest
  loading and run selection, grid geometry, plot helpers, schematic primitives.
- Figure-specific helpers, physics, and maths stay inside that figure.
- Promote a helper to `figkit/` only when a second figure genuinely needs it.
- If a helper is not useful across figures, keep it inside that figure (a
  figure-local module, or that figure's `make_figure.py`).

Design/house-style guidance (Nature-family aesthetics, typography sizes, colour
semantics, vector export) is documented in `figure_principles.md` — consult that,
do not re-derive it from the web.

## Figure Scripts

- Each figure has one active full-figure script named `make_figure.py`.
- The script composes all panels and writes final PNG and PDF outputs.
- The script is a pure plotter: it only *reads* saved data. It must not train,
  simulate, roll out, or run model inference to produce a plotted result. Anything
  that produces data lives in `generate_missing_data.py` (see "Missing or Unsaved
  Data").
- The script should run from the project root and from VS Code without requiring
  manual path edits.
- The script should use shared style and paths from `figkit/` in a way that is
  independent of the current working directory or the folder opened in VS Code.
- The script should fail clearly if required panel images or data folders are
  missing.

## Data Rules

- Raw data live in the repo-root `raw_data/<bundle>/`, in source format, kept local
  and gitignored. One drop-point for every dataset, not a copy per figure.
- Do not compress, summarize, rename, or transform source data unless explicitly
  approved. A raw bundle must be replaceable by dropping in an updated
  source-format bundle with the same filename conventions.
- Each figure's `extract_data.py` reduces its bundle ONCE into that figure's
  committed `extracted_data/*.tsv`: one row per individual observation, never a
  summary. `make_figure.py` reads only those tables and derives the statistics.
- The figure's `README.md` and `CAPTION.md` explain which data feed which panels.
- If copied source bundles include Python scripts, their role must be documented
  where the scripts live: inspection, provenance, training, evaluation, or
  active plotting code.
- The active manuscript figure builder must be clearly identified and kept
  separate from copied reference or inspection scripts.
- Small metadata files are allowed when source-array meaning is otherwise
  implicit in an inspection script. Metadata must be plain text and documented.
- Plotting code should discover available data from filenames or metadata.
- Do not hard-code data-point lists, model-size lists, run lists, or axis limits.
- Axis limits should be estimated from the plotted data.
- Formula constants that define a model's trainable-parameter count are allowed,
  but they must represent model definitions rather than selected data points.

## Missing or Unsaved Data

A `make_figure.py` only ever *reads* saved data. It must not train a model, run a
simulation or rollout, or run model inference to produce a plotted result.

When a figure needs data the source bundle did not ship — results that were never
saved (only the models were), or a simulation/mock standing in for absent data —
that data is produced **once** by a separate script in the figure folder named
`generate_missing_data.py`. This single uniform name is used in every figure that
needs it.

- `generate_missing_data.py` is the only place heavy work lives (model loading,
  forward passes, rollouts, training). It writes its output as saved arrays in the
  same per-`(size, run)` format the raw bundle uses, writing them **into**
  `raw_data/<bundle>/` because it stands in for raw data that belongs there.
  `extract_data.py` then reduces them like any other raw data, and the resulting
  table's header comment records that the values are generated, not measured.
- `extract_data.py` must fail clearly, naming `generate_missing_data.py`, if those
  saved arrays are missing.
- Re-run `generate_missing_data.py` only when its inputs change (new models, or a
  changed selection in `figure.toml`); routine builds just read the saved arrays.
- Statistical reproducibility stays at the plotter. Where the original method
  applied a random draw (e.g. an unseeded validation split), save the deterministic
  expensive part in `generate_missing_data.py` and apply the cheap random reduction
  at draw time, so the plotted number still varies build-to-build by design rather
  than being frozen into the saved file.

## Panel Assets

- Panels that are schematics may be supplied as ready images.
- Ready schematic images live inside the relevant `panels/panel_x/` folder.
- `source.png` is the manually prepared source asset.
- `current.png` is the exact asset used by `make_figure.py`.
- If Python pre-rendering is genuinely needed for a panel, that code must live
  inside that panel folder and be documented in `panels/README.md`.
- Do not recreate or redesign schematics programmatically unless explicitly
  requested.

## Visual Rules

- Use the shared style in `figkit/style.py` by default.
- Local visual overrides are allowed only when required by that figure and should
  stay inside the figure script.
- Standard figure dimensions should be reused across figures where possible.
- Panel labels must be aligned consistently across the complete figure.
- Image panels should be sized and positioned as part of the final figure layout,
  not adjusted by changing source data.
- Quantitative panels should use data-driven limits and consistent styling.

## Documentation

Each active figure directory must contain:

- `README.md`: what the figure shows, how to run it, which raw bundle it extracts
  from, what each file in the folder is for, and where outputs go.
- `CAPTION.md`: the hand-written caption, and per panel what is plotted and how it
  is reduced.
- `panels/README.md`: what panel assets are used and whether any panel-specific
  pre-rendering exists.

Provenance is prose written by a person, in these files and in `audits/`. No part of
it is generated.

Documentation should describe the current active structure only.

## Change Discipline

- Do not touch unrelated directories.
- Do not add new helper scripts without approval.
- Do not send schematic editing work back to the user unless it is genuinely a
  manual design choice or an external asset decision.
- Before changing structure, state what will be changed and where.
- After changing figure code, run the active figure script and confirm the
  PNG/PDF outputs are generated.
- Do not commit caches or OS cruft (`__pycache__/`, `*.pyc`, `.DS_Store`,
  `.mplconfig/`); these are covered by `.gitignore`.

## Completion Check

A figure task is complete only when:

- The active structure is clear.
- Source-format data are present and documented.
- The one active `make_figure.py` runs successfully.
- Final PNG and PDF outputs are generated.
- No undocumented active helper scripts are required.
- Any remaining manual schematic work is explicitly identified.
