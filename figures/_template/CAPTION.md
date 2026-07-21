# Figure &lt;name&gt; — Caption

Manuscript figure: "&lt;title as it appears in the manuscript&gt;".

## Draft caption

**(a)** One paragraph per panel, written by hand. Describe every panel completely
from the generation code: which table it reads, the per-run reduction, what the
plotted point shows (mean, median), and what the band shows (±1 SD, geometric std).

## Data plotted

- **Panel a.** `<table>.tsv` — what each row is, how many runs per point, and how
  the plotted point and band are derived from those rows.

## Notes

Known caveats, placeholder data, and anything a reader would otherwise assume
wrongly. Scientific gaps belong in `audits/figure_<name>.md`.

Where the figure's own code derives a caption fact (an architecture, a measured
error), write it to `outputs/panel_metadata.md` from `make_figure.py` and cite that
file here, so the number in the caption is derived rather than retyped.
