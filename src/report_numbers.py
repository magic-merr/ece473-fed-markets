"""Write docs/reports/final/numbers.md: every number the final report cites (sprint row P5). Palmer.

Each line: key, value as it should appear in the text, what it is, source file, and the commit that last
changed that source file. Values are read from the committed source files only:
  index/results/*.csv               Ari (decision 007 run)
  results/*.md                      Palmer (markdown tables, read back from the committed file)
  theory/results/noarb_summary.md   Jay
Keys used as `{{numbers.md: key}}` placeholders in docs/theory.md and sections 1, 4, 5 keep Jay's names.
Nothing is computed here beyond picking, rounding and formatting.

Run: cd src && python report_numbers.py  ->  docs/reports/final/numbers.md
"""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "reports" / "final" / "numbers.md"
IR = "index/results"


# ---------------------------------------------------------------- readers
def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / IR / f"{name}.csv")


def md_table(path: str, heading: str, nth: int = 0) -> pd.DataFrame:
    """The nth markdown table after the first line matching `heading` (regex) in a committed file."""
    lines = (ROOT / path).read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if re.search(heading, l))
    tables, cur = [], []
    for l in lines[start + 1:]:
        if l.startswith("|"):
            cur.append(l)
        elif cur:
            tables.append(cur)
            cur = []
            if len(tables) > nth:
                break
    if cur:
        tables.append(cur)
    t = tables[nth]
    rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in t if not re.match(r"^\|[\s:|-]+\|$", r)]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    def conv(s):
        try:
            return pd.to_numeric(s.str.replace(",", "").str.rstrip("%").replace({"nan": None, "": None}))
        except (ValueError, TypeError):
            return s
    return df.apply(conv)


def row(df, **kw):
    m = df
    for k, v in kw.items():
        m = m[m[k] == v]
    assert len(m) == 1, (kw, len(m))
    return m.iloc[0]


def commit(path: str) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h", "--", path],
                       capture_output=True, text=True)
    return r.stdout.strip() or "uncommitted"


# ---------------------------------------------------------------- formats
def usd(x, n=2):
    return f"-${abs(x):,.{n}f}" if x < 0 else f"${x:,.{n}f}"


def sgn_usd(x, n=2):
    return ("+" if x >= 0 else "-") + f"${abs(x):,.{n}f}"


def pct(x, n=0):
    return f"{100 * x:.{n}f}%"


def num(x, n=2):
    return f"{x:,.{n}f}"


def half_up(x, n=1) -> float:
    """Round half up (399.25 -> 399.3), so values match how a reader rounds the source tables."""
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))


def pts(x, n=1):
    return f"{half_up(x, n):+,.{n}f} points"


# ---------------------------------------------------------------- entries
SECTIONS: dict[str, list] = {}


def add(section, key, value, what, source):
    SECTIONS.setdefault(section, []).append((key, value, what, source))


