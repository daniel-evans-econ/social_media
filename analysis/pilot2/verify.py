"""Audit a generated report against the historical deck or current accounting identities."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def verify(folder, historical):
    def read(stem):
        return pd.read_csv(folder/(stem+".csv"))
    if (folder/"18_gap_decomposition.csv").exists():
        gap=read("18_gap_decomposition").iloc[0]
        assert np.isclose(gap.selection+gap.misreporting,gap.total_gap,equal_nan=True)
    sample=read("02_sample")
    if historical:
        assert (sample.iloc[0][["started","finished","social_decisions"]].tolist()==[124,100,600])
        assert read("14_quantitative_exact_over_under").reports.tolist()==[279,8,13]
        assert np.isclose(gap.all_truth,2.47) and np.isclose(gap.posted,2.642857142857143)
        assert np.allclose(read("25_median_person_rank").percentile,[52,56])
        assert round(read("06_total_correct").iloc[0]["mean"],2)==22.61
        assert round(read("09_initial_iq_calibration").iloc[0].mean_shortfall,1)==9.1
    else:
        assert (sample.visited>=sample.confirmed_selfie).all()
        assert (sample.entered_id>=sample.scored_any).all()
        assert (sample.scored_any>=sample.finished).all()
        if (folder/"observed_reactions_per_historical_message.csv").exists():
            tally=read("observed_reactions_per_historical_message")
            assert (tally[["none","like","love","care","haha","sad","angry"]].sum(axis=1)==tally.eligible_views).all()
            try:
                opportunities=read("reaction_opportunities")
            except pd.errors.EmptyDataError:
                opportunities=pd.DataFrame(columns=["outcome","observations"])
            observed=opportunities.loc[opportunities.outcome.eq("reacted"),"observations"].sum()
            assert tally.eligible_views.sum()==observed, "Eligible exposure with missing historical message ID"
    print("Verification passed.")


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folder",type=Path)
    cli.add_argument("--historical",action="store_true")
    args=cli.parse_args()
    verify(args.folder,args.historical)
