# demo_figure — figkit's test figure and worked example

This is NOT a manuscript figure. It plots synthetic seeded distributions, and it exists
for two reasons: it regression-tests `figkit` end to end, and it is the fullest worked
example of the framework in one file.

```bash
python tests/demo_figure/make_figure.py
```

Run it in a Python ≥ 3.11 environment with numpy, scipy, and matplotlib
installed — the Requirements in the repository README.

Every check prints `PASS` or `FAIL`, and any `FAIL` exits non-zero. Run it after editing
`figkit`, and look at `outputs/demo_figure.png` as well as the printed lines.

For the smallest possible starting point instead, see
[examples/minimal_figure/](../../examples/minimal_figure/) — one panel, one table, about
forty lines. Come here when you need a feature that example does not cover.

## Which panel demonstrates what

| Panel | figkit feature | Where |
|---|---|---|
| a | run-series selection + arithmetic bands: `config.resolve_runs`, `plotting.mean_band`, `plotting.draw_band` | `draw_panel_a` |
| b | geometric bands on log-normal data, log-y: `plotting.gmean_band` | `draw_panel_b` |
| c | palette roles on plain axes (two overlaid histograms) | `draw_panel_c` |
| d | smoothing a noisy trace: `plotting.exp_average` | `draw_panel_d` |
| e | heatmap with an aligned colorbar in its own subgrid column: `plotting.attach_colorbar`, `layout.subgrid` with a reasoned non-uniform split | `draw_panel_e` |
| f | a uniform `layout.subgrid` split (full trace beside its zoom) | `draw_panel_f` |
| g | every `schematic` primitive (`box`, `curve_in`, `connect`, `node_circle`, `draw_network`, `arrow`, `open_axes_miniplot`) plus `schematic.preview` standalone rendering | `draw_panel_g` |

Panel letters for all seven come from one `layout.place_panel_letters` call, and the
whole grid from one `layout.grid` call over `figure.toml`'s `[layout]`.

## What else it checks

- **Known-answer statistics** (`check_stats`) — the band helpers against hand-computed
  values, so a refactor cannot silently change what a band means.
- **Geometry** (`check_geometry`) — the *rendered* axes are measured and must equal the
  inches `figure.toml` declares: margins, gaps, canvas width, auto-derived height, and
  `layout.cell_size_in` against the real panel. This is what keeps "authored in inches"
  honest.
- **Refusals** (`check_config_rejections`, `check_layout_rejections`) — the
  reason-enforcement contract. Deliberately bad manifests and reason-less exception calls
  must each be rejected with a clear message: an unknown `[layout]` field, a reasoned knob
  without its reason, a fixed height without a reason, non-uniform `col_ratios` without a
  reason, `row_heights_in` combined with `row_ratios`, a non-uniform `subgrid`,
  `adjust_frame` with an empty reason, a `grid` override without a reason, shifted panel
  letters without a reason, and scaled framed art without a reason.
- **Under-selection** (`check_under_selection`) — a declared `runs = N` the data does not
  meet must warn on stdout naming the missing run numbers, record the shortfall in
  `extraction_log.txt`, and still return what exists rather than failing the build. Also
  checks that `write_extraction_log` drains its record, so a second log cannot repeat the
  first one's series. A real figure declares an explicit count (`runs = 10` in its
  `figure.toml`), and a silently short series would weaken a band without changing
  anything visible — this is the check that makes that impossible.
- **Module loading** (`check_modload`) — `figkit.modload.load_module` loads a module by
  path and registers it in `sys.modules`, which figures need when unpickling a model whose
  pickled module name differs from its filename.

When you add a feature to `figkit`, add its demonstration here — a panel if it draws
something, a rejection check if it enforces something.