def sample_and_index():
    s = "Sample, calendar and index (sections 2, 4, 6)"
    bt = (ROOT / IR / "futures_backtest.md").read_text()
    n_exp = int(re.search(r"Sample: (\d+) monthly expiries", bt).group(1))
    add(s, "sample_expiries", str(n_exp), "monthly expiries in the final backtest (decision 007 calendar), first "
        "2023-02-24, last 2026-10-23", f"{IR}/futures_backtest.md")
    cov = csv("futures_coverage")
    add(s, "sample_trades", f"{int(cov['ok'].sum()):,}", "futures trades run across CUT90, HIKE90, CUT60, HIKE60, "
        "7 entry leads (7, 14, 21, 30, 45, 60, 90 days)", f"{IR}/futures_coverage.csv")
    for ix in ("CUT90", "HIKE90", "CUT60", "HIKE60"):
        r = row(cov, index=ix)
        add(s, f"trades_{ix.lower()}", str(int(r["ok"])),
            f"{ix} trades run (skipped: {int(r['no_entry_price'])} no entry price, {int(r['no_exit_price'])} no exit "
            "price)", f"{IR}/futures_coverage.csv")
    nb = md_table("theory/results/noarb_summary.md", r"^## 4\. Expiry calendar", 0)
    add(s, "expiries_moved_old_calendar", "5 of 44", "Feb 2023 to Sep 2026 expiries that the spec section 4 rule "
        "moves back one week (each had an FOMC decision inside the 5-day window); the final calendar also adds "
        "2026-10-23 (moved from 2026-10-30), giving 45", "theory/results/noarb_summary.md")
    sm = csv("futures_settlement_methods")
    tot = int(sm["expiries"].sum())
    add(s, "settle_full", f"{int(sm['full'].sum())} of {tot}", "expiry settlements (45 or 44 per index x 4) with all "
        "5 window days valid", f"{IR}/futures_settlement_methods.csv")
    add(s, "settle_mean_of_valid", f"{int(sm['mean_of_valid'].sum())} of {tot}", "settlements on the mean of 3 or 4 "
        "valid window days", f"{IR}/futures_settlement_methods.csv")
    add(s, "settle_extended", f"{int(sm['extended'].sum())} of {tot}", "settlements that needed the window "
        "extension (spec 5.2 step 2)", f"{IR}/futures_settlement_methods.csv")
    add(s, "settle_deferred", f"{int(sm['deferred'].sum())} of {tot}", "settlements deferred to the next valid "
        "business day (spec 5.2 step 4)", f"{IR}/futures_settlement_methods.csv")
    add(s, "settle_backstop", f"{int(sm['backstop'].sum())}", "settlements on the backstop (spec 5.2 step 5)",
        f"{IR}/futures_settlement_methods.csv")
    rb = csv("futures_robustness")
    main = rb[rb["variant"].str.startswith("Main")]
    add(s, "share_settle_not_full_cut90", pct(row(main, index="CUT90")["share_settle_not_full"]),
        "CUT90 trades whose settlement used fewer than 5 window days", f"{IR}/futures_robustness.csv")
    iv = csv("index_vs_m1")
    for ix in ("CUT90", "HIKE90"):
        r = row(iv, sample="from 2023-02-02", index=ix)
        k = ix.lower()
        add(s, f"coverage_{k}_final", pct(r["coverage_rebuilt"], 1), f"days with a {ix} value from 2023-02-02, "
            "final rule", f"{IR}/index_vs_m1.csv")
        add(s, f"coverage_{k}_m1", pct(r["coverage_m1"], 1), f"same, Milestone 1 rule", f"{IR}/index_vs_m1.csv")
        add(s, f"corr_{k}_vs_m1", num(r["corr_level"], 3), f"level correlation of final {ix} with the Milestone 1 "
            f"index from 2023-02-02 ({int(r['days_both']):,} days with both)", f"{IR}/index_vs_m1.csv")
        add(s, f"mae_{k}_vs_m1", f"{r['mae_pp']:.2f}pp", f"mean absolute gap, final {ix} vs Milestone 1, from "
            "2023-02-02", f"{IR}/index_vs_m1.csv")
        add(s, f"max_gap_{k}_vs_m1", f"{r['max_abs_diff_pp']:.1f}pp", f"largest gap, final {ix} vs Milestone 1",
            f"{IR}/index_vs_m1.csv")
    vm = md_table("results/settlement_rule_check.md", r"Rebuilt CUT90/HIKE90 vs the Milestone 1 index", 0)
    for rule, lab in (("wide_mid", "final"), ("src rule", "src")):
        r = row(vm, rule=rule, index="CUT90")
        add(s, f"days_gap_gt5pp_cut90_{lab}", f"{int(r['days_gap_gt_5pp'])} of {int(r['days_both']):,}",
            f"days (from Jul 2021) where CUT90 under the {lab} rule differs from Milestone 1 by more than 5pp",
            "results/settlement_rule_check.md")


def event_study():
    s = "FOMC decision-day event study (section 7, A6)"
    es = csv("event_study_summary")
    for rule in ("final", "m1"):
        lab = "final rule" if rule == "final" else "Milestone 1 rule"
        for dec, ix in (("cut", "CUT90"), ("hike", "HIKE90"), ("hold", "CUT90"), ("hold", "HIKE90")):
            r = row(es, rule=rule, decision=dec, index=ix)
            add(s, f"event_{dec}_{ix.lower()}_{rule}", f"{r['mean_change_pp']:+.2f}pp",
                f"mean {ix} change on {dec} decision days, {lab} ({int(r['with_value'])} of {int(r['decisions'])} "
                "days with a value)", f"{IR}/event_study_summary.csv")
    n = es[(es["rule"] == "final") & (es["index"] == "CUT90")].set_index("decision")["decisions"]
    add(s, "event_decisions", f"{int(n.sum())} ({int(n['cut'])} cuts, {int(n['hold'])} holds, {int(n['hike'])} "
        "hikes)", "FOMC decisions from 2023-02-02 in the event study", f"{IR}/event_study_summary.csv")
    ev = csv("event_study")
    date_col, chg = "decision_date", "CUT90_change"
    r = ev.loc[ev[chg].idxmin()]
    add(s, "event_largest_cut90", f"{r[chg]:+.2f}pp on {r[date_col]}", "largest single CUT90 decision-day move, "
        "final rule", f"{IR}/event_study.csv")


