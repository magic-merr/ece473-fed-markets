# Final report sections

One file per section. Only the owner edits a section file. Palmer assembles them into the submitted report on
Monday and edits for one voice; comments on someone else's section go in the Requests table in `docs/TASKS.md`.

| File | Section | Owner |
|---|---|---|
| `1-product.md` | The product | Jay |
| `2-index.md` | The index | Ari |
| `3-data.md` | Data and price rule | Palmer |
| `4-spec.md` | Contract specification | Jay |
| `5-pricing.md` | Pricing | Jay |
| `6-method.md` | Backtest method and metrics | Ari |
| `7-results.md` | Results | Ari |
| `8-limitations.md` | Limitations | Palmer |
| `9-appendix.md` | References, reproduction commands, data files | Palmer |

Rules for the text (from Niusha's feedback and CLAUDE.md rule 6):
- Say what the product is before anything else; define the index once with a formula and a worked example.
- For every backtest: method, then metrics, then what each metric should show, then results.
- Announcement days are shown, never silently excluded.
- Plain sentences, every term defined once, no em dashes, no filler.
- Every number comes from `docs/reports/final/numbers.md`. If a number you need is not there, add a Request for
  Palmer rather than computing it in the text.
- Figures: cite by repo path (e.g. `index/results/fig_hedge_error.png`); Palmer places them.
