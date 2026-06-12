"""Tests for src/analyzer.py — uses in-memory DataFrame fixtures."""

import sys
from pathlib import Path
from datetime import date
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from analyzer import (
    flag_slippage,
    flag_near_critical,
    flag_behind_schedule,
    flag_milestone_gap,
    get_health_summary,
)

AS_OF = date(2026, 6, 12)


def _ts(s: str):
    return pd.Timestamp(s)


def make_df(rows):
    defaults = {
        "is_summary": False, "is_milestone": False, "is_critical": False,
        "pct_complete": 0.0, "total_slack_days": 0.0,
        "baseline_start": pd.NaT, "baseline_finish": pd.NaT,
        "start": pd.NaT, "finish": pd.NaT,
        "predecessor_uids": [],
    }
    records = [{**defaults, **r} for r in rows]
    return pd.DataFrame(records)


# ── flag_slippage ─────────────────────────────────────────────────────────────

def test_slippage_flags_slipped_task():
    df = make_df([
        {"uid": 1, "name": "On time",  "finish": _ts("2026-05-01"), "baseline_finish": _ts("2026-05-01"), "pct_complete": 50},
        {"uid": 2, "name": "Slipped",  "finish": _ts("2026-05-10"), "baseline_finish": _ts("2026-05-01"), "pct_complete": 50},
        {"uid": 3, "name": "Complete", "finish": _ts("2026-05-10"), "baseline_finish": _ts("2026-05-01"), "pct_complete": 100},
    ])
    result = flag_slippage(df)
    assert list(result["uid"]) == [2]


def test_slippage_skips_summary():
    df = make_df([
        {"uid": 1, "is_summary": True, "finish": _ts("2026-05-10"),
         "baseline_finish": _ts("2026-05-01"), "pct_complete": 50},
    ])
    assert flag_slippage(df).empty


# ── flag_near_critical ────────────────────────────────────────────────────────

def test_near_critical_flags_low_float():
    df = make_df([
        {"uid": 1, "name": "Critical",     "is_critical": True,  "total_slack_days": 0.0, "pct_complete": 50},
        {"uid": 2, "name": "Near-crit",    "is_critical": False, "total_slack_days": 2.0, "pct_complete": 50},
        {"uid": 3, "name": "Plenty float", "is_critical": False, "total_slack_days": 8.0, "pct_complete": 50},
        {"uid": 4, "name": "Complete",     "is_critical": False, "total_slack_days": 2.0, "pct_complete": 100},
    ])
    result = flag_near_critical(df)
    assert list(result["uid"]) == [2]


def test_near_critical_custom_threshold():
    df = make_df([
        {"uid": 1, "is_critical": False, "total_slack_days": 6.0, "pct_complete": 50},
    ])
    assert flag_near_critical(df, threshold_days=5.0).empty
    assert len(flag_near_critical(df, threshold_days=7.0)) == 1


# ── flag_behind_schedule ──────────────────────────────────────────────────────

def test_behind_schedule_flags_lagging_task():
    # Task should be ~50% done; actual is 10% — behind
    df = make_df([
        {
            "uid": 1, "name": "Behind",
            "baseline_start": _ts("2026-01-01"), "baseline_finish": _ts("2026-12-31"),
            "pct_complete": 10.0,
        },
        {
            "uid": 2, "name": "On track",
            "baseline_start": _ts("2026-01-01"), "baseline_finish": _ts("2026-12-31"),
            "pct_complete": 50.0,
        },
    ])
    result = flag_behind_schedule(df, AS_OF)
    assert 1 in result["uid"].values
    assert 2 not in result["uid"].values


def test_behind_schedule_skips_not_yet_started():
    df = make_df([
        {
            "uid": 1, "name": "Future",
            "baseline_start": _ts("2027-01-01"), "baseline_finish": _ts("2027-06-30"),
            "pct_complete": 0.0,
        },
    ])
    assert flag_behind_schedule(df, AS_OF).empty


# ── flag_milestone_gap ────────────────────────────────────────────────────────

def test_milestone_gap_past_due():
    df = make_df([
        {"uid": 1, "name": "Past-due MS", "is_milestone": True,
         "finish": _ts("2026-01-01"), "pct_complete": 0.0, "predecessor_uids": []},
        {"uid": 2, "name": "Future MS",   "is_milestone": True,
         "finish": _ts("2027-01-01"), "pct_complete": 0.0, "predecessor_uids": [1]},
        {"uid": 3, "name": "Done MS",     "is_milestone": True,
         "finish": _ts("2026-01-01"), "pct_complete": 100.0, "predecessor_uids": []},
    ])
    # uid=2 is a successor of uid=1, so uid=1 has a successor; uid=2 is future
    # uid=3 is complete so not past-due; but has no successor → flagged as gap
    result = flag_milestone_gap(df, AS_OF)
    flagged_uids = set(result["uid"])
    assert 1 in flagged_uids   # past due
    assert 3 in flagged_uids   # no successor


def test_milestone_gap_no_successor():
    df = make_df([
        {"uid": 1, "name": "Orphan MS", "is_milestone": True,
         "finish": _ts("2027-01-01"), "pct_complete": 0.0, "predecessor_uids": []},
    ])
    result = flag_milestone_gap(df, AS_OF)
    assert 1 in result["uid"].values


# ── get_health_summary ────────────────────────────────────────────────────────

def test_health_summary_keys():
    df = make_df([
        {"uid": 1, "finish": _ts("2026-05-10"), "baseline_finish": _ts("2026-05-01"),
         "pct_complete": 50, "baseline_start": _ts("2026-01-01")},
    ])
    summary = get_health_summary(df, AS_OF)
    for key in ("slippage", "near_critical", "behind_schedule", "milestone_gap"):
        assert key in summary
        assert "count" in summary[key]
        assert "uids" in summary[key]
