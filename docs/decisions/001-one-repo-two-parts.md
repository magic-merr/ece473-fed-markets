# 001: One repo holds both codebases; Milestone 1 is a frozen baseline
Status: accepted
Date / who: 2026-11-12, Palmer

Decision: The Milestone 1 index code, data and figures (previously only in a zip on Palmer's Mac) now live
in `index_m1/`. They are frozen: they rebuild the Milestone 1 report numbers exactly
(`cd index_m1 && python build_index.py`, verified 2026-11-12). New index work goes in a new `index/`
folder that reads the `src/` data layer. The Milestone 1 report is in `docs/reports/milestone1/`.

Why: The repo was only the cross-venue comparison project, so teammates could not see or run the index,
the tracking backtest or the futures draft. Keeping Milestone 1 frozen lets the final report show how
results change when the cleaning rule changes.

Alternatives considered: Merge `index_m1` scripts into `src/` now. Rejected: they use a different
cleaning rule and data layout (see 002), and changing them would break reproducibility of Milestone 1.

Files affected: `index_m1/` (new), `docs/reports/milestone1/` (new), `.gitignore`
(`index_m1/data/kalshi_daily.csv` excluded, the identical 1 MB parquet is committed), `requirements.txt`
(+pyarrow), `index_m1/build_index.py` and `make_figures.py` (read the parquet when the CSV is absent; no
other change).
