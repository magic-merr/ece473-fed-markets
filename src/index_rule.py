"""Which price rule the final results use (decision 007). Palmer.

Decision 007 adds the rule `final` (src rule plus the wide-book mid) to index/legs.py (Ari, A2). Palmer's
scripts that import index/ read-only call main_rule() so they run unchanged before and after that push:
'final' once index/legs.py has it, else 'src' (and the output says it is a pre-A4 run).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "index") not in sys.path:
    sys.path.append(str(ROOT / "index"))  # appended: src/figures.py and index/figures.py share a name

import legs  # noqa: E402


def main_rule() -> str:
    try:
        legs.contract_days("final")
        return "final"
    except ValueError:
        return "src"


def pre_a4_note(rule: str) -> list[str]:
    if rule == "final":
        return []
    return ["**Pre-A4 run.** `index/legs.py` does not have the decision 007 rule `final` yet, so this uses `src`. "
            "Rerun after Ari's A4 push; the script picks up `final` without changes.", ""]
