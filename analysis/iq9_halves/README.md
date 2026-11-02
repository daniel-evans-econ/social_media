# Reported IQ distributions at 9/15, conditional on comparison half

Generated 2 November 2026 with `python tools/simulate_iq9_halves.py`.
The script reads the encrypted pilot reference data using `PEER_REFERENCE_KEY`
from `.env`; outputs contain aggregate statistics only.

## Design

- Own score fixed at 9/15 in each of numerical reasoning, abstract reasoning,
  and working memory. These are task-specific distributions, not overall IQ.
- 20 comparison respondents drawn uniformly with replacement within the lower
  or upper performance half. Half boundaries and tied-score ordering match
  `social_media.peer_groups.group_for` exactly.
- Quantitative: within the assigned half, require all three numerical reports,
  including respondents who did not send those reports. Qualitative: all
  historical conditions are eligible within the assigned half.
- One million independent Monte Carlo draws for each of the 12 combinations of
  task, message format and half, using seed 20261102.
- Draw counts below, tied with, and above 9 from their multinomial distribution.
  This is equivalent to drawing 20 individual respondents for the IQ calculation.
- Apply the live survey's midrank percentile (ties count half), clipping to
  2.5%–97.5%, normal transformation, full-pool subtraction, calibrated full-sample
  IQ addition, and integer rounding. No changes to the survey calculation.

## Validation and summaries

All 231 attainable count combinations are evaluated through the live scoring
function. Exact probabilities are summed by displayed IQ. The plots use simulated
frequencies; means, SDs and 2.5th/97.5th percentiles use exact probabilities, avoiding
Monte Carlo fluctuation in the summary values. These intervals describe possible
feedback, not uncertainty about a person's true IQ.

Monte Carlo CDF error is below 0.0013 in every cell. A further 100 ordinary live
comparison-group draws per task and format validate eligible membership and
agreement between identity-level scoring and count-based scoring.

## Files

- `quantitative_iq9_halves.png` and `qualitative_iq9_halves.png`: three task rows,
  lower-half left and upper-half right; identical axes, no gridlines. Dashed line
  marks the calibrated full-sample IQ for 9/15.
- `summary.csv`: means, SDs, central 95% bounds, modes, pool sizes and validation.
- `distributions.csv`: exact and simulated probability for each IQ value.
- `results.json`: full results, seed and hashes of source files.

## Main finding

At 9/15, lower-half abstract-reasoning feedback is always 129 and lower-half
working-memory feedback is always 130, in both message formats: every eligible
peer scored below 9. Numerical-reasoning lower-half feedback varies because the
half includes peers tied at 9. Upper-half distributions remain substantially
lower in all three tasks. Conditioning on the half exposes the large between-half
shift that would be hidden inside a pooled distribution.
