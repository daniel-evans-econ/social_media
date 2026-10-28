# Whole-stratum message sampling: rerun on 28 October 2026

The local survey now draws messages separately from all eligible messages in
the assigned performance stratum. The 20-person IQ draw and end-of-survey
averages are unchanged. The survey still uses quintiles; terciles and halves
are counterfactuals. These code changes are not deployed.

## Complete results

- [Complete 95% tables (12-page PDF)](../../output/pdf/iq-feedback-95-intervals.pdf):
  every own score 0–15, three tasks, two message formats, pooled over each
  partition and separately within every quintile, tercile and half. There are
  1,248 intervals in total. The first three pages are pooled results; the next
  nine hold the assigned stratum fixed. Stratum 1 is the lowest-performing.
- `comparison.json` includes all exact IQ probability distributions, means,
  SDs, interval endpoints and the new message-availability results.
- `*_all_scores_pooled.png` contains the three full pooled tables.
- `*_conditional.png` contains the nine stratum-specific tables.
- `*_95pct_score_grid.png` contains compact tables at 0, 3, 6, 9, 12, 15 correct.
- `message_availability_details.json` adds task-specific availability checks.

The intervals are discrete 2.5th–97.5th percentile ranges for displayed IQ,
not confidence intervals for underlying ability. Every interval contains at
least 95% probability; some contain more because IQ is discrete. A point
interval is a valid result. The complete distributions and all endpoints
exactly equal the preceding calculation in `../strata_comparison/`.

## Current procedure

1. For each task, sort the historical linked reference respondents by actual
   number correct out of 15. Resolve score ties with a fixed hash. Split this
   full-domain pool into five approximately equal groups (three or two only
   in these counterfactuals).
2. Independently for each participant-period, choose a performance stratum
   uniformly. This is unrelated to the current participant's own performance.
3. For quantitative participants, restrict the selected stratum to historical
   respondents who provided all three numerical block reports, whether or not
   they sent them. For qualitative participants, retain all historical message
   conditions, including control. Draw 20 observations with replacement.
   Repeated respondents retain repeated statistical weight.
4. Given the participant's own score, calculate p=(below + 0.5*tied)/20 in
   those draws. Clip p to [0.025, 0.975] and map it to 100+15*Phi^-1(p).
5. Compute the analogous empirical-percentile IQ against the full task IQ
   reference pool (using that pool's own clipping bounds 0.5/n and 1-0.5/n).
   Subtract this full-pool value from the comparison-draw value, round the
   difference to the nearest integer (halves away from zero), and add it to
   the calibrated full sample IQ lookup for that score. There is no additional
   cap or mean correction. The calibrated lookup and full-pool percentile IQ
   are different quantities. Therefore the average feedback need not equal
   the calibrated full sample IQ.
6. Separately collect the sent, matching-format messages from the entire
   assigned full-domain stratum. Retain the existing qualitative content
   filters. Uniformly shuffle distinct sender/content pairs, selecting unseen
   pairs as blocks are encountered. An author need not occur in the 20 draws.
   Different messages from the same author are allowed; identical sender/content
   pairs cannot repeat across blocks or periods. Identical text/number from
   different authors remains eligible. Existing cached exposures are preserved.
7. End-of-survey group statistics still concern the 20 sampled observations,
   not the particular messages displayed. Quantitative reported averages are
   the mean sent numerical block report multiplied by three; actual averages
   are the mean actual /15 scores of all 20 draws. Qualitative figures compare
   the happy-emoji share among sent versus all composed qualitative messages.

The message change keeps IQ distributions fixed while expanding message
availability. It also means displayed messages and end statistics refer to
the same performance stratum, but not necessarily identical respondents.
Historical reference items differ from the current fixed question sets.

## Message availability after the change

All three messages were available in both social periods for **100% of the
2,000 simulated profiles per format/design** under terciles and halves.
That is a simulation result, not a guarantee for every possible history.

With quintiles, the first / second social-period rates were:

- Quantitative: 93.10% / 92.65%.
- Qualitative: 93.85% / 92.95%.

Two abstract-reasoning quintiles contain only one distinct eligible message:
quantitative quintile 2 and qualitative quintile 5. The current rule does not
fabricate messages or borrow messages from another stratum.

## Validation and reproduction

Reran 100,000 comparison groups per task/format/stratum: six million groups
across the three designs. IQ probabilities were also calculated exactly from
all 231 below/tied/above count states for N=20. Maximum absolute CDF discrepancy
against Monte Carlo was 0.004564. Source hashes match the preceding analysis;
all conditional and pooled IQ distributions exactly reproduce it.

Message checks use 2,000 matched profiles per format/design, random task order,
social/control/social and completion of all tasks. They verify stratum
membership, no repeated sender/content pairs, and unchanged IQ draws. Focused
survey tests passed for 400 participant plans / 1,200 groups, including repeat
senders, duplicate messages, cached refreshes, numerical averages and IQ helpers.

Run `tools/simulate_stratified_feedback.py --strata 5 --output
analysis/stratum_message_sampling/quintiles`, and analogously 3/terciles and
2/halves. Then run `tools/compare_feedback_strata.py --output
analysis/stratum_message_sampling` and `tools/report_stratum_message_sampling.py`.
The additional `tools/check_repeated_sender_availability.py` command checks
availability by task using the current selector. The encrypted reference key
must already be configured locally; it is never included in these outputs.

The permanent revisit item to reinstate no repeated sender after the reference
sample grows is in `../../LINKED_PILOT_DESIGN.md`.
