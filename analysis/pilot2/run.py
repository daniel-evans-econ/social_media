"""Local replication and treatment analysis. See README.md for commands."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data import load
from features import current
from replicate import comparison_row, historical, legacy
from report import Report


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    mode=cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--export",type=Path,help="one directory containing the original three session CSVs")
    mode.add_argument("--manifest",type=Path,help="JSON list of nonoverlapping cohort/slot ranges")
    mode.add_argument("--pilot1",action="store_true",help="repeat deck analyses on the original pilot's tidy files")
    local_legacy=Path.home()/"Desktop/research/social_media/pilot_1_analysis"
    bundle_rules=Path(__file__).parent/"legacy_rules"
    cli.add_argument("--legacy-dir",type=Path,default=local_legacy if local_legacy.is_dir() else bundle_rules)
    cli.add_argument("--out",required=True,type=Path,help="new local output directory")
    cli.add_argument("--min-slot",type=int,default=1)
    cli.add_argument("--max-slot",type=int)
    cli.add_argument("--exclude-code",action="append",default=[],help="excluded test or adjudicated repeat code")
    cli.add_argument("--cohort",choices=["no_feed","feed"],default="no_feed")
    args=cli.parse_args()
    for file in ("notes_coding.py","make_slide_figures.py"):
        if not (args.legacy_dir/file).is_file():
            cli.error("Use --legacy-dir to point to the original pilot analysis source folder.")
    if args.pilot1:
        if not (args.legacy_dir/"data/participant_level.csv").is_file():
            cli.error("--pilot1 requires --legacy-dir pointing to the original July scripts and private tidy data.")
        a,q,b,p=historical(args.legacy_dir)
        rep=Report(args.out)
        rep.table("02_sample",[dict(started=len(a),finished=int(a.finished.sum()),
                  social_decisions=int((b.finished & b.is_social & b.shared.notna()).sum()))])
        legacy(rep,a,q,b,p,args.legacy_dir,45)
        rep.finish("July pilot: replication of August slide analyses")
        return
    entries=json.loads(args.manifest.read_text(encoding="utf-8-sig")) if args.manifest else [
        dict(folder=str(args.export),min_slot=args.min_slot,max_slot=args.max_slot,
             exclude_codes=args.exclude_code,cohort=args.cohort)]
    seen,ids=set(),set()
    collected=[]
    flow=[]
    provenance=[]
    for entry in entries:
        folder=Path(entry["folder"])
        if args.manifest and not folder.is_absolute():
            folder=args.manifest.parent/folder
        cohort=entry["cohort"]
        if cohort not in ("no_feed","feed"):
            cli.error("Expected a 'no_feed' or 'feed' recruitment wave")
        counts,frames,keys,identifiers=load(folder,entry.get("min_slot",1),entry.get("exclude_codes",[]),entry.get("max_slot"))
        if seen & keys or ids & identifiers:
            raise ValueError("Overlapping participants across snapshots; specify disjoint slot ranges")
        seen.update(keys)
        ids.update(identifiers)
        a,q,b,p,belief,wta,feed=frames
        a["cohort"]=cohort
        counts.update(cohort=cohort,scored_any=q.pid.nunique() if len(q) else 0,
                      finished=int(a.finished.sum()) if len(a) else 0)
        collected.append(frames)
        flow.append(counts)
        provenance.append(dict(snapshot=folder.name,cohort=cohort,min_slot=entry.get("min_slot",1),
                               max_slot=entry.get("max_slot"),explicit_exclusions=len(entry.get("exclude_codes",[]))))
    if not collected:
        cli.error("Empty manifest")
    a,q,b,p,belief,wta,feed=[pd.concat(dfs,ignore_index=True) for dfs in zip(*collected)]
    rep=Report(args.out)
    rep.table("00_inputs",provenance)
    rep.table("02_sample",flow,"Visited slots after explicit test exclusions. Assignment analyses start at Prolific ID entry.")
    if len(a) and len(p):
        base=p[p.period.le(2)].pivot(index="pid",columns="period",values="full_iq").reindex(columns=[1,2])
        a=a.merge(np.floor(base.mean(axis=1,skipna=False)+.5).rename("benchmark"),on="pid",how="left")
        if len(b):
            rep.summary("02_social_decisions",b[b.pid.isin(a.loc[a.finished.eq(1),"pid"]) & b.social.eq(1)],
                        ["condition","period"],["shared"])
            legacy(rep,a,q,b,p,args.legacy_dir,30)
            mandatory=Report(rep.out/"mandatory-periods")
            legacy(mandatory,a,q[q.period.le(2)],b[b.period.le(2)],p[p.period.le(2)],args.legacy_dir,30)
            mandatory.finish("Current pilot: slide analyses restricted to mandatory periods")
            comparison=[comparison_row("Current: mandatory periods, finishers",a,q,b,True)]
            if (args.legacy_dir/"data/participant_level.csv").is_file():
                old_a,old_q,old_b,_=historical(args.legacy_dir)
                comparison[:0]=[comparison_row(label,old_a,old_q,old_b,cap)
                    for label,cap in [("July: deck sample, all three periods",False),
                                      ("July: first two periods, finishers",True)]]
            elif (args.legacy_dir/"july_benchmarks.csv").is_file():
                comparison[:0]=pd.read_csv(args.legacy_dir/"july_benchmarks.csv").to_dict("records")
            rep.table("pilot_comparison",comparison,"Descriptive comparisons across different cohorts, items and designs.")
        current(rep,a,q,b,p,belief,wta,feed)
    rep.finish("Current pilot: replication and treatment contrasts")
    print(f"Local report: {args.out.resolve() / 'index.html'}")


if __name__=="__main__":
    main()
