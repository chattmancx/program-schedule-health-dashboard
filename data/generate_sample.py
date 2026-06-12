"""
Generate data/sample_schedule.xml — a synthetic MS Project XML export for the
"Notional Sensor Upgrade" program. Stdlib only (no lxml/pandas dependency).

Seeded problems for verification:
  - 8 slipped tasks  (Finish > BaselineFinish)
  - 6 near-critical tasks  (TotalSlack 1–4 work days)
  - 2 incomplete milestones past their Finish date
  - 1 milestone with no successor
"""

import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

NS = "http://schemas.microsoft.com/project"
OUT = Path(__file__).parent / "sample_schedule.xml"

# Work-day helpers (Mon–Fri)
def add_work_days(start: date, days: int) -> date:
    d = start
    added = 0
    while added < days:
        d += timedelta(1)
        if d.weekday() < 5:
            added += 1
    return d

def work_days_between(a: date, b: date) -> int:
    count = 0
    d = min(a, b)
    end = max(a, b)
    while d < end:
        if d.weekday() < 5:
            count += 1
        d += timedelta(1)
    return count if b >= a else -count

def fmt(d: date) -> str:
    return d.strftime("%Y-%m-%dT08:00:00")

def fmt_finish(d: date) -> str:
    return d.strftime("%Y-%m-%dT17:00:00")


# ── Task definitions ─────────────────────────────────────────────────────────
# Each dict: name, level, duration (work days), summary, milestone,
#            slip (days to add to Finish only), slack_min (TotalSlack override),
#            pct, no_successor (milestone with no successor)

PROGRAM_START = date(2025, 3, 3)   # Monday