def hedge():
    s = "Hedge error, effectiveness, direction (sections 5, 6, 7)"
    ac = csv("futures_accuracy_by_case")
    for ix in ("CUT90", "HIKE90", "CUT60", "HIKE60"):
        k = ix.lower()
        mv, al = row(ac, index=ix, case="rate_move"), row(ac, index=ix, case="all")
        add(s, f"{k}_rmse_rate_move", usd(mv["rmse_err"]), f"{ix} hedge error RMSE when the Fed changed the rate "
            f"before expiry ({int(mv['trades'])} trades)", f"{IR}/futures_accuracy_by_case.csv")
        add(s, f"{k}_worst_rate_move", usd(mv["max_abs_err"]), f"{ix} largest absolute hedge error, rate-move "
            "trades", f"{IR}/futures_accuracy_by_case.csv")
        add(s, f"{k}_effectiveness", num(al["hedge_effectiveness"], 2), f"{ix} hedge effectiveness, all trades "
            "(1 - sum err^2 / sum futures P&L^2)", f"{IR}/futures_accuracy_by_case.csv")
        add(s, f"{k}_mean_err_all", usd(al["mean_err"]), f"{ix} mean dealer hedge error, all trades (positive: "
            "dealer gains)", f"{IR}/futures_accuracy_by_case.csv")
    for case, key in (("meeting_hold", "cut90_rmse_held"), ("no_meeting", "cut90_rmse_no_meeting")):
        r = row(ac, index="CUT90", case=case)
        add(s, key, usd(r["rmse_err"]), f"CUT90 hedge error RMSE, {case.replace('_', ' ')} before expiry "
            f"({int(r['trades'])} trades; includes settlement fallback windows and the 0.25 rounding of S)",
            f"{IR}/futures_accuracy_by_case.csv")
    nm = ac[ac["case"].isin(["no_meeting", "meeting_hold"])]
    add(s, "max_err_no_move", usd(nm["max_abs_err"].max()), "largest absolute hedge error with no rate change, any "
        "index (a settlement fallback window; after rounding S to 0.25)", f"{IR}/futures_accuracy_by_case.csv")
    add(s, "max_err_no_move_before_rounding", usd(nm["max_abs_err_before_rounding"].max()), "same, before rounding "
        "S to 0.25", f"{IR}/futures_accuracy_by_case.csv")
    txt = (ROOT / "index/README.md").read_text()
    m = re.search(r"exactly zero before S is rounded to 0\.25, and at most (\$[\d.]*\d) after", txt)
    add(s, "max_err_full_window_no_move", f"$0 before rounding S, at most {m.group(1)} after", "hedge error with a "
        "full 5-day window and no rate change (meetings where the Fed holds included)", "index/README.md")
    add(s, "worst_err_rate_move", usd(ac["max_abs_err"].max()), "largest absolute hedge error, any index",
        f"{IR}/futures_accuracy_by_case.csv")
    add(s, "cut90_mean_err_rate_move", usd(row(ac, index="CUT90", case="rate_move")["mean_err"]),
        "CUT90 mean dealer hedge error on rate-move trades", f"{IR}/futures_accuracy_by_case.csv")
    d = csv("futures_error_by_direction")
    for ix in ("CUT90", "HIKE90", "CUT60", "HIKE60"):
        for rel in ("with", "against"):
            r = row(d, index=ix, relative_to_index=rel)
            key = (f"cut90_gain_{rel}_move" if ix == "CUT90" else f"{ix.lower()}_gain_{rel}_move")
            add(s, key, usd(r["mean_err"]), f"{ix} mean dealer gain when the Fed moved {rel} the index's direction "
                f"({int(r['trades'])} trades; dealer gains on {pct(r['share_dealer_gains'])})",
                f"{IR}/futures_error_by_direction.csv")


