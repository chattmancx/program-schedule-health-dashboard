"""
Program Schedule Health Dashboard — CLI entry point.

Usage
-----
    python src/main.py --input data/sample_schedule.xml
    python src/main.py --input data/sample_schedule.xml --as-of 2026-06-12
    python src/main.py --input data/sample_schedule.xml --chart-rag all
    python src/main.py --input data/sample_schedule.xml --chart-rag red
    python src/main.py --input data/sample_schedule.xml --chart-rag red,amber
    python src/main.py --input data/sample_schedule.xml --date-from 2025-06-01 --date-to 2026-12-31

--chart-rag   Comma-separated RAG statuses to include in the variance chart.
              Accepted values: red, amber, green, or "all".
              Default: red,amber  (all flagged tasks, no Green).

--date-from   Restrict the chart to tasks whose finish date is on or after
              this date (YYYY-MM-DD). Does not affect the RAG table or CSV.

--date-to     Restrict the chart to tasks whose finish date is on or before
              this date (YYYY-MM-DD). Does not affect the RAG table or CSV.
"""

import argparse
from datetime import date
from pathlib import Path
import sys

# Allow running from project root: python src/main.py
sys.path.insert(0, str(Path(__file__).parent))

from parser import parse_schedule
from report import save_report

_VALID_RAG = {"red": "Red", "amber": "Amber", "green": "Green"}


def _parse_chart_rag(raw: str) -> list[str]:
    if raw.lower() == "all":
        return ["Red", "Amber", "Green"]
    statuses = []
    for token in raw.split(","):
        token = token.strip().lower()
        if token not in _VALID_RAG:
            raise argparse.ArgumentTypeError(
                f"Unknown RAG value '{token}'. Use: red, amber, green, or all."
            )
        statuses.append(_VALID_RAG[token])
    return statuses


def main():
    p = argparse.ArgumentParser(
        description="Program Schedule Health Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", required=True, help="Path to MS Project XML export")
    p.add_argument("--as-of", default=str(date.today()),
                   help="Analysis date (YYYY-MM-DD). Defaults to today.")
    p.add_argument("--out-dir", default="docs/",
                   help="Output directory for CSV and PNG. Defaults to docs/.")
    p.add_argument("--chart-rag", default="red,amber",
                   help="RAG statuses to show in the chart: red, amber, green, or all. "
                        "Comma-separated. Default: red,amber.")
    p.add_argument("--date-from", default=None,
                   help="Chart: only tasks with finish >= this date (YYYY-MM-DD).")
    p.add_argument("--date-to", default=None,
                   help="Chart: only tasks with finish <= this date (YYYY-MM-DD).")
    p.add_argument("--chart-name", default="variance_chart",
                   help="Output filename stem for the chart PNG (no extension). "
                        "Default: variance_chart.")
    args = p.parse_args()

    as_of = date.fromisoformat(args.as_of)

    try:
        chart_rag = _parse_chart_rag(args.chart_rag)
    except argparse.ArgumentTypeError as e:
        p.error(str(e))

    date_from = date.fromisoformat(args.date_from) if args.date_from else None
    date_to   = date.fromisoformat(args.date_to)   if args.date_to   else None

    print(f"Parsing {args.input}  (as-of {as_of})")
    df = parse_schedule(args.input)
    print(f"  {len(df)} tasks loaded ({df['is_summary'].sum()} summary, "
          f"{df['is_milestone'].sum()} milestones)")

    save_report(df, as_of, Path(args.out_dir),
                chart_rag=chart_rag, date_from=date_from, date_to=date_to,
                chart_name=args.chart_name)


if __name__ == "__main__":
    main()
