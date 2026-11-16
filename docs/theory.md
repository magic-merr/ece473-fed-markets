# Pricing the CUT90 future

Owner: Jay. Covers TASKS 9, 14 and 20. Configuration: decision 007. Contract terms: `docs/spec.md`.

Every empirical number below comes from `docs/reports/final/numbers.md` (CLAUDE.md sprint rule 7), which
cites its source file and commit. Filled at J5.

## 1. Notation

Fixed once, used throughout.

| Symbol | Meaning |
|---|---|
| `U_t` | Upper bound of the target range set by the most recent decision announced on or before day `t`, in percent. The close is after the 2:00pm announcement, so a decision day reads against its own new range |
| `Y_m(K, t)` | Price on day `t` of meeting `m`'s contract "the upper bound after `m` is above `K`" |
| `C_m(t)` | `1 - Y_m(U_t - 0.25, t)`, the cut leg: the upper bound after `m` is below today's |
| `H_m(t)` | `Y_m(U_t, t)`, the hike leg |
| `T` | `t + 90` days, the constant-maturity point |
| `a, b` | The meetings bracketing `T`: `a` the last on or before it, `b` the first after |
| `w(t)` | `(date of b - T) / (date of b - date of a)`, the weight on the nearer meeting |
| `I(t)` | `CUT90(t) = w(t) C_a(t) + (1 - w(t)) C_b(t)`, in index points |
| `E` | Expiry, by `docs/spec.md` section 4 |
| `W` | The settlement window, the five calendar days ending on `E` |
| `S` | `(1/5) sum over d in W of I(d)`, the settlement value |

HIKE90 is identical with `H_m` in place of `C_m`. Everything below holds for both.

A note on prices. `Y_m(K, t)` is a traded price, not a probability. Section 5 says exactly where that
distinction matters, and it is less often than the Milestone 1 report assumed.

## 2. Fair value from a static hedge

**Proposition 1.** Fix a trade date `t` and an expiry `E`. Suppose the target range does not change between
`t` and `E`, so `U_d = U_t` for every `d` in `[t, E]`. Then

    F0(t) = (1/5) sum over d in W of [ w(d) C_a(d)(t) + (1 - w(d)) C_b(d)(t) ]

is the unique price at which the future admits no arbitrage, and the following portfolio replicates it
exactly: for each settlement day `d`, buy `20 w(d)` contracts of meeting `a(d)` and `20 (1 - w(d))` contracts
of meeting `b(d)`, all struck at `U_t - 0.25`, and sell day `d`'s tranche at the close of day `d`.

**Proof.** FOMC meeting dates are published years ahead, so for each `d` in `W` the constant-maturity point
`T(d) = d + 90`, the bracketing meetings `a(d)` and `b(d)`, and the weight `w(d)` are all deterministic and
known on day `t`. By hypothesis `U_d = U_t`, so the strike `K = U_t - 0.25` is also known on day `t`. The
settlement value is therefore

    S = (1/5) sum over d in W of [ w(d) C_a(d)(d) + (1 - w(d)) C_b(d)(d) ]