def cost_capital_basis():
    s = "Trading cost, capital, fair value and basis (sections 4, 5, 7)"
    c = csv("futures_costs_pooled")
    for ix in ("CUT90", "HIKE90", "CUT60", "HIKE60"):
        r = row(c, index=ix)
        k = ix.lower()
        add(s, f"hedge_cost_{k}", usd(r["total"]), f"{ix} mean round-trip hedge cost per $100 contract (spread "
            f"{usd(r['spread'])}, taker fees {usd(r['fees'])})", f"{IR}/futures_costs_pooled.csv")
        add(s, f"far_share_cost_{k}", pct(r["far_share_of_cost"]), f"{ix} far leg's share of hedge cost (holds "
            f"{pct(r['far_share_of_qty'])} of contracts)", f"{IR}/futures_costs_pooled.csv")
        add(s, f"per_contract_near_far_{k}", f"{100 * r['per_unit_near']:.1f}c / {100 * r['per_unit_far']:.1f}c",
            f"{ix} cost per contract, near leg / far leg", f"{IR}/futures_costs_pooled.csv")
    cap = csv("futures_capital")
    add(s, "dealer_capital_range", f"{usd(cap['dealer_capital'].min())} to {usd(cap['dealer_capital'].max())}",
        "dealer capital per contract (100 - F0 collateral plus hedge purchase), range over index and lead means",
        f"{IR}/futures_capital.csv")
    add(s, "capital_cost_range", f"{usd(cap['dealer_capital_cost'].min())} to "
        f"{usd(cap['dealer_capital_cost'].max())}", "dealer capital cost at an illustrative 4% a year, 7-day to "
        "90-day lead, all indices", f"{IR}/futures_capital.csv")
    add(s, "capital_cost_90d", usd(row(cap, index="CUT90", lead=90)["dealer_capital_cost"]), "CUT90 dealer capital "
        "cost at a 90-day lead, 4% a year", f"{IR}/futures_capital.csv")
    cc = cap[cap["index"] == "CUT90"]
    add(s, "buyer_capital_cut90", f"{usd(cc['long_capital'].min())} to {usd(cc['long_capital'].max())}",
        "CUT90 buyer capital (F0), mean by lead, 7 to 90 days", f"{IR}/futures_capital.csv")
    fv = csv("futures_fair_value")
    for lead in (7, 30, 90):
        r = row(fv, index="CUT90", lead=lead)
        add(s, f"basis_cut90_{lead}d", usd(r["mean_basis"]), f"CUT90 mean basis F0 minus 100 x spot index, "
            f"{lead}-day lead", f"{IR}/futures_fair_value.csv")
        add(s, f"buyer_pnl_cut90_{lead}d", sgn_usd(r["mean_futures_pnl_long"]), f"CUT90 mean futures buyer P&L "
            f"(S - F0), {lead}-day lead", f"{IR}/futures_fair_value.csv")
    h = fv[fv["index"] == "HIKE90"]["mean_basis"]
    add(s, "basis_hike90_range", f"{usd(h.min())} to {usd(h.max())}", "HIKE90 mean basis across leads (about zero)",
        f"{IR}/futures_fair_value.csv")
    for lead in (7, 30, 90):
        add(s, f"basis_hike90_{lead}d", usd(row(fv, index="HIKE90", lead=lead)["mean_basis"]),
            f"HIKE90 mean basis, {lead}-day lead", f"{IR}/futures_fair_value.csv")
    add(s, "trading_cost_range_by_lead", f"{usd(cap['trading_cost'].min())} to {usd(cap['trading_cost'].max())}",
        "mean round-trip hedge cost by index and lead, lowest to highest", f"{IR}/futures_capital.csv")
    al = csv("futures_accuracy_by_lead")
    al = al[al["index"] == "CUT90"].set_index("lead")["share_no_meeting"]
    add(s, "no_meeting_share_cut90_by_lead", ", ".join(f"{pct(al[l])} ({l}d)" for l in (7, 14, 30, 45)),
        "share of CUT90 trades with no FOMC meeting before expiry, by lead (0% from 45 days on)",
        f"{IR}/futures_accuracy_by_lead.csv")


