# Actual-pilot noisy IQ feedback

These replace the idealized illustration in ../iq100_feedback for the user's actual-data request. Source: social_media/data/iq_scores_initial.json and iq_distribution_initial.json, the reference pools and calibrated score-to-IQ tables used by EXPERIMENT_PILOT=iq. Data hashes are included.

## Full sample IQ selection

In the plots, full sample IQ means the calibrated IQ before comparison-group noise, not the uncalibrated IQ obtained directly from the full pool's empirical percentile. Number correct identifies the task score corresponding to that calibrated IQ. CSV field names baseline_iq and raw_score are retained for compatibility.

Working memory: 8/15 correct, calibrated IQ 100, N=82 (41 below, 9 tied, 32 above). Abstract reasoning: 7/15, calibrated IQ 101, N=60 (31 below, 5 tied, 24 above). Numerical reasoning: 9/15, calibrated IQ 101, N=105 (52 below, 14 tied, 39 above). Only working memory has an exact calibrated IQ of 100. The other tasks use the nearest available IQ, without interpolation or recentering. The focal participant is treated as a new participant compared with these full reference pools; no reference observation is removed. Spatial reasoning is omitted because it is not one of the three tasks in the current IQ pilot.

## Calculation

1,000,000 independent comparison groups per task, size and sampling method. Mid-P percentile is (number below + 0.5 * number tied)/n, clipped to [0.5/n,1-0.5/n]. The sampled percentile is converted to 100+15*inverse_normal(p). Subtract the analogous percentile IQ for the entire actual pilot pool, round the resulting offset to the nearest integer (halves away from zero), and add it to the calibrated baseline IQ. This follows _percentile_iq, iq_noise_offset and estimate_iq_for_player. There is no additional hard cap. A baseline IQ of 100 need not be the empirical 50th percentile because the calibrated lookup table and empirical distribution differ.

The survey now samples without replacement (updated 17 September 2026); both sampling rules are shown here for comparison. Below/tied/above counts are sufficient statistics: draws from their multinomial or multivariate hypergeometric distribution are exactly equivalent to resampling individual records from the actual pilot pool for this feedback calculation. All ties and observed frequencies are retained. The observations are not forced into a 100-person pool. All target sizes are shown for all tasks, including 100. With replacement, exactly the target number of draws is used, even if there are fewer reference people. Without replacement, the effective size is min(target size, pool size); this is an explicit whole-pool convention, not a draw of 100 distinct people from a smaller pool. The CSVs include both target and effective sizes. Whole-pool draws produce a point mass at the calibrated baseline. At target 100, working memory uses all 82 people and abstract reasoning all 60 without replacement. Numerical reasoning still draws 100 of 105.

This is an analysis extension beyond the live implementation: iq_noise_offset currently returns zero noise whenever the requested size exceeds the pool, including with replacement. Thus the new with-replacement n>pool panels illustrate the sampling design, not that safeguard. The survey has not been changed.

## Files and verification

pilot_nNNN.png compares tasks and sampling methods at each size. working_memory_*.png gives the exact IQ-100 case over all target sizes. The other task overviews show IQ 101 and are labelled accordingly. pilot_noise_by_group_size.png summarizes variability, with an additional full-pool anchor at 82 for working memory so the curve reaches zero at the correct size. CSVs retain empirical and exact values; intervals are discrete equal-tail 95% quantiles and may cover more than 95%. Exact means are reported rather than assuming they equal baseline: the nonlinear transform, endpoint handling and rounding may shift the expected value.

Validation checks every attainable percentile against the pure helper extracted directly from survey source, verifies exact probability mass, checks all empirical CDFs against exact probabilities within 0.003, and verifies deterministic feedback at the baseline when sampling the whole pool without replacement. Root random seed: 20260916, separate streams by task/size/method. Run python tools/simulate_pilot_iq_feedback.py (numpy, scipy, matplotlib). No survey configuration or database was changed.
