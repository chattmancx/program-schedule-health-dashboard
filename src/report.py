"""
Generate the RAG status table and variance chart.

Public API
----------
    build_rag_table(df, as_of) -> pd.DataFrame
    save_report(df, as_of, out_dir)
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


def _save_variance_chart(rag_df: pd.DataFrame, out_dir: Path):
    flagged = rag_df[rag_df["RAG"] != "Green"].copy()
    flagged = flagged.sort_values("slip_days", ascending=True)

    if flagged.empty:
        print("  No flagged tasks — skipping chart.")
        return

    fig, ax = plt.subplots(figsize=(12, max(6, len(flagged) * 0.4)))

    colors = [RAG_COLORS[r] for r in flagged["RAG"]]
    bars = ax.barh(flagged["name"], flagged["slip_days"], color=colors, edgecolor="white", height=0.6)

    ax.set_xlabel("Schedule Slip (calendar days)")
    ax.set_title("Schedule Variance — Flagged Tasks\n(Baseline Finish vs. Current Finish)", pad=12)
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")

    # Legend
    patches = [mpatches.Patch(color=RAG_COLORS[r], label=r) for r in ["Red", "Amber", "Green"]]
    ax.legend(handles=patches, loc="lower right")

    # Value labels
    for bar, val in zip(bars, flagged["slip_days"]):
        if val > 0:
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    f"+{val:.0f}d", va="center", fontsize=8)

    plt.tight_layout()
    path = out_dir / "variance_chart.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")


def save_report(df: pd.DataFrame, as_of: date, out_dir: Path):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rag_df = build_rag_table(df, as_of)
    _print_summary(rag_df)
    _save_rag_csv(rag_df, out_dir)
    _save_variance_chart(rag_df, out_dir)