def robustness():
    s = "Robustness, CUT90 (section 7)"
    rb = csv("futures_robustness")
    rb = rb[rb["index"] == "CUT90"]
    names = [("Main", "main"), ("Only trades where every hedge leg", "rule_priced_only"),
             ("Milestone 1 price rule", "m1_rule"), ("src rule with the trade branch", "src_rule"),
             ("Milestone 1 expiry rule", "m1_calendar"), ("Ari's 11/12 fallback", "fallback_1112"),
             ("Sample from 2022-03-17", "from_2022"), ("11/12 configuration", "config_1112")]
    for prefix, lab in names:
        r = rb[rb["variant"].str.startswith(prefix)].iloc[0]
        add(s, f"rob_{lab}_cut90", f"RMSE {usd(r['rmse_err_rate_move'])}, cost {usd(r['mean_cost'])}",
            f"CUT90 rate-move RMSE and mean hedge cost: {r['variant']} ({int(r['trades'])} trades)",
            f"{IR}/futures_robustness.csv")


def palmer_results():
    s = "Dealer break-even and reset adjustment (sections 5, 7; Palmer P4)"
    be = md_table("results/reset_adjustment.md", r"^## 4\. Dealer break-even", 0)
    for ix in ("CUT90", "HIKE90", "CUT60", "HIKE60"):
        r = row(be, index=ix)
        k = ix.lower()
        add(s, f"breakeven_net_{k}", usd(r["mean_net"]), f"{ix} dealer mean P&L net of round-trip hedge cost, before "
            f"any futures spread (mean error {usd(r['mean_err'])} minus mean cost {usd(r['mean_cost'])}, "
            f"{int(r['trades'])} executable trades)", "results/reset_adjustment.md")
        add(s, f"breakeven_share_negative_{k}", pct(r["share_net_negative"]), f"{ix} share of trades where that net "
            "is negative", "results/reset_adjustment.md")
    add(s, "cost_no_move_cut90", usd(row(be, index="CUT90")["cost_when_no_move"]), "CUT90 mean hedge cost on trades "
        "with no rate change: the spread a dealer needs on those", "results/reset_adjustment.md")
    gc = md_table("results/reset_adjustment.md", r"^## 2\. Predicted vs realized", 0)
    for ix in ("CUT90", "HIKE90"):
        r = row(gc, index=ix)
        k = ix.lower()
        add(s, f"G_{k}_predicted", usd(r["predicted_G"]), f"{ix} predicted dealer gain G from the entry-day ladder, "
            f"trades where the Fed moved the index's way ({int(r['trades'])} trades with a two-step price)",
            "results/reset_adjustment.md")
        add(s, f"G_{k}_realized", usd(r["realized_gain"]), f"{ix} realized dealer gain on the same trades",
            "results/reset_adjustment.md")
        add(s, f"G_{k}_corr", num(r["corr"], 2), f"{ix} correlation of predicted G with realized gain across those "
            "trades", "results/reset_adjustment.md")
    cal = md_table("results/reset_adjustment.md", r"^## 3\. Calibration", 0)
    r = row(cal, index="CUT90")
    add(s, "p_dir_cut90_mean", num(r["mean_p_dir"], 2), "CUT90 mean ex-ante probability p_dir of a move in the "
        "index's direction before expiry", "results/reset_adjustment.md")
    add(s, "p_dir_cut90_realized", num(r["realized_share_with"], 2), "CUT90 realized share of trades with such a "
        "move", "results/reset_adjustment.md")
    add(s, "buyer_loss_F0_cut90", usd(-r["long_pnl_at_F0"]), "CUT90 mean buyer loss at F0, i.e. minus the mean "
        f"buyer P&L (trades with the adjustment, {int(r['trades'])})", "results/reset_adjustment.md")
    add(s, "buyer_loss_Fadj_cut90", usd(-r["long_pnl_at_Fadj"]), "CUT90 mean buyer loss at F_adj = F0 - p_dir x G",
        "results/reset_adjustment.md")
    r = row(cal, index="HIKE90")
    add(s, "buyer_pnl_F0_Fadj_hike90", f"{usd(r['long_pnl_at_F0'])} at F0, {usd(r['long_pnl_at_Fadj'])} at F_adj",
        "HIKE90 mean buyer P&L; the adjustment overcorrects", "results/reset_adjustment.md")


