# IQ feedback at each task's pilot median

Generated 2 November 2026 with:

    python tools/simulate_iq9_halves.py --medians

The participant scores 9/15 in numerical reasoning, 7/15 in abstract reasoning,
and 8/15 in working memory. These are the medians of all historical respondents
in the linked task-specific reference pools, before splitting into halves or
filtering numerical reporters. The same own score is used for both message formats.

All other assumptions match the [9/15 analysis](../iq9_halves/README.md):
20 comparison respondents drawn with replacement within the assigned performance
half; the current quantitative/qualitative eligibility rules; the live survey's
IQ calculation; one million simulations per task, format and half. Each simulated
distribution is checked against exact multinomial probabilities and ordinary
live comparison-group draws. Means, SDs, medians and central 95% bounds are exact;
bars show simulated frequencies. The 95% bounds describe feedback distributions,
not confidence intervals for true IQ.

Each PNG has lower-half comparisons on the left and upper-half comparisons on
the right. The dashed line is the calibrated full-sample IQ for the task's own
score; it need not equal 100 because the calibrated lookup is distinct from the
empirical percentile transformation used to calculate the random adjustment.

`summary.csv` contains summary statistics and eligible-pool counts.
`distributions.csv` contains probabilities by reported IQ.
`results.json` contains all results, source hashes and the reproducible seed.
No individual identities, messages, images or private reference records are exported.
