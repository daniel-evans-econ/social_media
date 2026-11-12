"""Package the analysis, calibration and historical coding rules for offline use."""
import argparse
from pathlib import Path
from pprint import pformat
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd
from data import ROOT
from replicate import comparison_row, historical, literal


def bundle(archive, source):
    here=Path(__file__).resolve().parent
    prefix="analysis/pilot2/"
    with ZipFile(archive,"x",compression=ZIP_DEFLATED) as dest:
        for name in ("README.md","requirements.txt","run.py","verify.py","replicate.py",
                     "report.py","features.py","expanded.py","treatment_plots.py","data.py"):
            dest.write(here/name,prefix+name)
        calibration="social_media/data/iq_distribution_initial.json"
        dest.write(ROOT/calibration,calibration)
        for filename,keys in [("notes_coding.py",["CATS","SLIDE_LABELS","POS_LEX","NEG_LEX"]),
                              ("make_slide_figures.py",["REASONS","MOTIVE_PAT"])]:
            rules="\n\n".join(f"{k} = {pformat(literal(source/filename,k),width=100)}" for k in keys)
            dest.writestr(prefix+"legacy_rules/"+filename,rules+"\n")
        a,q,b,_=historical(source)
        benchmarks=[comparison_row(label,a,q,b,cap) for label,cap in [
            ("July: deck sample, all three periods",False),("July: first two periods, finishers",True)]]
        dest.writestr(prefix+"legacy_rules/july_benchmarks.csv",pd.DataFrame(benchmarks).to_csv(index=False))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("archive",type=Path)
    cli.add_argument("--source",type=Path,default=Path.home()/"Desktop/research/social_media/pilot_1_analysis")
    params=cli.parse_args()
    bundle(params.archive,params.source)