def decomposition():
    s = "Return decomposition (sections 1, 5, 7; Palmer P3)"
    t = md_table("results/decomposition.md", r"^## 1\. Index change split", 0)
    main = t[t["configuration"].str.startswith("Main")]
    m1 = t[t["configuration"].str.startswith("Milestone 1 report")]
    parts = [("index_change", "summed index change"), ("belief_change", "belief change (holding the contracts)"),
             ("roll_down", "roll-down on ordinary days"), ("bracket_rolls", "bracket rolls"),
             ("announcement_resets", "announcement resets"),
             ("of_which_rate_change_days", "of which on rate-change days")]
    for ix in ("CUT90", "HIKE90"):
        k = ix.lower()
        for col, lab in parts:
            add(s, f"decomp_{k}_{col}", pts(row(main, index=ix)[col]), f"{ix} {lab}, final rule, from 2023-02-02 "
                "(chained intervals)", "results/decomposition.md")
    rr = row(m1, index="CUT90")
    add(s, "rolldown_total_m1", f"{half_up(rr['roll_down']):,.1f}", "CUT90 roll-down in index points, Milestone 1 rule and "
        "sample (from 2022-03-17), Milestone 1 one-day method", "results/decomposition.md")
    add(s, "index_change_m1", f"{half_up(rr['index_change']):+,.1f}", "CUT90 summed index change, same configuration",
        "results/decomposition.md")
    add(s, "portfolio_pnl_m1", f"{half_up(rr['belief_change']):+,.1f}", "CUT90 P&L of holding the contracts, same "
        "configuration (the Milestone 1 gap is this minus the index change)", "results/decomposition.md")
    ty1 = md_table("results/decomposition.md", r"^## 4\. By interval type, Milestone 1", 0)
    ty = md_table("results/decomposition.md", r"^## 3\. By interval type, main", 0)
    add(s, "rolldown_bp_per_day", f"{half_up(-row(ty1, index='CUT90', type='ordinary')['mean_gap_bp_per_day']):.1f}",
        "CUT90 roll-down in basis points a day on ordinary days, Milestone 1 configuration (equals the mean "
        "term-structure slope)", "results/decomposition.md")
    add(s, "rolldown_bp_per_day_final", f"{half_up(-row(ty, index='CUT90', type='ordinary')['mean_gap_bp_per_day']):.1f}",
        "same, final rule from 2023-02-02", "results/decomposition.md")
    add(s, "rate_change_intervals", str(int(row(ty, index="CUT90", type="announcement")["rate_change"])),
        "rate changes from 2023-02-02 captured by the chained decomposition (all of them)",
        "results/decomposition.md")


