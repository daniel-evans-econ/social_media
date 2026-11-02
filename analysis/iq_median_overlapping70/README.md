# IQ feedback from overlapping lower/upper 70% pools

Generated 2 November 2026 with:

    python tools/simulate_iq9_halves.py --medians --pool-percent 70

This is an analysis-only counterfactual; the live survey still samples within halves.
Own scores are the pilot task medians: numerical reasoning 9/15, abstract reasoning
7/15, working memory 8/15. All other methods match the
[75% analysis](../iq_median_overlapping75/README.md).

The lower pool retains the first ceil(0.70*N) people in the full reference pool's
score ranking; the upper pool retains the last ceil(0.70*N). Ranking uses the
survey's stable tie-break. With full pools of 100, 56 and 77, the comparison pools
contain 70, 40 and 54 respondents, respectively, before quantitative eligibility
filtering. Intersections contain 40, 24 and 31 respondents. Small differences from
70% and 40% reflect rounding to whole respondents.

For quantitative participants, each pool is then restricted to respondents with
all three numerical reports, including unsent reports. Qualitative participants
use all historical conditions in each pool. Boundaries and own median scores are
computed before this restriction.

Each panel uses one million simulations of 20 draws with replacement, checked
against exact multinomial probabilities and 100 identity-level draws. The live IQ
scoring function supplies the calibration, tie weighting, clipping and rounding.
Plot bars show simulations; means, SDs, medians and central 95% bounds are exact.
Intervals describe feedback, not uncertainty about true IQ.

The two PNGs show lower 70% on the left and upper 70% on the right, with matching
axes. Dashed lines mark calibrated full-sample IQ. `summary.csv` contains statistics
and pool counts, `distributions.csv` contains probabilities, and `results.json`
contains full results, seed and source hashes. All outputs are aggregate-only.
