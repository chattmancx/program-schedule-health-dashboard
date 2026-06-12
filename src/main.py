"""
Program Schedule Health Dashboard — CLI entry point.

Usage
-----
    python src/main.py --input data/sample_schedule.xml
    python src/main.py --input data/sample_schedule.xml --as-of 2026-06-12 --out-dir docs/
"""

import argparse
from datetime import date
from pathlib import Path
import sys

# Allow running from project root: python src/main.py
sys.path.insert(0, str(Path(__file__).parent))

from parser import parse_schedule
from report import save_report


def main():
    p = argparse.ArgumentParser(description="Program Schedule Health Dashboard")
    p.add_argument("--input", required=True, help="Path to MS Project XML export")
    p.add_argument("--as-of", default=str(date.today()),
                   help="Analysis date (YYYY-MM-DD). Defaults to today.")
    p.add_argument("--out-dir", default="docs/",
                   help="Directory for output files (CSV, PNG). Defaults to docs/.")
    args = p.parse_args()

    as_of = date.fromisoformat(args.as_of)
    print(f"Parsing {args.input}  (as-of {as_of})")

    df = parse_schedule(args.input)
    print(f"  {len(df)} tasks loaded ({df['is_summary'].sum()} summary, "
          f"{df['is_milestone'].sum()} milestones)")

    save_report(df, as_of, Path(args.out_dir))


if __name__ == "__main__":
    main()
