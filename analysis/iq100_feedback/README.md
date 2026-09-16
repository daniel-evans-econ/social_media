# Noisy IQ feedback for a median participant

Created 2026-09-16. These are empirical Monte Carlo distributions from an idealized reference population, not distributions estimated from pilot participants. The fixed reference pool has 100 people: 50 score below the focal participant and 50 above; none tie. The focal participant is separate from those 100 people. Their full-reference percentile is 50% and their baseline IQ is 100.

Group sizes: 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 75, 100. Each setting uses 1,000,000 independent draws. With replacement, the number below is Binomial(n, 0.5); without replacement it is Hypergeometric(100, 50, n). With replacement, n counts draws, not necessarily distinct people.

## Match to the survey

The logic follows `_percentile_iq` and `iq_noise_offset` in `social_media/__init__.py` at commit 96662b9. For K people below the focal participant, p=K/n, clipped to [0.5/n, 1-0.5/n]. Reported IQ = 100 + round_away_from_zero(15 * inverse_normal(p)). There is no additional IQ-offset cap. The full-reference percentile correction is zero in this illustration. The currently deployed sampling method is with replacement. Without replacement is a design alternative.

Actual pilot data include score ties, different sample sizes, and calibrated task-specific IQ mappings. A calibrated IQ of 100 alone does not specify the pilot percentile or tie frequency; these plots assume the stated exact-median, no-ties case. Different underlying score distributions with the same below/equal/above counts produce the same results. No normality assumption is required for the reference scores themselves.

## Reading the files

Each iq100_nNNN.png compares both methods at one size on common axes. Overview PNGs show all sizes for each method, with common axes except the degenerate n=100 panel without replacement. noise_by_group_size.png summarizes standard deviations. Bars show simulation frequencies; plot summaries use exact probabilities to avoid Monte Carlo variation. Intervals are discrete equal-tail quantiles and can cover more than 95%. Discrete support causes gaps and sometimes excludes IQ 100, especially at odd n; curves are not smoothed. summary.csv and distributions.csv retain empirical and exact values.

## Validation and reproduction

Run `python tools/simulate_iq100_feedback.py` with numpy, scipy and matplotlib. Root seed: 20260916; independent deterministic streams by sample size and method. Validated exact mass, symmetry, mean=100, empirical CDF agreement within 0.003, and deterministic IQ=100 when sampling all 100 without replacement. No survey configuration, database, or deployment was changed.
