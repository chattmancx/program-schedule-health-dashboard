"""
Generate the RAG status table and variance chart.

Public API
----------
    build_rag_table(df, as_of) -> pd.DataFrame
    save_report(df, as_of, out_dir, chart_rag=None, date_from=None, date_to=None)

chart_rag  : list of RAG statuses to include in the chart, e.g. ["Red"],
             ["Red", "Amber"], or ["Red", "Amber", "Green"]. Default: ["Red", "Amber"].
date_from  : only include tasks whose finish date >= this date (datetime-like).
date_to    : only include tasks whose finish date <= this date (datetime-like).
"""

from datetime import date
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from analyzer import (
    flag_slippage,
    flag_near_critical,
    flag_behind_schedule,
    flag_milestone_gap,
)

RAG_COLORS = {"Red": "#d32f2f", "Amber": "#f9a825", "Green": "#388e3c"}
_RAG_ORDER  = {"Red": 0, "Amber": 1, "Green": 2}
_DEFAULT_CHART_RAG = ["Red", "Amber"]


def build_rag_table(df: pd.DataFrame, as_of: date) -> pd.DataFrame:
    wt = df[~df["is_summary"]].copy()

    slipped_uids  = set(flag_slippage(df)["uid"])
    near_uids     = set(flag_near_critical(df)["uid"])
    behind_uids   = set(flag_behind_schedule(df, as_of)["uid"])
    gap_uids      = set(flag_milestone_gap(df, as_of)["uid"])

    def rag(row):
        uid = row["uid"]
        if uid in gap_uids:
            return "Red"
        if uid in slipped_uids and row["is_critical"]:
            return "Red"
        if uid in slipped_uids or uid in near_uids or uid in behind_uids:
            return "Amber"
        return "Green"

    wt["RAG"] = wt.apply(rag, axis=1)

    # Slip variance in calendar days
    wt["slip_days"] = (
        (wt["finish"] - wt["baseline_finish"]).dt.total_seconds() / 86400
    ).round(1)
    wt["slip_days"] = wt["slip_days"].clip(lower=0)

    cols = ["uid", "name", "RAG", "pct_complete", "finish", "baseline_finish",
            "slip_days", "is_critical", "is_milestone", "total_slack_days"]
    return wt[cols].reset_index(drop=True)


def _save_rag_csv(rag_df: pd.DataFrame, out_dir: Path):
    path = out_dir / "rag_table.csv"
    rag_df.to_csv(path, index=False)
    print(f"  Saved {path}")


def _print_summary(rag_df: pd.DataFrame):
    counts = rag_df["RAG"].value_counts()
    total = len(rag_df)
    print(f"\nSchedule Health Summary  ({total} tasks)")
    print(f"  Red:   {counts.get('Red', 0)}")
    print(f"  Amber: {counts.get('Amber', 0)}")
    print(f"  Green: {counts.get('Green', 0)}")

    flagged = rag_df[rag_df["RAG"] != "Green"][
        ["uid", "name", "RAG", "pct_complete", "slip_days", "total_slack_days"]
    ].copy()
    flagged.columns = ["UID", "Task", "RAG", "% Done", "Slip (days)", "Float (days)"]
    print("\nFlagged Tasks:\n")
    print(flagged.to_string(index=False))


def _apply_chart_filters(
    rag_df: pd.DataFrame,
    chart_rag: list[str],
    date_from,
    date_to,
) -> pd.DataFrame:
    """Return the subset of rag_df that passes RAG and date-range filters."""
    subset = rag_df[rag_df["RAG"].isin(chart_rag)].copy()

    if date_from is not None:
        subset = subset[subset["finish"] >= pd.Timestamp(date_from)]
    if date_to is not None:
        subset = subset[subset["finish"] <= pd.Timestamp(date_to)]

    # Sort: Red → Amber → Green, then by descending slip within each group
    subset["_rag_order"] = subset["RAG"].map(_RAG_ORDER)
    subset = subset.sort_values(["_rag_order", "slip_days"], ascending=[False, True])
    subset = subset.drop(columns=["_rag_order"])
    return subset


def _save_variance_chart(
    rag_df: pd.DataFrame,
    out_dir: Path,
    chart_rag: list[str] | None = None,
    date_from=None,
    date_to=None,
):
    if chart_rag is None:
        chart_rag = _DEFAULT_CHART_RAG

    subset = _apply_chart_filters(rag_df, chart_rag, date_from, date_to)

    if subset.empty:
        print("  No tasks match the chart filters — skipping chart.")
        return

    n = len(subset)
    fig, ax = plt.subplots(figsize=(13, max(8, n * 0.45)))

    colors = [RAG_COLORS[r] for r in subset["RAG"]]
    bars = ax.barh(subset["name"], subset["slip_days"], color=colors, edgecolor="white", height=0.65)

    ax.set_xlabel("Schedule Slip (calendar days)")

    # Build a descriptive subtitle from active filters
    rag_label = "/".join(chart_rag)
    parts = [f"RAG: {rag_label}"]
    if date_from:
        parts.append(f"from {date_from}")
    if date_to:
        parts.append(f"to {date_to}")
    filter_note = "  |  ".join(parts)
    ax.set_title(
        f"Schedule Variance  ({n} tasks)\n{filter_note}",
        pad=12,
    )
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")

    # Legend — only include RAG statuses that are actually present
    present = [r for r in ["Red", "Amber", "Green"] if r in chart_rag]
    patches = [mpatches.Patch(color=RAG_COLORS[r], label=r) for r in present]
    ax.legend(handles=patches, loc="lower right")

    # Value labels
    for bar, val in zip(bars, subset["slip_days"]):
        if val > 0:
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    f"+{val:.0f}d", va="center", fontsize=8)

    plt.tight_layout()
    path = out_dir / "variance_chart.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}  ({n} tasks)")


def save_report(
    df: pd.DataFrame,
    as_of: date,
    out_dir: Path,
    chart_rag: list[str] | None = None,
    date_from=None,
    date_to=None,
):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rag_df = build_rag_table(df, as_of)
    _print_summary(rag_df)
    _save_rag_csv(rag_df, out_dir)
    _save_variance_chart(rag_df, out_dir, chart_rag=chart_rag, date_from=date_from, date_to=date_to)
