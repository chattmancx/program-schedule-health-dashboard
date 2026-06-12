"""
Health flag functions for MS Project schedule analysis.

Each function accepts the full task DataFrame and returns a filtered DataFrame
of flagged tasks. Summary rows are always excluded.

Public API
----------
    flag_slippage(df)
    flag_near_critical(df, threshold_days=5.0)
    flag_behind_schedule(df, as_of)
    flag_milestone_gap(df, as_of)
    get_health_summary(df, as_of) -> dict
"""

from datetime import date
import pandas as pd


def _work_tasks(df: pd.DataFrame) -> pd.DataFrame:
    return df[~df["is_summary"]].copy()


def flag_slippage(df: pd.DataFrame) -> pd.DataFrame:
    """Tasks where Finish > BaselineFinish and not yet 100% complete."""
    wt = _work_tasks(df)
    mask = (
        wt["baseline_finish"].notna()
        & (wt["finish"] > wt["baseline_finish"])
        & (wt["pct_complete"] < 100)
    )
    return wt[mask].copy()


def flag_near_critical(df: pd.DataFrame, threshold_days: float = 5.0) -> pd.DataFrame:
    """Non-critical tasks with TotalSlack < threshold and not already complete."""
    wt = _work_tasks(df)
    mask = (
        ~wt["is_critical"]
        & ~wt["is_milestone"]
        & (wt["total_slack_days"] > 0)
        & (wt["total_slack_days"] < threshold_days)
        & (wt["pct_complete"] < 100)
    )
    return wt[mask].copy()


def flag_behind_schedule(df: pd.DataFrame, as_of: date) -> pd.DataFrame:
    """
    Tasks where actual % complete lags expected progress by more than 10 points.

    Expected % = elapsed baseline days / total baseline days * 100.
    Only applies to tasks that have started (baseline_start <= as_of)
    but are not yet complete.
    """
    wt = _work_tasks(df)
    as_of_ts = pd.Timestamp(as_of)

    has_baseline = wt["baseline_start"].notna() & wt["baseline_finish"].notna()
    started = wt["baseline_start"] <= as_of_ts
    not_done = wt["pct_complete"] < 100

    wt = wt[has_baseline & started & not_done].copy()
    if wt.empty:
        return wt

    total_days = (wt["baseline_finish"] - wt["baseline_start"]).dt.total_seconds() / 86400
    elapsed = (as_of_ts - wt["baseline_start"]).dt.total_seconds() / 86400
    expected_pct = (elapsed / total_days.replace(0, float("nan"))) * 100
    expected_pct = expected_pct.clip(0, 100)

    mask = wt["pct_complete"] < (expected_pct - 10)
    return wt[mask].copy()


def flag_milestone_gap(df: pd.DataFrame, as_of: date) -> pd.DataFrame:
    """
    Incomplete milestones that are past their finish date, OR milestones that
    have no task designating them as a predecessor (no successor).
    """
    wt = _work_tasks(df)
    as_of_ts = pd.Timestamp(as_of)

    milestones = wt[wt["is_milestone"]].copy()

    # Build the set of UIDs that appear in any task's predecessor list
    all_pred_uids: set = set()
    for preds in df["predecessor_uids"]:
        all_pred_uids.update(preds)

    past_due = (milestones["finish"] < as_of_ts) & (milestones["pct_complete"] < 100)
    no_successor = ~milestones["uid"].isin(all_pred_uids)

    return milestones[past_due | no_successor].copy()


def get_health_summary(df: pd.DataFrame, as_of: date) -> dict:
    slipped = flag_slippage(df)
    near_crit = flag_near_critical(df)
    behind = flag_behind_schedule(df, as_of)
    gaps = flag_milestone_gap(df, as_of)

    return {
        "slippage":       {"count": len(slipped),   "uids": slipped["uid"].tolist()},
        "near_critical":  {"count": len(near_crit),  "uids": near_crit["uid"].tolist()},
        "behind_schedule":{"count": len(behind),     "uids": behind["uid"].tolist()},
        "milestone_gap":  {"count": len(gaps),       "uids": gaps["uid"].tolist()},
    }