PHASES = [
    # (phase_name, tasks)
    ("Requirements & Stakeholder Engagement", [
        {"name": "Kickoff & charter approval",    "dur": 5,  "pct": 100},
        {"name": "Stakeholder identification",    "dur": 8,  "pct": 100},
        {"name": "Requirements elicitation",      "dur": 15, "pct": 100},
        {"name": "Requirements review",           "dur": 5,  "pct": 100, "slip": 3},
        {"name": "System Requirements Baseline",  "dur": 0,  "pct": 100, "milestone": True},
        {"name": "Concept of operations draft",   "dur": 10, "pct": 100},
        {"name": "CONOPS review & approval",      "dur": 5,  "pct": 100},
        {"name": "Interface requirements capture","dur": 8,  "pct": 95,  "slip": 5},
        {"name": "Trade study initiation",        "dur": 10, "pct": 90},
    ]),
    ("System Design", [
        {"name": "Preliminary design activities", "dur": 20, "pct": 85},
        {"name": "PDR preparation",               "dur": 8,  "pct": 80, "slip": 7},
        {"name": "Preliminary Design Review",     "dur": 0,  "pct": 0,  "milestone": True, "slip": 7},
        {"name": "Design updates post-PDR",       "dur": 12, "pct": 60},
        {"name": "Detailed design - subsystem A", "dur": 15, "pct": 55, "slack_min": 960},
        {"name": "Detailed design - subsystem B", "dur": 15, "pct": 50, "slack_min": 480},
        {"name": "Interface control documents",   "dur": 10, "pct": 45, "slip": 4},
        {"name": "CDR preparation",               "dur": 8,  "pct": 30, "slack_min": 1440},
        {"name": "Critical Design Review",        "dur": 0,  "pct": 0,  "milestone": True},
        {"name": "Design freeze",                 "dur": 3,  "pct": 0,  "slack_min": 1920},
    ]),
    ("Procurement", [
        {"name": "RFP development",               "dur": 10, "pct": 100},
        {"name": "Vendor solicitation",           "dur": 15, "pct": 100},
        {"name": "Proposal evaluation",           "dur": 10, "pct": 90,  "slip": 8},
        {"name": "Contract award",                "dur": 0,  "pct": 0,   "milestone": True},
        {"name": "Vendor kickoff",                "dur": 2,  "pct": 0},
        {"name": "Long-lead item procurement",    "dur": 30, "pct": 15,  "slip": 12},
        {"name": "Hardware delivery - batch 1",   "dur": 0,  "pct": 0,   "milestone": True},
        {"name": "Hardware delivery - batch 2",   "dur": 0,  "pct": 0,   "milestone": True, "no_successor": True},
        {"name": "Receiving inspection",          "dur": 5,  "pct": 0,   "slack_min": 720},
        {"name": "Parts kitting",                 "dur": 8,  "pct": 0},
    ]),
    ("Integration & Test", [
        {"name": "Integration planning",          "dur": 10, "pct": 100},
        {"name": "Lab setup & calibration",       "dur": 8,  "pct": 80},
        {"name": "Subsystem A integration",       "dur": 15, "pct": 60,  "slip": 6},
        {"name": "Subsystem B integration",       "dur": 15, "pct": 40,  "slip": 9},
        {"name": "System-level integration",      "dur": 20, "pct": 20,  "slack_min": 480},
        {"name": "Integration complete",          "dur": 0,  "pct": 0,   "milestone": True},
        {"name": "Unit test - subsystem A",       "dur": 10, "pct": 50},
        {"name": "Unit test - subsystem B",       "dur": 10, "pct": 30,  "slip": 15},
        {"name": "System functional test",        "dur": 15, "pct": 10,  "slack_min": 960},
        {"name": "Test readiness review",         "dur": 0,  "pct": 0,   "milestone": True},
        {"name": "Performance verification",      "dur": 12, "pct": 0},
        {"name": "Test report draft",             "dur": 8,  "pct": 0,   "slack_min": 1440},
    ]),
    ("Operational Test & Evaluation", [
        {"name": "OT&E planning",                 "dur": 10, "pct": 100},
        {"name": "OT&E site preparation",         "dur": 8,  "pct": 60},
        {"name": "OT&E execution phase 1",        "dur": 15, "pct": 20,  "slip": 5},
        {"name": "OT&E execution phase 2",        "dur": 15, "pct": 0},
        {"name": "Data reduction & analysis",     "dur": 10, "pct": 0,   "slack_min": 1920},
        {"name": "OT&E report",                   "dur": 8,  "pct": 0},
        {"name": "OT&E complete",                 "dur": 0,  "pct": 0,   "milestone": True},
        {"name": "Follow-on deficiency resolution","dur": 10, "pct": 0},
        {"name": "Test closure review",           "dur": 3,  "pct": 0},
    ]),
    ("Delivery & Closeout", [
        {"name": "Delivery preparation",          "dur": 8,  "pct": 0},
        {"name": "Final acceptance test",         "dur": 5,  "pct": 0},
        {"name": "System delivery",               "dur": 0,  "pct": 0,   "milestone": True},
        {"name": "Documentation handoff",         "dur": 8,  "pct": 0},
        {"name": "Lessons learned workshop",      "dur": 3,  "pct": 0},
        {"name": "Contract closeout",             "dur": 5,  "pct": 0},
        {"name": "Program closeout",              "dur": 0,  "pct": 0,   "milestone": True},
    ]),
]


