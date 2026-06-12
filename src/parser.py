"""
Parse an MS Project XML export into a pandas DataFrame.

Public API
----------
    parse_schedule(xml_path) -> pd.DataFrame
"""

from pathlib import Path
import re
import pandas as pd
from lxml import etree

NS = "http://schemas.microsoft.com/project"
NS_RE = re.compile(r"\{[^}]+\}")


def _strip_ns(tree):
    """Remove namespace prefixes from all element tags in-place."""
    for el in tree.iter():
        el.tag = NS_RE.sub("", el.tag)


def _text(task_el, tag, default=None):
    el = task_el.find(tag)
    return el.text if el is not None and el.text else default


def _int(task_el, tag, default=0) -> int:
    v = _text(task_el, tag)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _float(task_el, tag, default=float("nan")) -> float:
    v = _text(task_el, tag)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _dt(task_el, tag):
    v = _text(task_el, tag)
    if not v:
        return pd.NaT
    try:
        return pd.to_datetime(v)
    except Exception:
        return pd.NaT


def _predecessors(task_el) -> list:
    uids = []
    for link in task_el.findall("PredecessorLink"):
        uid_el = link.find("PredecessorUID")
        if uid_el is not None and uid_el.text:
            try:
                uids.append(int(uid_el.text))
            except ValueError:
                pass
    return uids


def parse_schedule(xml_path: str | Path) -> pd.DataFrame:
    xml_path = Path(xml_path)
    tree = etree.parse(str(xml_path))
    _strip_ns(tree)
    root = tree.getroot()

    rows = []
    for task_el in root.findall(".//Task"):
        slack_min = _float(task_el, "TotalSlack", default=0.0)
        rows.append({
            "uid":              _int(task_el, "UID"),
            "name":             _text(task_el, "Name", ""),
            "outline_level":    _int(task_el, "OutlineLevel"),
            "is_summary":       bool(_int(task_el, "Summary")),
            "is_milestone":     bool(_int(task_el, "Milestone")),
            "is_critical":      bool(_int(task_el, "Critical")),
            "start":            _dt(task_el, "Start"),
            "finish":           _dt(task_el, "Finish"),
            "baseline_start":   _dt(task_el, "BaselineStart"),
            "baseline_finish":  _dt(task_el, "BaselineFinish"),
            "pct_complete":     _float(task_el, "PercentComplete", default=0.0),
            "total_slack_days": slack_min / 480.0,
            "predecessor_uids": _predecessors(task_el),
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_schedule.xml"
    df = parse_schedule(path)
    print(df[["uid", "name", "is_summary", "is_milestone", "pct_complete", "total_slack_days"]].to_string())
    print(f"\n{len(df)} rows total ({df['is_summary'].sum()} summary, {df['is_milestone'].sum()} milestones)")
