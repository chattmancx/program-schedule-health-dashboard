"""Tests for src/parser.py — reads the real sample_schedule.xml."""

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from parser import parse_schedule

XML_PATH = Path(__file__).parent.parent / "data" / "sample_schedule.xml"

EXPECTED_COLUMNS = [
    "uid", "name", "outline_level", "is_summary", "is_milestone",
    "is_critical", "start", "finish", "baseline_start", "baseline_finish",
    "pct_complete", "total_slack_days", "predecessor_uids",
]


@pytest.fixture(scope="module")
def df():
    return parse_schedule(XML_PATH)


def test_row_count(df):
    assert len(df) >= 60


def test_columns_present(df):
    for col in EXPECTED_COLUMNS:
        assert col in df.columns, f"Missing column: {col}"


def test_pct_complete_in_range(df):
    assert df["pct_complete"].between(0, 100).all()


def test_no_nat_dates_for_work_tasks(df):
    work = df[~df["is_summary"]]
    assert work["start"].notna().all(), "NaT found in start for work tasks"
    assert work["finish"].notna().all(), "NaT found in finish for work tasks"


def test_uid_unique(df):
    assert df["uid"].is_unique


def test_slack_days_non_negative(df):
    assert (df["total_slack_days"] >= 0).all()


def test_milestone_count(df):
    assert df["is_milestone"].sum() >= 5


def test_predecessor_uids_are_lists(df):
    assert all(isinstance(v, list) for v in df["predecessor_uids"])
