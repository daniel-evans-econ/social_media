"""Illustrate the survey's noisy IQ feedback for a median reference participant.

Run: python tools/simulate_iq100_feedback.py
Requires numpy, scipy, matplotlib. Does not import oTree or change survey data.
"""

from pathlib import Path
from statistics import NormalDist
import csv
import json
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import binom, hypergeom


OUT = Path(__file__).resolve().parents[1] / "analysis" / "iq100_feedback"
SIZES = list(range(15, 61, 5)) + [75, 100]
N_DRAWS = 1_000_000
SEED = 20260916
MODES = ("with_replacement", "without_replacement")
COLORS = {"with_replacement": "#2563A6", "without_replacement": "#B25F29"}
LABELS = {"with_replacement": "With replacement", "without_replacement": "Without replacement"}
SCORES = np.arange(55, 146)
NORMAL = NormalDist()


def reported_iq(n, counts):
    # Matches _percentile_iq and iq_noise_offset: baseline percentile=.5,
    # so baseline percentile IQ=100 and offset is 15*inverse_normal(p).
    p = np.clip(np.asarray(counts) / n, 0.5 / n, 1 - 0.5 / n)
    offsets = np.array([15 * NORMAL.inv_cdf(float(v)) for v in p])
    rounded = np.sign(offsets) * np.floor(np.abs(offsets) + 0.5)
    return (100 + rounded).astype(int)


def quantile(prob, q):
    return int(SCORES[min(np.searchsorted(np.cumsum(prob), q), len(SCORES) - 1)])


