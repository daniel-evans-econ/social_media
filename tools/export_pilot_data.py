"""Export shared messages (and period scores) from a finished pilot.

Run this between pilots on the oTree "all-apps wide" CSV you download from the
admin (Data tab). It produces, in ``social_media/data/``:

  - ``messages_<pilot>.json`` : shared peer messages keyed by (task, set_id),
    which the NEXT pilot serves to participants facing the same set.
  - ``iq_scores_<pilot>.json`` : the list of period scores (number correct out
    of 15) per IQ component, to help you fit the IQ distribution that the next
    pilot reads from ``iq_distribution_<pilot>.json``.

Usage:
    python tools/export_pilot_data.py --pilot initial --csv path/to/wide.csv

The script only reads the CSV; it never touches the live database.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "social_media" / "data"

NUM_ROUNDS = 45
PERIOD_LENGTH = 15
TASK_IQ_COMPONENT = {
    "shape_rotation": "spatial",
    "ravens": "fluid",
    "working_memory": "working_memory",
    "sequences": "numerical",
}

CELL_RE = re.compile(r"^social_media\.(\d+)\.player\.(\w+)$")


def _read_wide_csv(path: Path):
    """Return a list of participants, each a dict: round -> {field: value}."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    participants = []
    for row in rows:
        per_round = defaultdict(dict)
        for col, val in row.items():
            m = CELL_RE.match(col or "")
            if not m:
                continue
            rnd = int(m.group(1))
            field = m.group(2)
            per_round[rnd][field] = val
        if per_round:
            participants.append(per_round)
    return participants


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def build(pilot: str, csv_path: Path):
    participants = _read_wide_csv(csv_path)

    # messages[task][set_id][quant|qual] -> list of entries
    messages: dict = defaultdict(lambda: defaultdict(lambda: {"quantitative": [], "qualitative": []}))
    # scores[component] -> list of period scores
    scores: dict = defaultdict(list)

    for per_round in participants:
        # Per-period scores (number correct out of 15) keyed by component.
        for period in range(3):
            start = period * PERIOD_LENGTH + 1
            end = start + PERIOD_LENGTH
            correct = 0
            task = None
            counted = False
            for rnd in range(start, end):
                rec = per_round.get(rnd)
                if not rec:
                    continue
                task = rec.get("q_task") or task
                if _truthy(rec.get("q_correct")):
                    correct += 1
                if rec.get("q_task"):
                    counted = True
            if counted and task in TASK_IQ_COMPONENT:
                scores[TASK_IQ_COMPONENT[task]].append(correct)

        # Shared messages per feedback round.
        for rnd, rec in per_round.items():
            if not _truthy(rec.get("report_shared")):
                continue
            task = rec.get("q_task")
            set_id = rec.get("q_set_id")
            if not task or not set_id:
                continue
            cond = rec.get("condition") or ""
            name = (rec.get("report_display_name") or "").strip()
            if cond == "quantitative_social":
                num = rec.get("report_number")
                if num in (None, ""):
                    continue
                messages[task][set_id]["quantitative"].append(
                    {"name": name, "number": int(float(num))}
                )
            elif cond == "qualitative_social":
                emoji = (rec.get("report_emoji") or "").strip()
                sentence = (rec.get("report_message") or "").strip()
                if not sentence:
                    continue
                messages[task][set_id]["qualitative"].append(
                    {"name": name, "emoji": emoji, "sentence": sentence}
                )

    # Convert defaultdicts to plain dicts and prune empty sets.
    msg_out = {}
    for task, sets in messages.items():
        msg_out[task] = {}
        for set_id, pools in sets.items():
            pruned = {k: v for k, v in pools.items() if v}
            if pruned:
                msg_out[task][set_id] = pruned

    scores_out = {comp: sorted(vals) for comp, vals in scores.items()}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    msg_path = DATA_DIR / f"messages_{pilot}.json"
    scores_path = DATA_DIR / f"iq_scores_{pilot}.json"
    with open(msg_path, "w", encoding="utf-8") as fh:
        json.dump(msg_out, fh, ensure_ascii=False, indent=2)
    with open(scores_path, "w", encoding="utf-8") as fh:
        json.dump(scores_out, fh, ensure_ascii=False, indent=2)

    n_msgs = sum(len(v.get("quantitative", [])) + len(v.get("qualitative", []))
                 for sets in msg_out.values() for v in sets.values())
    print(f"Wrote {msg_path} ({n_msgs} shared messages across {len(msg_out)} tasks)")
    print(f"Wrote {scores_path} (period scores per component)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True, choices=["initial", "iq", "main"],
                    help="Which pilot the CSV came FROM (the next pilot reads this file).")
    ap.add_argument("--csv", required=True, type=Path, help="oTree all-apps wide CSV export.")
    args = ap.parse_args()
    build(args.pilot, args.csv)


if __name__ == "__main__":
    main()
