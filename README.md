# Program Schedule Health Dashboard

**Owner:** Christopher X. Chattman, PMP
**Track:** Track 1 — Advanced Python & Data Engineering
**Status:** In development

---

## Problem

Program managers can't easily spot schedule slippage, critical-path risk, or missed milestones buried in a large Microsoft Project file. This tool parses an MS Project XML export and surfaces the at-risk items automatically.

## What it does

Given an MS Project XML export, the tool:
- Flags slipped tasks (actual vs. baseline dates)
- Identifies near-critical-path float
- Detects milestones with missing successors or date gaps
- Outputs a RAG status table and variance chart

## Quickstart

```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows
pip install -r requirements.txt

python src/parser.py --input data/sample_schedule.xml
```

## Project structure

```
data/          Sample MS Project XML export (synthetic)
src/           Parser and analysis modules
docs/          Screenshots and generated reports
```

## Generating the sample schedule

**macOS:** Author a notional schedule in [ProjectLibre](https://www.projectlibre.com/) or [GanttProject](https://www.ganttproject.biz/) and export as MS Project XML.

**Windows:** Author in Microsoft Project and export as XML.

Commit the exported XML to `data/` so the parser can run without the authoring tool.

## Data

All data in this repository is synthetic. No real program data is used.

## References

- *Python for Data Analysis* — McKinney
- pandas docs: pandas.pydata.org
- python-pptx / python-docx: PyPI
- ProjectLibre: projectlibre.com
- GanttProject: ganttproject.biz