def draw_panel(ax, n, mode, result, ymax, compact=False):
    empirical, exact = result
    ax.bar(SCORES, empirical * 100, width=0.82, color=COLORS[mode], linewidth=0)
    ax.axvline(100, color="#334155", linestyle="--", linewidth=1, alpha=0.8)
    ax.set_xlim(55, 145)
    ax.set_ylim(0, ymax)
    ax.set_xticks([60, 80, 100, 120, 140])
    ax.set_xlabel("Reported IQ (points)")
    ax.set_ylabel("Simulated draws (%)")
    sd = np.sqrt(np.sum((SCORES - 100) ** 2 * exact))
    lo, hi = quantile(exact, 0.025), quantile(exact, 0.975)
    if compact:
        ax.set_title(f"n = {n}   |   SD {sd:.2f}   |   95%: {lo}–{hi}", loc="left", fontsize=10)
    else:
        ax.set_title(LABELS[mode], loc="left", fontsize=14, fontweight="bold", pad=13)
        ax.text(0.98, 0.95, f"SD: {sd:.2f} IQ points\nCentral 95%: {lo}–{hi}",
                transform=ax.transAxes, ha="right", va="top", fontsize=11)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.labelcolor": "#334155", "text.color": "#172B44",
                         "axes.edgecolor": "#CBD5E1", "figure.facecolor": "white"})
    results = {}
    summary = []
    distribution_rows = []
    for n in SIZES:
        count_support = np.arange(n + 1)
        iq_support = reported_iq(n, count_support)
        for mi, mode in enumerate(MODES):
            rng = np.random.default_rng(np.random.SeedSequence([SEED, n, mi]))
            if mode == "with_replacement":
                counts = rng.binomial(n, 0.5, N_DRAWS)
                count_probability = binom.pmf(count_support, n, 0.5)
            else:
                counts = rng.hypergeometric(50, 50, n, N_DRAWS)
                count_probability = hypergeom.pmf(count_support, 100, 50, n)
            # Mapping counts, rather than recomputing inverse_normal per draw,
            # is exactly equivalent and keeps this illustration fast.
            empirical = np.bincount(iq_support[counts] - SCORES[0], minlength=len(SCORES)) / N_DRAWS
            exact = np.bincount(iq_support - SCORES[0], weights=count_probability,
                                minlength=len(SCORES))
            assert np.isclose(exact.sum(), 1)
            assert np.allclose(exact, exact[::-1], atol=1e-12)
            assert abs(np.sum(SCORES * exact) - 100) < 1e-10
            max_cdf_error = float(np.max(np.abs(np.cumsum(empirical) - np.cumsum(exact))))
            assert max_cdf_error < 0.003, (n, mode, max_cdf_error)
            if n == 100 and mode == "without_replacement":
                assert np.all(iq_support[counts] == 100)
            results[n, mode] = empirical, exact
            summary.append(dict(
                group_size=n, sampling=mode, simulated_draws=N_DRAWS,
                empirical_mean=float(np.sum(SCORES * empirical)),
                empirical_sd=float(np.sqrt(np.sum((SCORES - np.sum(SCORES * empirical)) ** 2 * empirical))),
                exact_mean=float(np.sum(SCORES * exact)),
                exact_sd=float(np.sqrt(np.sum((SCORES - 100) ** 2 * exact))),
                exact_p025=quantile(exact, 0.025), exact_p975=quantile(exact, 0.975),
                exact_prob_more_than_5_points=float(exact[np.abs(SCORES - 100) > 5].sum()),
                exact_prob_more_than_10_points=float(exact[np.abs(SCORES - 100) > 10].sum()),
                maximum_empirical_cdf_error=max_cdf_error,
            ))
            for score, ep, xp in zip(SCORES, empirical, exact):
                distribution_rows.append(dict(group_size=n, sampling=mode, reported_iq=int(score),
                                              empirical_probability=float(ep), exact_probability=float(xp)))

    for n in SIZES:
        ymax = max(results[n, m][0].max() for m in MODES) * 100 * 1.22
        fig, axes = plt.subplots(1, 2, figsize=(12, 6.2), sharey=True)
        fig.subplots_adjust(left=0.075, right=0.975, bottom=0.29, top=0.75, wspace=0.12)
        fig.suptitle(f"Noisy IQ feedback from a comparison group of {n}",
                     x=0.075, y=0.95, ha="left", fontsize=20, fontweight="bold")
        fig.text(0.075, 0.87, "Baseline IQ 100 against 100 people · 50 below, 50 above · no ties", fontsize=12)
        for ax, mode in zip(axes, MODES):
            draw_panel(ax, n, mode, results[n, mode], ymax)
        fig.text(0.075, 0.05,
                 "Source: simulated sampling from a fixed, idealized 100-person reference group; 1,000,000 draws per panel.\n"
                 "Survey percentile-to-IQ transform, endpoint adjustment and integer rounding. Dashed line: baseline IQ 100.\n"
                 "SD and equal-tail 95% intervals are exact benchmarks; bars are empirical simulation frequencies.",
                 fontsize=9, color="#475569", linespacing=1.55)
        fig.savefig(OUT / f"iq100_n{n:03d}.png", dpi=180)
        plt.close(fig)

    for mode in MODES:
        fig, axes = plt.subplots(4, 3, figsize=(14, 15))
        fig.subplots_adjust(left=0.075, right=0.975, bottom=0.14, top=0.90, hspace=0.62, wspace=0.30)
        fig.suptitle(f"IQ 100: noisy feedback {LABELS[mode].lower()}",
                     x=0.075, y=0.965, ha="left", fontsize=22, fontweight="bold")
        fig.text(0.075, 0.932, "Fixed reference group: 100 people · 50 below the participant, 50 above · no ties", fontsize=12)
        common_ymax = float(np.ceil(max(results[n, mode][0].max() for n in SIZES
                                        if not (mode == "without_replacement" and n == 100)) * 115 / 5) * 5)
        for ax, n in zip(axes.flat, SIZES):
            ymax = 105 if mode == "without_replacement" and n == 100 else common_ymax
            draw_panel(ax, n, mode, results[n, mode], ymax, compact=True)
        fig.text(0.075, 0.035,
                 "Source: 1,000,000 simulated draws per panel. Survey transform and whole-point rounding; exact SD and central 95% intervals.\n"
                 "Dashed lines mark the baseline IQ of 100. Common axes, except the n=100 panel without replacement (all results are 100).\n"
                 "This is an idealized median participant, not a task-specific estimate from the pilot data. Seed: 20260916.",
                 fontsize=10, color="#475569", linespacing=1.65)
        fig.savefig(OUT / f"overview_{mode}.png", dpi=170)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.23, top=0.80)
    for mode in MODES:
        rows = [r for r in summary if r["sampling"] == mode]
        ax.plot(SIZES, [r["exact_sd"] for r in rows], marker="o", color=COLORS[mode],
                label=LABELS[mode], linewidth=2)
    ax.set_xlabel("Comparison-group size (draws)")
    ax.set_ylabel("Feedback standard deviation (IQ points)")
    ax.set_ylim(bottom=0)
    ax.set_xticks([15, 20, 25, 30, 35, 40, 50, 60, 75, 100])
    ax.grid(color="#E2E8F0")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.suptitle("How comparison-group size changes feedback noise", x=0.10, y=0.95,
                 ha="left", fontsize=18, fontweight="bold")
    fig.text(0.10, 0.87, "Baseline IQ 100 · fixed 100-person reference group · 50 below, 50 above", fontsize=11)
    fig.text(0.10, 0.065,
             "Source: exact binomial / hypergeometric probabilities, validated against 1,000,000 simulations per setting.\n"
             "Uses the survey percentile-to-IQ transform, endpoint adjustment and whole-point rounding.\n"
             "Sampling with replacement can remain noisy at n=100 because the same person can be drawn repeatedly.",
             fontsize=9, color="#475569", linespacing=1.6)
    fig.savefig(OUT / "noise_by_group_size.png", dpi=180)
    plt.close(fig)

    for name, rows in (("summary.csv", summary), ("distributions.csv", distribution_rows)):
        with (OUT / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    (OUT / "README.md").write_text(
        "# Noisy IQ feedback for a median participant\n\n"
        "Created 2026-09-16. These are empirical Monte Carlo distributions from an idealized reference population, "
        "not distributions estimated from pilot participants. The fixed reference pool has 100 people: 50 score "
        "below the focal participant and 50 above; none tie. The focal participant is separate from those 100 people. "
        "Their full-reference percentile is 50% and their baseline IQ is 100.\n\n"
        "Group sizes: 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 75, 100. Each setting uses 1,000,000 independent draws. "
        "With replacement, the number below is Binomial(n, 0.5); without replacement it is Hypergeometric(100, 50, n). "
        "With replacement, n counts draws, not necessarily distinct people.\n\n"
        "## Match to the survey\n\n"
        "The logic follows `_percentile_iq` and `iq_noise_offset` in `social_media/__init__.py` at commit 96662b9. "
        "For K people below the focal participant, p=K/n, clipped to [0.5/n, 1-0.5/n]. "
        "Reported IQ = 100 + round_away_from_zero(15 * inverse_normal(p)). There is no additional IQ-offset cap. "
        "The full-reference percentile correction is zero in this illustration. The currently deployed sampling "
        "method is with replacement. Without replacement is a design alternative.\n\n"
        "Actual pilot data include score ties, different sample sizes, and calibrated task-specific IQ mappings. "
        "A calibrated IQ of 100 alone does not specify the pilot percentile or tie frequency; these plots assume "
        "the stated exact-median, no-ties case. Different underlying score distributions with the same below/equal/above "
        "counts produce the same results. No normality assumption is required for the reference scores themselves.\n\n"
        "## Reading the files\n\n"
        "Each iq100_nNNN.png compares both methods at one size on common axes. Overview PNGs show all sizes for "
        "each method, with common axes except the degenerate n=100 panel without replacement. "
        "noise_by_group_size.png summarizes standard deviations. Bars show simulation frequencies; plot summaries "
        "use exact probabilities to avoid Monte Carlo variation. Intervals are discrete equal-tail quantiles and "
        "can cover more than 95%. Discrete support causes gaps and sometimes excludes IQ 100, especially at odd n; "
        "curves are not smoothed. summary.csv and distributions.csv retain empirical and exact values.\n\n"
        "## Validation and reproduction\n\n"
        "Run `python tools/simulate_iq100_feedback.py` with numpy, scipy and matplotlib. Root seed: 20260916; "
        "independent deterministic streams by sample size and method. Validated exact mass, symmetry, mean=100, "
        "empirical CDF agreement within 0.003, and deterministic IQ=100 when sampling all 100 without replacement. "
        "No survey configuration, database, or deployment was changed.\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(OUT / "iq100_distribution_pngs.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(OUT.iterdir()):
            if path.suffix in {".png", ".csv", ".md"}:
                z.write(path, path.name)
        z.write(Path(__file__), "simulate_iq100_feedback.py")
    print(json.dumps({"output": str(OUT), "png_count": len(list(OUT.glob('*.png'))),
                      "n30": [r for r in summary if r['group_size'] == 30],
                      "max_cdf_error": max(r['maximum_empirical_cdf_error'] for r in summary)}, indent=2))


if __name__ == "__main__":
    main()
