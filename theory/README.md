# theory/: evidence for the contract spec and the pricing argument

Owner: Jay. Covers TASK 10 (no-arbitrage check and settlement discount) and TASK 13 (expiry rule).
Runs from data already in the repo. Nothing is pulled.

```bash
cd theory && python noarb.py      # writes results/noarb_summary.md
```

Full output is in `results/noarb_summary.md`. The four findings and where they are used:

**1. The ladder is arbitrage-free at executable prices.** Across 11,179 meeting-days from March 2022,
12 (0.11%) admit a trade where a bid at a higher strike sits above an ask at a lower strike, which is what
no-arbitrage forbids, since "upper bound above K" must be weakly decreasing in K. The largest credit is
$0.09. Mid prices look much worse, 25.5% non-monotone, but a mid is not a tradable price when the book is
one-sided, which is common here. Used in `docs/spec.md` section 7. This is the check that says the index
can settle a contract.

**2. CUT90's legs are never in the tail regime after 2023.** The index reads one strike per meeting at
`U_t - 0.25`, which is near the money. The pinned 1c / 99c share is 40.4% on the near leg in March 2022 to
January 2023 and 0.7% from February 2023, zero in 2024, 2025 and 2026. On the 186 pinned days the BOUND
price equals the Milestone 1 mid to four decimals, because `(1+bid)/2` is `(bid+ask)/2` when the ask is
pinned at 1. Used in decision 005.

**3. The settlement discount is not measurable at these spreads.** A discount `D(tau) < 1` predicts an
asymmetry: a near-certain winner trades below $1, a near-certain loser trades near $0. In this data both
sides are off by the same amount at every horizon, 3 cents at a week and 6 cents past 150 days. So the
shortfall is residual uncertainty plus the one-cent tick, not a financing discount, and the implied
annualized carry of 10 to 130% confirms it is not a rate. What we can say is a bound: any true discount is
smaller than the quantity above, which is in turn smaller than the $5 to $8 round-trip hedging cost Ari
measures. The pricing argument in `theory.md` should carry the discount as a named term that we bound
rather than estimate, and should not claim a point estimate. This revises `docs/notes/futures_pricing.md`
item 2, which assumed D could be estimated from this data.

**4. The spec's expiry rule removes every collision.** Under the Milestone 1 rule an FOMC decision falls
inside the five-day settlement window at 5 of the 44 expiries in Ari's backtest sample, and 7 of 58 over
March 2022 to December 2026. Under `docs/spec.md` section 4 it is 0 in both. Five expiry dates move, each
back by one week. Used in `docs/spec.md` section 4 and TASK 18.

## Still open

- TASK 9, `docs/theory.md`: the static-hedge proposition and its proof. The exactness condition is "no
  change in the target range before expiry", not "no meeting before expiry". Ari's backtest establishes
  this empirically (`index/README.md` result 1); the proof belongs here.
- TASK 14: fair value for a contract that spans a possible rate change, where the static hedge does not
  hold.
