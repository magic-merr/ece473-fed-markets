# Ari's log

(Append entries using the template in CLAUDE.md. Newest at the bottom.)

## 2026-11-12 17:45  main
Did:
- Built `index/` (TASKS 5 and 6), using only data already in the repo (`index_m1/raw`, `index_m1/data`): `legs.py`
  applies Palmer's `src/stale.py` rule (decision 002) to the committed candles, `build.py` builds CUT/HIKE for
  H = 90 and 60 in the decision 003 format, `futures.py` runs the futures-vs-static-hedge backtest under the
  Milestone 1 draft contract terms, `figures.py` makes two figures, 11 tests.
- Under the Milestone 1 price rule `build.py` reproduces `index_m1/data/index_daily.csv` exactly (1,943 days).
Results (numbers worth keeping), 44 monthly expiries Feb 2023 to Sep 2026, 1,152 trades, $ per $100 contract:
- Hedge error is exactly 0 when the rate does not change before expiry (meetings where the Fed holds included),
  apart from settlement days without an index value (max $1.31). When the Fed moves: RMSE $23.5 (CUT90),
  $33.7 (CUT60), worst $74; the dealer gains when the move is in the index's direction.
- Round-trip hedge cost: CUT90 $7.56, CUT60 $5.61, HIKE90 $7.26, HIKE60 $6.05. Far leg: 51 to 66% of cost with
  about half the contracts; 1.3 to 2.0 times the near leg's cost per contract.
- Dealer capital about $103 to $105 per contract for the life of the trade ($0.07 to $1.04 at 4% a year).
- Futures price above spot CUT90 by $1.8 (7-day lead), $8.2 (30), $16.3 (90): the roll-down is priced in.
Open issues:
- Decision 002 is still proposed; results use it. Rerun `python futures.py` if it changes.
- TASKS 13 to 16 added for Jay and Palmer.
Next: TASK 7 (return decomposition on the src-rule index), then my report section.
