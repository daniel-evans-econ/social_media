# Quintiles, terciles and halves — actual pilot data

Completed 27 October 2026. Analysis only: the survey still uses quintiles.

These are archived calculations. The latest whole-stratum message-sampling
rerun is in `../stratum_message_sampling/`; its IQ distributions are identical.

## Results near full sample IQ 100

Across the three tasks and two message formats, displayed IQ standard deviations
are 25.69–26.75 points with quintiles, 23.99–24.65 with terciles, and 22.15–25.78
with halves. These are modest reductions; wider strata do not remove large IQ
shifts. Halves do not improve every comparison: abstract reasoning in the
qualitative arm has SD 25.78 with halves, compared with 24.29 with terciles.

For the quantitative arm, SDs in numerical / working-memory / abstract reasoning
are respectively:

- Quintiles: 26.49 / 26.47 / 26.75 IQ points.
- Terciles: 24.16 / 24.26 / 24.65 IQ points.
- Halves: 23.20 / 23.59 / 22.15 IQ points.

The focal own scores are 9/15 in numerical reasoning (full sample IQ 101), 8/15
in working memory (IQ 100), and 7/15 in abstract reasoning (IQ 101). These are the
nearest available calibrated values to 100, not interpolated scores.

The 95% feedback ranges are unchanged with terciles: 69–128 for numerical and
abstract reasoning, and 69–127 for working memory. With halves they narrow in
some cells, but remain wide: quantitative numerical 69–128, working memory
73–127, abstract reasoning 77–128; qualitative numerical 74–128, working memory
73–127, abstract reasoning 69–128. These are equal-tail distributions of feedback,
not confidence intervals for true IQ.

Why the limited improvement? A person near the overall median can still outperform
nearly everyone in the lower stratum, and fall below nearly everyone in the upper
stratum. Terciles retain a central group, making a three-cluster distribution.
Halves generally create two widely separated clusters. Even under halves,
96.7–98.9% of the variance near IQ 100 is between assigned strata. Ties, integer
cut points and format-specific eligibility explain why the comparison is not
uniform across tasks.

Nor are means guaranteed to equal full sample IQ: for example, quantitative
abstract-reasoning feedback averages 105.98 under halves, versus full sample IQ
101. The nonlinear transform, clipping and calibration adjustment remain unchanged.

At own IQ values nearest 85 and 115, larger strata reduce spread more noticeably.
Near 85 (available full sample IQs 82–85), SD ranges across cells are 10.04–14.94
for quintiles, 6.75–12.99 for terciles, and 5.61–12.00 for halves. Near 115
(available IQs 113–115), the corresponding ranges are 13.18–18.02, 9.79–15.00,
and 8.93–12.44. All own scores 0–15 are included in the results.

## Message availability: October 28 update

Different messages from the same sender are now allowed in the local linked
survey selector; repeated sender/content pairs remain forbidden across periods.
The IQ distributions and 95% ranges are unchanged. The original figures and
JSON files below retain the earlier no-repeat-sender baseline.

The repeated-sender check used the same 2,000
profiles per format/design, with matching task orders and group draws. Results
are saved separately in `repeated_sender_availability.json`. The shares receiving
all three messages in the first / second social period are:

- Quantitative quintiles: 93.10% / 92.85%.
- Quantitative terciles: 100.00% / 100.00%.
- Quantitative halves: 100.00% / 100.00%.
- Qualitative quintiles: 80.70% / 78.75%.
- Qualitative terciles: 88.25% / 88.70%.
- Qualitative halves: 90.20% / 91.80%.

100% is an observed simulation frequency, not a guarantee over every possible
reference draw. Qualitative groups still sample from mixed-format pools; some
draws contain fewer than three distinct sent messages that pass the historical
content filters. The rerun verifies membership and absence of repeated
sender/content pairs. No survey database or deployment is modified by it.

## Message availability: original no-repeat-sender baseline

