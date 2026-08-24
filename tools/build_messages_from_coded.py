"""Build the pilot-2 (IQ pilot) received-message pool from the CODED pilot-1 notes.

This is the canonical builder for ``social_media/data/messages_initial.json`` and
supersedes the message export in ``export_pilot_data.py`` (which only filtered on task
vocabulary). Qualitative messages are drawn from the analysis project's
``notes_coded.csv`` and kept only when they can safely travel to a fresh participant:

    task_specific == 0   (does not name content tied to one task type)
    time_specific == 0   (does not reference an earlier/later block, or a trend)
    nonsense      == 0   (not keyboard-mash)
    sent          == 1   (the sender actually chose to share it)

Quantitative messages are just a number correct (0-5); no content filter applies, so
they are taken from the in-repo ``social_media/data/quant_reports_initial.csv`` (already
restricted to shared quantitative-arm reports). If that file is absent the builder falls
back to the analysis project's ``block_level.csv``. The raw emoji is not stored in
notes_coded.csv, so it is joined back from block_level.csv on (pcode, block_global).

Usage:
    python tools/build_messages_from_coded.py
    python tools/build_messages_from_coded.py --analysis-dir "D:/path/to/pilot_1_analysis/data"

Output preserves the schema the experiment expects:
    { task: { set_id: { "quantitative": [{name, number}],
                        "qualitative":  [{name, emoji, sentence}] } } }
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "social_media" / "data"
DEFAULT_ANALYSIS_DIR = Path(
    r"C:\Users\Evans\Desktop\research\social_media\pilot_1_analysis\data"
)

# Human task label used in notes_coded.csv -> task key used by the experiment.
TASK_KEY = {
    "Numerical reasoning": "sequences",
    "Spatial reasoning": "shape_rotation",
    "Working memory": "working_memory",
    "Abstract reasoning": "ravens",
}


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on", "1.0")


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _read_csv(path: Path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def build(analysis_dir: Path):
    block_rows = _read_csv(analysis_dir / "block_level.csv")
    note_rows = _read_csv(analysis_dir / "notes_coded.csv")

    # Quantitative arm lives in-repo as a self-contained repository (already filtered to
    # shared reports); fall back to block_level.csv only if the file is missing.
    quant_path = DATA_DIR / "quant_reports_initial.csv"
    if quant_path.exists():
        quant_rows = _read_csv(quant_path)
        quant_prefiltered = True
    else:
        quant_rows = block_rows
        quant_prefiltered = False

    # (pcode, block_global) -> raw emoji, so the coded notes can recover their glyph.
    emoji_by_block = {}
    for r in block_rows:
        if r.get("condition") == "qualitative_social":
            emoji_by_block[(r.get("pcode"), r.get("block_global"))] = (
                (r.get("report_emoji") or "").strip()
            )

    messages: dict = defaultdict(
        lambda: defaultdict(lambda: {"quantitative": [], "qualitative": []})
    )

    # Quantitative arm: shared numeric reports (content filters do not apply).
    n_quant = 0
    for r in quant_rows:
        if not quant_prefiltered and (
            r.get("condition") != "quantitative_social" or not _truthy(r.get("shared"))
        ):
            continue
        task = r.get("task")
        set_id = r.get("set_id")
        num = _int(r.get("report_number"))
        if not task or not set_id or num is None:
            continue
        messages[task][set_id]["quantitative"].append(
            {"name": (r.get("username") or "").strip(), "number": num}
        )
        n_quant += 1

    # Qualitative arm: coded notes that pass all three content filters and were shared.
    n_qual = 0
    for r in note_rows:
        if not (_truthy(r.get("sent"))
                and not _truthy(r.get("task_specific"))
                and not _truthy(r.get("time_specific"))
                and not _truthy(r.get("nonsense"))):
            continue
        task = TASK_KEY.get((r.get("task_label") or "").strip())
        set_id = r.get("set_id")
        sentence = (r.get("msg") or "").strip()
        if not task or not set_id or not sentence:
            continue
        emoji = emoji_by_block.get((r.get("pcode"), r.get("block_global")), "")
        messages[task][set_id]["qualitative"].append(
            {"name": (r.get("username") or "").strip(), "emoji": emoji, "sentence": sentence}
        )
        n_qual += 1

    # Plain dicts, pruning empty pools/sets.
    out = {
        "_README": (
            "Portable pilot-1 messages for the IQ pilot. Built by "
            "tools/build_messages_from_coded.py: qualitative entries come from "
            "data/notes_coded.csv (kept only when task_specific==time_specific=="
            "nonsense==0 and sent==1); quantitative entries come from "
            "data/quant_reports_initial.csv (shared numeric reports)."
        )
    }
    for task, sets in messages.items():
        task_out = {}
        for set_id, pools in sets.items():
            pruned = {k: v for k, v in pools.items() if v}
            if pruned:
                task_out[set_id] = pruned
        if task_out:
            out[task] = task_out

    return out, n_quant, n_qual


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR,
                    help="pilot_1_analysis/data dir holding notes_coded.csv + block_level.csv")
    ap.add_argument("--out", type=Path, default=DATA_DIR / "messages_initial.json")
    args = ap.parse_args()

    out, n_quant, n_qual = build(args.analysis_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    tasks = [k for k in out if k != "_README"]
    print(f"wrote {args.out}")
    print(f"  {n_quant} quantitative + {n_qual} qualitative messages across {len(tasks)} tasks")
    print(f"  tasks: {tasks}")


if __name__ == "__main__":
    main()