def build_tasks():
    """Flatten PHASES into a list of task dicts with computed dates."""
    tasks = []
    uid = 1
    cursor = PROGRAM_START

    # Seeding counters — tracked to verify we hit exactly our targets
    slip_count = 0
    near_crit_count = 0

    # Phase 0: project summary row
    tasks.append({
        "uid": uid, "id": uid,
        "name": "Notional Sensor Upgrade",
        "outline_level": 0, "summary": 1, "milestone": 0, "critical": 0,
        "start": PROGRAM_START, "finish": PROGRAM_START,  # updated later
        "base_start": PROGRAM_START, "base_finish": PROGRAM_START,
        "pct": 0, "slack": 0, "preds": [], "no_successor": False,
    })
    uid += 1

    for phase_name, phase_tasks in PHASES:
        phase_start = cursor
        phase_uid = uid
        # Phase summary row
        tasks.append({
            "uid": uid, "id": uid,
            "name": phase_name,
            "outline_level": 1, "summary": 1, "milestone": 0, "critical": 0,
            "start": phase_start, "finish": phase_start,  # updated later
            "base_start": phase_start, "base_finish": phase_start,
            "pct": 0, "slack": 0, "preds": [], "no_successor": False,
        })
        uid += 1

        prev_uid = None
        for t in phase_tasks:
            is_milestone = t.get("milestone", False)
            dur = t.get("dur", 0)
            slip = t.get("slip", 0)
            slack_min = t.get("slack_min", 0)
            pct = t.get("pct", 0)
            no_succ = t.get("no_successor", False)

            # Baseline dates
            base_start = cursor
            if is_milestone:
                base_finish = base_start
            else:
                base_finish = add_work_days(base_start, dur)

            # Actual dates (slip shifts finish only)
            start = base_start
            finish = add_work_days(base_finish, slip) if slip > 0 else base_finish

            is_critical = (slack_min == 0 and not no_succ)
            preds = [prev_uid] if prev_uid else []

            tasks.append({
                "uid": uid, "id": uid,
                "name": t["name"],
                "outline_level": 2, "summary": 0,
                "milestone": 1 if is_milestone else 0,
                "critical": 1 if is_critical else 0,
                "start": start, "finish": finish,
                "base_start": base_start, "base_finish": base_finish,
                "pct": pct, "slack": slack_min,
                "preds": preds, "no_successor": no_succ,
            })

            if slip > 0:
                slip_count += 1
            if slack_min > 0 and slack_min < 5 * 480:
                near_crit_count += 1

            if not is_milestone:
                cursor = finish

            prev_uid = uid
            uid += 1

        # Update phase summary finish
        tasks[phase_uid - 1]["finish"] = cursor
        tasks[phase_uid - 1]["base_finish"] = cursor

    # Update project summary finish
    tasks[0]["finish"] = cursor
    tasks[0]["base_finish"] = cursor

    print(f"  Slip count:        {slip_count}  (target 8)")
    print(f"  Near-critical:     {near_crit_count}  (target 6)")

    # Find past-due incomplete milestones
    today = date(2026, 6, 12)
    past_due_ms = [
        t["name"] for t in tasks
        if t["milestone"] and t["pct"] < 100 and t["finish"] < today
    ]
    print(f"  Past-due milestones: {len(past_due_ms)}  (target ≥2): {past_due_ms}")

    no_succ_ms = [t["name"] for t in tasks if t.get("no_successor")]
    print(f"  No-successor milestones: {len(no_succ_ms)}  (target 1): {no_succ_ms}")

    return tasks


def write_xml(tasks):
    root = ET.Element("Project")
    root.set("xmlns", NS)

    tasks_el = ET.SubElement(root, "Tasks")
    successor_map = set()
    for t in tasks:
        for p in t["preds"]:
            successor_map.add(p)

    for t in tasks:
        task_el = ET.SubElement(tasks_el, "Task")
        ET.SubElement(task_el, "UID").text = str(t["uid"])
        ET.SubElement(task_el, "ID").text = str(t["id"])
        ET.SubElement(task_el, "Name").text = t["name"]
        ET.SubElement(task_el, "OutlineLevel").text = str(t["outline_level"])
        ET.SubElement(task_el, "Summary").text = str(t["summary"])
        ET.SubElement(task_el, "Milestone").text = str(t["milestone"])
        ET.SubElement(task_el, "Critical").text = str(t["critical"])
        ET.SubElement(task_el, "Start").text = fmt(t["start"])
        ET.SubElement(task_el, "Finish").text = fmt_finish(t["finish"])
        ET.SubElement(task_el, "BaselineStart").text = fmt(t["base_start"])
        ET.SubElement(task_el, "BaselineFinish").text = fmt_finish(t["base_finish"])
        ET.SubElement(task_el, "PercentComplete").text = str(t["pct"])
        ET.SubElement(task_el, "TotalSlack").text = str(t["slack"])

        for pred_uid in t["preds"]:
            pl = ET.SubElement(task_el, "PredecessorLink")
            ET.SubElement(pl, "PredecessorUID").text = str(pred_uid)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(OUT), encoding="unicode", xml_declaration=True)
    print(f"\nWrote {OUT}")
    task_count = sum(1 for t in tasks if not t["summary"])
    print(f"  Total tasks (non-summary): {task_count}")


if __name__ == "__main__":
    print("Generating sample_schedule.xml...")
    tasks = build_tasks()
    write_xml(tasks)