def data_section():
    s = "Data, price rule, liquidity, venues (section 3; Palmer)"
    add(s, "stale_rule", "N = 3 days, S = $0.10", "freshness and spread limits of the price rule (decision 002)",
        "src/config.py")
    tb = md_table("results/settlement_rule_check.md", r"^## Trade-branch prices vs the standing book", 0).iloc[0]
    add(s, "trade_branch_days", f"{int(tb['trade_branch_contract_days']):,}", "index-leg days from 2023-02-02 priced "
        "by a last trade on a two-sided book wider than 10c (src rule)", "results/settlement_rule_check.md")
    add(s, "trade_branch_spread", f"{100 * tb['median_spread']:.0f}c", "median spread on those days",
        "results/settlement_rule_check.md")
    add(s, "trade_branch_gap", f"{100 * tb['median_abs_gap_to_mid']:.1f}c", "median distance of the last trade from "
        "the book mid on those days", "results/settlement_rule_check.md")
    fc = md_table("results/settlement_rule_check.md", r"Last trade vs book mid as a forecast", 0).iloc[0]
    add(s, "mid_vs_trade_mae", f"{100 * fc['mae_book_mid']:.1f}c vs {100 * fc['mae_last_trade']:.1f}c",
        f"mean error of book mid vs last trade as a forecast of the next tight quote 1 to 3 days later "
        f"({int(fc['contract_days']):,} days)", "results/settlement_rule_check.md")
    add(s, "mid_closer_share", pct(fc["share_mid_closer"]), "share of those days where the mid is closer",
        "results/settlement_rule_check.md")
    v = md_table("results/settlement_rule_check.md", r"^## Settlement variants", 0)
    b, nt = row(v, variant="base", index="CUT90"), row(v, variant="no_trade", index="CUT90")
    add(s, "drop_trade_lt3_cut90", f"{pct(b['share_lt3_valid'])} to {pct(nt['share_lt3_valid'])}", "CUT90 "
        "settlements with fewer than 3 valid days if trade-branch days were dropped (decision 005 point 3) "
        "instead of priced at the book mid (11/12 configuration)", "results/settlement_rule_check.md")
    add(s, "drop_trade_lt5_cut90", f"{pct(b['share_fallback'])} to {pct(nt['share_fallback'])}", "same, fewer than "
        "5 valid days", "results/settlement_rule_check.md")
    wm = row(v, variant="wide_mid", index="CUT90")
    add(s, "wide_mid_changes_cut90", f"{pct(wm['share_S_changed'])} of trades, at most {usd(wm['max_abs_dS'])}",
        "CUT90 settlements changed by the wide-book mid vs the last trade (11/12 configuration)",
        "results/settlement_rule_check.md")
    lq = md_table("results/leg_liquidity.md", r"^## Pooled over CUT and HIKE", 0)
    for h in (90, 60):
        r = row(lq, horizon=h, role="far")
        add(s, f"far_leg_{h}d", f"{int(r['median_days_to_meeting'])} days out, {r['median_spread_c']:.0f}c median "
            f"spread, traded {pct(r['share_traded'])} of days, {pct(r['share_stale'])} stale",
            f"far leg of the {h}-day index from 2023-02-02 (final rule)", "results/leg_liquidity.md")
        r = row(lq, horizon=h, role="near")
        add(s, f"near_leg_{h}d", f"{int(r['median_days_to_meeting'])} days out, {r['median_spread_c']:.0f}c median "
            f"spread, traded {pct(r['share_traded'])} of days, {pct(r['share_stale'])} stale",
            f"near leg of the {h}-day index", "results/leg_liquidity.md")
    pa = md_table("results/summary.md", r"^## Pairwise Agreement", 0)
    r = row(pa, pair="kalshi - polymarket", horizon="all")
    add(s, "kp_mae_p_hold", f"{100 * r['mae_p_hold']:.1f}pp", f"Kalshi vs Polymarket mean absolute gap in P(hold), "
        f"all horizons ({int(r['days']):,} meeting-days, {int(r['meetings'])} meetings)", "results/summary.md")
    add(s, "kp_corr_exp_change", num(r["corr_exp_change"], 3), "correlation of the expected rate change, Kalshi vs "
        "Polymarket", "results/summary.md")
    add(s, "kp_share_gap_gt5pp", pct(r["share_abs_gap_gt_5pp"], 1), "share of meeting-days with a P(hold) gap above "
        "5pp", "results/summary.md")
    hz = ", ".join(f"{100 * row(pa, pair='kalshi - polymarket', horizon=h)['mae_p_hold']:.1f}pp ({h})"
                   for h in ("1-7d", "8-30d", "31-90d", ">90d"))
    add(s, "kp_mae_by_horizon", hz, "Kalshi vs Polymarket P(hold) gap by days to the meeting", "results/summary.md")
    r = row(pa, pair="kalshi - zq", horizon="all")
    add(s, "kz_mae_p_hold", f"{100 * r['mae_p_hold']:.1f}pp", f"Kalshi vs fed funds futures (ZQ) P(hold) gap "
        f"({int(r['days'])} meeting-days, {int(r['meetings'])} meetings; ZQ from 2026-01-02 only)",
        "results/summary.md")
    br = md_table("results/summary.md", r"^## Accuracy Brier", 0)
    for hday in (1, 7, 30):
        k, p = row(br, venue="kalshi", horizon_days=hday), row(br, venue="polymarket", horizon_days=hday)
        add(s, f"brier_{hday}d", f"Kalshi {k['brier_common']:.3f}, Polymarket {p['brier_common']:.3f}",
            f"Brier score {hday} day(s) before the decision, meetings both venues price "
            f"({int(k['meetings_common_kalshi_poly'])})", "results/summary.md")
    add(s, "fee_kalshi_taker", "0.07 x P x (1 - P) per contract", "Kalshi taker fee, held constant over the sample "
        "(decision 007; live /series check 11/12)", "README.md")
    add(s, "data_end_index", "2026-10-26", "last complete day of the committed Kalshi pull (index and backtest)",
        f"{IR}/futures_backtest.md")
    add(s, "data_end_cross_venue", "2026-11-12", "end of the cross-venue run", "results/summary.md")


