# Actual-pilot noisy IQ feedback

These replace the idealized illustration in ../iq100_feedback for the user's actual-data request. Source: social_media/data/iq_scores_initial.json and iq_distribution_initial.json, the reference pools and calibrated score-to-IQ tables used by EXPERIMENT_PILOT=iq. Data hashes are included.

## Baseline selection

Working memory: 8/15 correct, calibrated IQ 100, N=82 (41 below, 9 tied, 32 above). Abstract reasoning: 7/15, calibrated IQ 101, N=60 (31 below, 5 tied, 24 above). Numerical reasoning: 9/15, calibrated IQ 101, N=105 (52 below, 14 tied, 39 above). Only working memory has an exact calibrated IQ of 100. The other tasks use the nearest available IQ, without interpolation or recentering. The focal participant is treated as a new participant compared with these full reference pools; no reference observation is removed. Spatial reasoning is omitted because it is not one of the three tasks in the current IQ pilot.

## Calculation

1,000,000 independent comparison groups per task, size and sampling method. Mid-P percentile is (number below + 0.5 * number tied)/n, clipped to [0.5/n,1-0.5/n]. The sampled percentile is converted to 100+15*inverse_normal(p). Subtract the analogous percentile IQ for the entire actual pilot pool, round the resulting offset to the nearest integer (halves away from zero), and add it to the calibrated baseline IQ. This follows _percentile_iq, iq_noise_offset and estimate_iq_for_player. There is no additional hard cap. A baseline IQ of 100 need not be the empirical 50th percentile because the calibrated lookup table and empirical distribution differ.

Sampling with replacement follows the currently deployed mechanism. Without replacement is the alternative requested for comparison. Below/tied/above counts are sufficient statistics: draws from their multinomial or multivariate hypergeometric distribution are exactly equivalent to resampling individual records from the actual pilot pool for this feedback calculation. All ties and observed frequencies are retained. The observations are not forced into a 100-person pool. Sizes above a task's actual pool are excluded for both methods: the survey currently returns zero noise rather than sampling when its requested group size exceeds the pool.

## Files and verification

pilot_nNNN.png compares tasks and sampling methods at each size. working_memory_*.png gives the exact IQ-100 case over all eligible sizes. The other task overviews show IQ 101 and are labelled accordingly. pilot_noise_by_group_size.png summarizes variability. CSVs retain empirical and exact values; intervals are discrete equal-tail 95% quantiles and may cover more than 95%. Exact means are reported rather than assuming they equal baseline: the nonlinear transform, endpoint handling and rounding may shift the expected value.

Validation checks every attainable percentile against the pure helper extracted directly from survey source, verifies exact probability mass, checks all empirical CDFs against exact probabilities within 0.003, and verifies deterministic feedback at the baseline when sampling the whole pool without replacement. Root random seed: 20260916, separate streams by task/size/method. Run python tools/simulate_pilot_iq_feedback.py (numpy, scipy, matplotlib). No survey configuration or database was changed.
