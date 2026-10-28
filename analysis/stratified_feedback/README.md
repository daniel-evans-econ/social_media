# Stratified comparison-group simulations — 27 October 2026

These results describe the current IQ pilot's implemented sampling and feedback
rules. They do not change the experiment or simulate an idealized normal reference
population. The source is the encrypted linked initial-pilot reference file, the
full initial-pilot IQ-score pools, and the calibrated score-to-IQ lookup tables.
File hashes and the seed are recorded in `results.json`. Only aggregate results
are exported; no usernames, individual reference records or selfies are included.

## Main findings

- At full sample IQ 100–101, displayed IQ has an overall SD of approximately
  25.7–26.8 points when all five quintiles are equally likely. The equal-tail 95%
  ranges are 69–127 for working memory and 69–128 for the other two tasks.
- More than 99% of the variance at these focal scores comes from which quintile
  is selected, rather than sampling variation within that quintile. A participant
  outperforming everyone in a low quintile is at the clipped upper percentile;
  the same participant falling below everyone in a high quintile is at the lower
  endpoint. Many conditional distributions therefore are single point masses.
  These are feedback-distribution intervals, not confidence intervals for true IQ.
- Effects depend strongly on own number correct: the same quintile assignment
  does not produce a constant IQ shock across scores. See the complete 0–15 score
  curves and the variance decomposition near full sample IQ 85, 100 and 115.
- Quantitative eligible pools have only 2–10 people per task/quintile. Twenty
  draws are not twenty distinct people. In the smallest pools, the no-repeat-sender
  rule makes three incoming messages impossible, regardless of replacement draws.
- In 2,000 simulated profiles per format, three messages were available in the
  first social period for 75.45% of quantitative and 54.20% of qualitative profiles.
  For a second social period these rates fell to 67.00% and 50.20%, respectively.
  This scenario assumes everyone plays two social periods, with different tasks
  and a control period between them; it is not a prediction of optional-task uptake.
- The quantitative correction share can still exceed 100% or become negative
  when selection and misreporting offset. For example, roughly 95.35% of nonzero
  gaps in numerical-reasoning quintile 2 have an out-of-range selection share.
  This is the current signed decomposition, not a coding fix or bounded statistic.

The assigned quintile changes both IQ feedback and which peer messages can be
shown. Those channels are jointly manipulated, so the quintile contrast alone
does not isolate a pure effect of IQ feedback. The format-specific eligible pools
also make quantitative and qualitative reference-group exposures differ. These
are design considerations to revisit, not changes made by this analysis.

## Method

For each of three tasks and two message formats, use the exact full-domain
quintile boundaries and hashed tie-break from `peer_groups.group_for`. Quantitative
eligibility requires three numerical reports, including unsent reports. Qualitative
eligibility is the full mixed-format stratum. Simulate 100,000 independent groups
of 20 draws with replacement for each quintile: 30 cells, 3,000,000 groups total.
Counts of each sampled identity give the same distribution as drawing people
individually and preserve repeated-draw weights in averages.

For every own score from 0 to 15, additionally enumerate the exact multinomial
distribution of counts below, tied and above that score (231 possible count states
at N=20). Compute percentile `(below + 0.5 * tied) / 20`, clip it to [0.025, 0.975],
and map it to `100 + 15 * inverse_normal(percentile)`. Subtract the corresponding
empirical-percentile IQ from the full IQ reference pool, round that difference to
an integer with halves away from zero, and add it to the calibrated full sample
IQ. There is no additional IQ cap. Full sample IQ refers to the calibrated lookup
table, not the full-pool percentile conversion. Pools for that subtraction contain
105 numerical, 82 working-memory and 60 abstract-reasoning observations; linked
group-eligible full pools contain 100, 77 and 56 respectively.

Exact conditional distributions and equally weighted five-quintile mixtures are
reported for all 16 own scores. Raw-offset and rounded-display moments are both
stored. `within_quintile_variance` is the mean of the five conditional variances;
`between_quintile_variance` is the variance of their conditional means. Their sum
equals total variance. Exact distributions were checked against identity-level
Monte Carlo near full sample IQ 85, 100 and 115; maximum CDF error was 0.003412.

For report statistics, quantitative reported averages remain three times the
sent-block mean, while truth is the actual /15 score averaged over all 20 draws.
Decompose the gap into actual sent-block performance minus actual group performance
(selection), and reported minus actual sent-block performance (misreporting).
Missing reported averages are not zero. Qualitative calculations remain happy
emoji shares among sent versus all composed qualitative messages; the proposed
private-satisfaction target is deferred. Mixed-format qualitative pools mean this
emoji statistic covers the qualitative-message subset within the comparison group.

Per-cell message diagnostics count distinct eligible sender usernames in each
group. A separate 2,000-profile simulation per format calls the actual `message_for`
function for two social periods, retaining the cross-period no-repeat rule.
Historical messages retain the current portability filtering. Historical task
items differ from the current fixed item set. Results are conditional on these
finite pilot pools and contain no uncertainty about sampling a new pilot population.

## Files and reproduction

- [Numerical reasoning](sequences_iq100.png), [working memory](working_memory_iq100.png),
  [abstract reasoning](ravens_iq100.png): exact
  conditional distributions near IQ 100, five quintiles by two formats.
- [Mean adjustment by own score](mean_adjustment_by_score.png): all own scores.
- [Sources of variance](variance_sources.png): within/between quintile variance near IQ 85, 100, 115.
- `results.json`: aggregate distributions, moments, message availability, report
  diagnostics, reproducibility settings and source hashes.

Run `python tools/simulate_stratified_feedback.py` from the repository, with
`PEER_REFERENCE_KEY` available through `.env`. Requires numpy, scipy, matplotlib
and the existing survey dependencies. It does not connect to or alter the study
database. Analysis seed: 20261027. No survey settings were changed by the run.