a combination of traded contract prices whose weights and strikes are fixed at `t`. The portfolio above holds
exactly those positions and liquidates tranche `d` at day `d`'s close, receiving `20 w(d) C_a(d)(d) +
20 (1 - w(d)) C_b(d)(d)`, which is `100` times day `d`'s contribution to `S`. Summing over the five days, the
portfolio pays `100` times that mean, which is the contract's payout before `S` is rounded to the nearest
0.25. Rounding leaves a residual bounded by half a tick of the index, which is $0.125 a contract. The
portfolio is bought once at `t` and needs no
rebalancing, so it is self-financing, and the contract is fully collateralized, so neither side defaults. A
price other than the portfolio's cost at `t` would therefore permit a riskless profit. ∎

The portfolio usually involves two meetings, and three when the window straddles a switch of the bracketing
pair.

**Corollary 1.1. The condition is no rate change, not no meeting.** Proposition 1 assumes `U_d = U_t`, not
that no FOMC meeting occurs. A meeting at which the Fed holds leaves `U` unchanged, so the strike is still
known at `t` and the hedge is still exact. This is the sharper form of the condition in
`docs/notes/futures_pricing.md`, which said "no meeting before expiry".

Ari's backtest confirms it. Trades with a meeting that held have the same near-zero hedge error as trades with
no meeting at all: RMSE $0.20 against $0.22 per
$100 contract. The residual comes from settlement days with no valid index value and from rounding `S` to
0.25: with a full five-day window and no rate change the error is zero before rounding and at most $0.12
after it (`numbers.md`: `max_err_full_window_no_move`).

**Corollary 1.2. The future prices the roll-down that the spot index cannot deliver.** Between announcements
`U` is fixed, and `T = t + 90` advances one day per day, so

    dw/dt = -1 / (date of b - date of a)

The weight moves deterministically from the nearer meeting to the later one. Differentiating `I`:

    dI/dt = [ (C_b - C_a) / (date of b - date of a) ] + w dC_a/dt + (1 - w) dC_b/dt

The first term is the roll-down. It is mechanical: it depends only on the slope of the cut curve across the
two bracketing meetings and the gap between them, not on any news. The second and third terms are belief
change. A holder of the two meeting contracts earns only the belief terms, because their holdings do not
re-weight. That gap is what the Milestone 1 backtest measured: the roll-down averaged
26.0 basis points a day and accumulated to
399.3 index points, against an index that moved
+9.4 (`results/decomposition.md`).

The future does not have this problem, and Proposition 1 says why. `F0` is the cost today of the contracts the
index will hold at expiry, at the weights it will hold them. The roll-down is already in that price. This is
the product's reason to exist, and it is visible as a positive basis that grows with the lead: `F0` minus the
spot index averages $1.61, $8.20 and
$17.28 at 7, 30 and 90 days (`index/results/futures_backtest.md`).

## 3. What a rate change does

When the Fed changes the range at a meeting before `E`, the hypothesis of Proposition 1 fails, and it fails in
one specific way: the hedge holds contracts struck at `U_t - 0.25`, while the index re-anchors to
`U_E - 0.25`. The two are no longer the same claim.

**Proposition 2 (sign and size).** Suppose the Fed cuts one notch before expiry, so `U_E = U_t - 0.25`. Write
`P_one(m)` for the price of "at least one cut by meeting `m`" at the old strike and `P_two(m)` for "at least
two cuts by `m`". After the cut, the hedge leg at the old strike is worth about 1, while the index now asks
for a further cut and is worth about `P_two(m) / P_one(m)`. The dealer's gain per unit held in meeting `m` is
therefore about

    1 - P_two(m) / P_one(m)

which is positive. A hike instead leaves the old strike two notches away and nearly worthless, so the dealer
loses only a little. The dealer is long a digital on "the Fed moves in the index's direction before expiry",
and `F0` does not charge for it.

The backtest shows exactly this asymmetry. The CUT90 dealer's mean gain is
$25.27 when the Fed moves in the index's direction,
-$2.51 when it moves against, and about zero with no change
(`results/reset_adjustment.md`).

### 3.1 An ex-ante correction

Everything needed is observable on the trade date. Let `k` be the last meeting before expiry and define

- `p_dir` = the price of at least one step in the index's direction by meeting `k`. For CUT this is
  `1 - Y_k(U_t - 0.25, t)`; for HIKE it is `Y_k(U_t, t)`.
- `G` = the sum over hedge tranches of `q (1 - P_two(m) / P_one(m))`, with `q` the tranche's size: what the
  dealer gains if the move happens.

Then

    F_adj = F0 - p_dir G

**This is an upper bound on the correction, not an estimate of it.** It ignores moves against the index, which
cost the dealer a little, and it assumes the old legs go to exactly 1. Both push `G` up.

**How it performs** (`results/reset_adjustment.md`):

- `p_dir` is well calibrated for both indices. For CUT90 the mean is 0.15 against
  a realized share of 0.13.
- **For CUT, `G` is about right, and the bound does not bind.** Predicted $22.71 against realized
  $26.40, so in this sample the correction comes in a little below the gain it is built to cap rather than
  above it. The correction tracks the dealer's mean gain closely to 60 days and
  overshoots at 90. Applying it cuts the CUT90 buyer's mean loss from $8.63 to
  $4.92.
- **For HIKE, `G` is too large**, $37.24 predicted against
  $20.01 realized, and the cross-trade correlation is near zero. The reason is
  that `P_two / P_one` is read off the entry-day ladder, which assumes the ratio is stable. It is not, and it
  misses in both directions: the aggregate overstatement comes from the May 2023 and September 2026 hikes,
  where the market priced a further hike far more richly after the move than the entry-day ratio implied, so
  the re-anchored index was worth more than predicted and the dealer's gain was smaller. At the March and
  July 2023 hikes the formula understated the gain instead. The errors are large and of both signs, which is
  why the correlation is near zero rather than merely weak. Report `F_adj` as fair value for CUT and as an
  upper bound for HIKE.

What remains after the correction is belief change, not construction. In this sample cuts kept arriving later
than priced, which is a fact about 2023 to 2026 and not a property of the contract.

## 4. Continuity

`I` is continuous in `t` on any interval containing no rate change, because `w` moves continuously and the two
contract prices move continuously. It stays continuous at a bracket roll too, where `w` jumps from 0 to 1 as
the ninety-day point passes a meeting: on either side of that jump all the weight sits on the same meeting, so
`I` does not move. At a meeting that changes the range, `I` jumps, because the strike changes by one notch.
There is no jump at a meeting that holds.

This is the formal content of decision 004. The jumps are a property of a constant-maturity index measured
against a moving reference rate, they are where the hedge fails (section 3), and they are where the product's
residual risk lives. Removing them from the sample would remove the only days on which the dealer's digital
pays. They stay in, and they are shown as their own row.

The same fact drives the expiry rule in `docs/spec.md` section 4. Index values on the two sides of a rate
change are measured against different reference rates, so averaging them is not averaging one quantity. That is
why no FOMC decision may fall inside the settlement window, and why the settlement-window extension stops at a
decision date rather than running back through one.

## 5. The settlement discount, and why it does not enter

Prediction-market prices are not probabilities. A contract paying $1 at resolution trades at roughly
`probability x D(tau)`, where `D(tau) < 1` is the time value of the collateral locked until resolution
(Gebele and Matthes 2026). The Milestone 1 report treated this as a quantity to estimate and correct for.

**It does not enter Proposition 1.** The proof never uses the interpretation of `Y_m(K, t)` as a probability.
It uses only that the settlement value is a fixed-weight combination of contracts that trade, and that the
hedge holds those same contracts and liquidates them on the same days the index reads them. If every price
carries a factor `D`, it carries it identically on both sides and cancels. The static hedge is exact in prices,
whatever those prices mean. The discount matters only when reading the index as a probability of a cut, which
the product does not require anyone to do.

**It is also not identifiable in this data** (TASK 10, `theory/README.md`). A discount predicts an asymmetry:
a near-certain winner trades below $1 and a near-certain loser near $0. Both sides are off by the same amount
at every horizon, about 3 cents at a week and
6 cents past 150 days, and the implied annualized carry runs to triple digits.
What is being measured is residual uncertainty plus the one-cent tick, not a financing rate.

So the discount is carried as a bounded term. Any true `D` shifts `F0` by less than the figures above, which
are themselves far below the round-trip hedge cost of $7.76
(`index/results/futures_backtest.md`). Decision 007 records this as bounded, not estimated.

## 6. The ladder the index reads

The index reads one strike per meeting, at `U_t - 0.25`. Proposition 1 needs those prices to be internally
consistent, since "the upper bound is above `K`" must be weakly decreasing in `K`. Across
11,179 meeting-days from March 2022, 12 (0.11%)
admit an executable violation, a bid at a higher strike above an ask at a lower strike, with a largest credit
of $0.09 (`theory/README.md`). Mid prices look far worse, at
25.5%, but a mid is not a tradable price when the book is one-sided, which
is common in this ladder. The ladder is sound enough to settle a contract on.

## 7. What this does not cover

- **Depth.** `F0` and the hedge cost are computed at the standing book with no depth model. A dealer working
  size would pay more, and the far leg is where that bites.
- **The HIKE correction.** `p_dir G` overstates it, as section 3.1 explains. A regime-aware estimate of
  `P_two / P_one` would be the next step and is not in this report.
- **Overlapping trades.** Entries at leads above about 30 days overlap across expiries, so the trade-level
  statistics are not independent observations.
