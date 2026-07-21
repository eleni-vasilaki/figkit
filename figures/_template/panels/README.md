# Panels

Per-panel render modules and schematic art live here. For each non-trivial panel,
`panels/panel_x/` holds `render_panel_x.py` (exposing `draw_panel_x(ax, ...)`), the
editable source asset (e.g. the `.svg`), and the `current.png` the build places.

Record here: which panels have editable source assets, which rendered asset the
figure uses, how standalone previews are regenerated, and any panel-local
composition knobs needed to reproduce the appearance.