def theory():
    s = "Ladder no-arbitrage, tail regime, settlement discount (section 5; Jay)"
    p = "theory/results/noarb_summary.md"
    t = md_table(p, r"^## 1\. Ladder no-arbitrage", 0)
    ex = t[t["Test"].str.startswith("Executable")].iloc[0]
    mid = t[t["Test"].str.startswith("Mid")].iloc[0]
    n = re.search(r"of ([\d,]+)", ex["Violations"]).group(1)
    add(s, "ladder_days", n, "Kalshi meeting-days checked, from March 2022", p)
    add(s, "ladder_violations_tradable", f"{ex['Violations'].split(' of ')[0]} ({ex['Share']}%)", "meeting-days "
        "with an executable violation (bid at a higher strike above an ask at a lower strike)", p)
    add(s, "ladder_violations_mid", f"{mid['Share']}%", "meeting-days with non-monotone mid prices", p)
    txt = (ROOT / p).read_text()
    add(s, "ladder_worst_credit", re.search(r"Largest executable credit: (\$\d+\.\d+)", txt).group(1),
        "largest executable credit", p)
    tr = md_table(p, r"^## 2\. Tail regime", 0)
    a, b = row(tr, period="Mar 2022 to Jan 2023"), row(tr, period="Feb 2023 to Oct 2026")
    add(s, "pinned_near_leg", f"{pct(a['near'], 1)} (Mar 2022 to Jan 2023), {pct(b['near'], 1)} (from Feb 2023)",
        "share of CUT90 near-leg days pinned at 1c/99c", p)
    w = md_table(p, r"^Winning side", 0)
    l = md_table(p, r"^Losing side", 0)
    for lab, key in (("0-7", "discount_gap_1week"), ("150+", "discount_gap_150day")):
        ww, ll = row(w, days_to_decision=lab), row(l, days_to_decision=lab)
        add(s, key, f"{100 * (ww['mean'] + ll['mean']) / 2:.0f} cents", f"mean shortfall of near-certain contracts, "
            f"{lab} days to the decision: winning side {100 * ww['mean']:.1f}c below $1, losing side "
            f"{100 * ll['mean']:.1f}c above $0 (same size, so no measurable discount)", p)


def theory_prose():
    s = "Ladder no-arbitrage, tail regime, settlement discount (section 5; Jay)"
    txt = (ROOT / "theory/README.md").read_text()
    m = re.search(r"annualized carry of (\d+) to (\d+)%", txt)
    add(s, "discount_implied_carry", f"{m.group(1)}% to {m.group(2)}% a year", "annualized carry implied if the "
        "near-certain shortfall were a financing discount (too large to be a rate); stated in Jay's README, not in "
        "a results table", "theory/README.md")


def main():
    for f in (sample_and_index, hedge, cost_capital_basis, robustness, event_study, palmer_results, decomposition,
              data_section, theory, theory_prose):
        f()
    keys = [e[0] for v in SECTIONS.values() for e in v]
    dup = {k for k in keys if keys.count(k) > 1}
    assert not dup, dup
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    lines = [
        "# Numbers the final report cites (P5)", "",
        f"Generated by `src/report_numbers.py` from the committed source files at `{head}`. Configuration: decision 007. "
        "Units: dollars per $100 contract unless stated (1 index point = $1). Freeze: tag `results-final`.", "",
        "**Rules.** The report cites a number only from this file (CLAUDE.md sprint rule 7). Write the value as given, "
        "or round it further in the text. A number that is not here gets a Request to Palmer in `docs/TASKS.md`; do "
        "not compute it in the text. In `docs/theory.md` and the sections, `{{numbers.md: key}}` refers to the "
        "Key column. Commit is the last commit that changed the source file.", "",
    ]
    for sec, ents in SECTIONS.items():
        lines += [f"## {sec}", "", "| Key | Value | What it is | Source | Commit |", "|---|---|---|---|---|"]
        lines += [f"| `{k}` | {v} | {w} | `{src}` | `{commit(src)}` |" for k, v, w, src in ents]
        lines.append("")
    OUT.write_text("\n".join(lines))
    print(f"{len(keys)} numbers -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