Wider strata improve the supply of distinct senders substantially. In the first
social period, the percentage of profiles receiving all three messages is:

- Quantitative: 72.6% with quintiles, 99.9% with terciles, 100.0% with halves.
- Qualitative: 52.4%, 67.75%, 75.0%, respectively.

For the second social period, retaining the no-repeat-sender rule across periods:

- Quantitative: 69.95%, 97.95%, 99.95%.
- Qualitative: 50.15%, 61.5%, 73.05%.

These are Monte Carlo frequencies from 2,000 profiles per format and design.
100% means every simulated profile, not a guarantee. The scenario assumes a
social/control/social sequence with distinct tasks and completion of the optional
period; it does not model WTA uptake. Task orders and participant-code seeds are
matched across the three designs. This separate task-order random stream changes
the quintile Monte Carlo message percentages slightly relative to the preceding
report; the exact quintile IQ distributions are identical and verified as such.

Quantitative eligible pool sizes grow from 2–10 per quintile to 4–15 per tercile
and 6–20 per half. Qualitative pools include other historical message formats,
and portable-message filtering still applies, so their message shortages persist.

## Method and files

Only the number of strata changes. Sort the same full-domain linked reference
pool by actual performance with the same fixed hashed tie-break. Partition it
into 5, 3 or 2 approximately equal groups using integer boundaries; select each
group with equal probability. Within that group, retain quantitative-only
eligibility for quantitative participants and mixed-format eligibility for
qualitative participants, then draw N=20 with replacement. Do not redefine
boundaries using the quantitative subset. Repeated draws retain their weights.

All other rules are held fixed: mid-rank ties, percentile clipping, subtraction
of the full empirical-pool percentile IQ, calibrated full sample IQ, rounding,
reported/actual averages and message filters. Counterfactual group snapshots
exist only in simulated objects. The actual message selector and IQ helper are
used to validate the results. The survey code and live data are untouched.

100,000 groups per task × format × stratum: 6,000,000 groups across these three
designs. IQ distributions are calculated exactly by enumerating below/tied/above
counts and checked against Monte Carlo near IQ 85, 100 and 115. Maximum CDF
errors: quintiles 0.003412, terciles 0.004563, halves 0.004060. Source hashes match
across designs. The five-stratum exact output also reproduces the prior analysis.

The strata jointly change IQ feedback and eligible peer messages; these
simulations do not isolate a pure IQ-feedback effect. Historical tasks used
different items from the current fixed questions. No proposed satisfaction-based
qualitative target or new accuracy incentive is included.

Comparison figures:

- [IQ spread near 100](spread_comparison.png)
- [Quantitative IQ distributions](quantitative_distributions.png)
- [Qualitative IQ distributions](qualitative_distributions.png)
- [IQ spread across own scores](spread_by_own_score.png)
- [Message availability](message_availability.png)

Conditional distributions by task and stratum:

- Halves: [numerical](halves/sequences_iq100.png), [working memory](halves/working_memory_iq100.png), [abstract](halves/ravens_iq100.png).
- Terciles: [numerical](terciles/sequences_iq100.png), [working memory](terciles/working_memory_iq100.png), [abstract](terciles/ravens_iq100.png).
- Quintiles: [numerical](quintiles/sequences_iq100.png), [working memory](quintiles/working_memory_iq100.png), [abstract](quintiles/ravens_iq100.png).

Each subdirectory also contains mean-adjustment curves, variance decompositions
and complete aggregate `results.json`; `comparison.json` combines all designs,
including pooled distributions. There are no exported participant identities,
messages or images. Reproduce with `python tools/simulate_stratified_feedback.py
--strata K --output analysis/strata_comparison/NAME` for each K/NAME pair
(5/quintiles, 3/terciles, 2/halves), then `python tools/compare_feedback_strata.py`.
An authorized local `PEER_REFERENCE_KEY` is needed to read the encrypted source;
do not publish that key. No database access or deployment is involved.
