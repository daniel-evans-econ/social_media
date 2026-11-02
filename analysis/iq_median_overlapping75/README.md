# IQ feedback from overlapping lower/upper 75% pools

Generated 2 November 2026 with:

    python tools/simulate_iq9_halves.py --medians --pool-percent 75

This is an analysis-only counterfactual; the live survey still samples within halves.
Own scores remain at the task-specific pilot medians: numerical reasoning 9/15,
abstract reasoning 7/15, working memory 8/15. One million simulations are run for
each task, message format and pool, with 20 comparison draws with replacement.

## Pool construction

Sort the full linked reference pool by score, using the survey's existing stable
tie-break. The lower pool retains the first ceil(0.75*N) people; the upper pool
retains the last ceil(0.75*N). This gives equally sized pools, with slight upward
rounding when N is not divisible by four. The full pools contain 100, 56 and 77
respondents, respectively, giving comparison pools of 75, 42 and 58 before the
message-format eligibility restriction. Their intersections contain 50, 28 and
39 respondents. At tied cutoffs, tied respondents may appear on different sides.

For quantitative participants, restrict each pool to respondents who provided all
three numerical reports, including unsent reports, matching the current survey's
eligibility rule. For qualitative participants, retain all historical conditions.
Pool boundaries are set before this restriction. Consequently the overlap among
eligible quantitative respondents need not be exactly 50% of all quantitative
respondents.

## Calculation and verification

The IQ scoring function is unchanged: calibrated full-sample lookup plus the
sample-versus-full-pool percentile IQ difference, with half-weight ties, endpoint
clipping and survey rounding. All 231 attainable below/tied/above count states
are scored by the live function. Exact multinomial probabilities provide means,
SDs, medians and central 95% bounds; PNG bars show Monte Carlo frequencies.

The Monte Carlo CDF must agree with the exact CDF within 0.003 in each cell. A
further 100 identity-level draws per cell validate the count-based calculation
against live IQ scoring. These counterfactual draws deliberately bypass the live
half-selection function, while using its ordering and eligibility rules.

## Files

- Two PNGs: quantitative and qualitative, with lower 75% left and upper 75% right.
  Dashed lines mark calibrated full-sample IQ. Axes are identical across these
  two figures; the probability axis is rescaled relative to the earlier halves
  figures so the distributions are visible.
- `summary.csv`: summary statistics and pool composition.
- `distributions.csv`: exact and simulated probabilities by displayed IQ.
- `results.json`: all results, seed and source hashes.

All outputs are aggregate-only. The 95% bounds describe the distribution of
feedback, not uncertainty about a person's true IQ.
