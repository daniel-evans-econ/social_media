"""Resample the actual deployed pilot reference pools near baseline IQ 100.

Run: python tools/simulate_pilot_iq_feedback.py
Requires numpy, scipy, matplotlib. No database or survey settings are modified.
"""
from pathlib import Path
from statistics import NormalDist
import ast
import csv
import hashlib
import json
import math
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import multinomial

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "pilot_iq_feedback"
DATA = ROOT / "social_media" / "data"
SIZES = list(range(15, 61, 5)) + [75, 100]
DRAWS = 1_000_000
SEED = 20260916
SCORES = np.arange(40, 161)
TASKS = [("working_memory", "Working memory", 8),
         ("fluid", "Abstract reasoning", 7),
         ("numerical", "Numerical reasoning", 9)]
MODES = ["with_replacement", "without_replacement"]
COLORS = ["#2563A6", "#B25F29"]
NORMAL = NormalDist()


def load_survey_helper():
    """Execute only the pure helper, directly from survey source, for validation."""
    source = ast.parse((ROOT / "social_media" / "__init__.py").read_text(encoding="utf-8"))
    helper = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "_percentile_iq")
    namespace = {"NormalDist": NormalDist}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), "survey_helper", "exec"), namespace)
    return namespace["_percentile_iq"]


def away(x):
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def mapping(n, baseline, full_iq):
    # k=2*below+equal indexes every possible mid-P percentile, retaining ties.
    p = np.clip(np.arange(2 * n + 1) / (2 * n), 0.5 / n, 1 - 0.5 / n)
    return np.array([baseline + away(100 + 15 * NORMAL.inv_cdf(float(v)) - full_iq) for v in p])


def exact_distribution(n, categories, iqmap, mode):
    states = np.array([(b, e, n-b-e) for b in range(n+1) for e in range(n-b+1)])
    if mode == "with_replacement":
        prob = multinomial.pmf(states, n, categories / categories.sum())
    else:
        denominator = math.comb(int(categories.sum()), n)
        prob = np.array([math.prod(math.comb(int(cap), int(k)) if k <= cap else 0
                                   for cap, k in zip(categories, state)) / denominator for state in states])
    scores = iqmap[2 * states[:, 0] + states[:, 1]]
    return np.bincount(scores - SCORES[0], weights=prob, minlength=len(SCORES))


def stats(p, baseline):
    mean = float(SCORES @ p)
    return dict(mean=mean, sd=float(np.sqrt(((SCORES - mean)**2) @ p)),
                p025=int(SCORES[np.searchsorted(np.cumsum(p), .025)]),
                p975=int(SCORES[np.searchsorted(np.cumsum(p), .975)]),
                prob_more_than_5_points=float(p[np.abs(SCORES-baseline)>5].sum()),
                prob_more_than_10_points=float(p[np.abs(SCORES-baseline)>10].sum()))


def panel(ax, task, n, mode, result, ymax, compact=False):
    empirical, exact = result
    s = stats(exact, task["baseline_iq"])
    ax.bar(SCORES, 100 * empirical, width=.85, color=COLORS[MODES.index(mode)])
    ax.axvline(task["baseline_iq"], linestyle="--", linewidth=1, color="#334155")
    ax.set(xlim=(50, 150), ylim=(0, ymax), xticks=[60, 80, 100, 120, 140],
           xlabel="Reported IQ (points)", ylabel="Simulated draws (%)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E2E8F0", linewidth=.7)
    ax.set_axisbelow(True)
    if compact:
        title = f"n={n}  |  SD {s['sd']:.2f}  |  95%: {s['p025']}–{s['p975']}"
        ax.set_title(title, loc="left", fontsize=10)
    else:
        title = f"{task['label']} · {mode.replace('_', ' ')}"
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=12)
        ax.text(.97, .94, f"Baseline {task['baseline_iq']} · pilot N={task['pool_n']}\n"
                f"Mean {s['mean']:.2f} · SD {s['sd']:.2f}\n95%: {s['p025']}–{s['p975']}",
                transform=ax.transAxes, ha="right", va="top", fontsize=10)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pools = json.loads((DATA / "iq_scores_initial.json").read_text())
    tables = json.loads((DATA / "iq_distribution_initial.json").read_text())
    helper = load_survey_helper()
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "text.color": "#172B44", "axes.labelcolor": "#334155",
                         "axes.edgecolor": "#CBD5E1"})
    tasks, results, summary, distributions = [], {}, [], []
    for ti, (component, label, score) in enumerate(TASKS):
        sample = np.array(pools[component])
        categories = np.array([(sample < score).sum(), (sample == score).sum(), (sample > score).sum()])
        baseline = int(round(tables[component][str(score)]))
        full_iq = helper(sample.tolist(), score)
        task = dict(component=component, label=label, raw_score=score, baseline_iq=baseline,
                    pool_n=len(sample), below=int(categories[0]), equal=int(categories[1]),
                    above=int(categories[2]), full_pool_percentile=100*(categories[0]+.5*categories[1])/len(sample),
                    full_pool_percentile_iq=full_iq)
        tasks.append(task)
        # n>N is excluded for both methods: the deployed helper returns zero
        # noise in that case, before performing any sampling.
        sizes = [n for n in SIZES if n <= len(sample)]
        for n in sizes:
            iqmap = mapping(n, baseline, full_iq)
            assert iqmap.min() >= 50 and iqmap.max() <= 150
            # Every possible mid-P value must agree with the actual survey helper.
            for k, iq in enumerate(iqmap):
                below, equal = divmod(k, 2)
                group = [score-1]*below + [score]*equal + [score+1]*(n-below-equal)
                assert iq == baseline + away(helper(group, score) - full_iq)
            for mi, mode in enumerate(MODES):
                rng = np.random.default_rng(np.random.SeedSequence([SEED, ti, n, mi]))
                if mode == "with_replacement":
                    draws = rng.multinomial(n, categories / len(sample), size=DRAWS)
                else:
                    draws = rng.multivariate_hypergeometric(categories, n, size=DRAWS)
                empirical = np.bincount(iqmap[2*draws[:, 0]+draws[:, 1]] - SCORES[0],
                                        minlength=len(SCORES)) / DRAWS
                exact = exact_distribution(n, categories, iqmap, mode)
                assert np.isclose(exact.sum(), 1, atol=1e-10)
                cdf_error = float(np.max(np.abs(np.cumsum(empirical)-np.cumsum(exact))))
                assert cdf_error < .003
                if n == len(sample) and mode == "without_replacement":
                    assert np.isclose(exact[SCORES == baseline][0], 1)
                results[component, n, mode] = empirical, exact
                summary.append(dict(**task, group_size=n, sampling=mode, simulated_draws=DRAWS,
                                    **{f"exact_{k}":v for k,v in stats(exact, baseline).items()},
                                    **{f"empirical_{k}":v for k,v in stats(empirical, baseline).items()},
                                    maximum_empirical_cdf_error=cdf_error))
                for iq, ep, xp in zip(SCORES, empirical, exact):
                    distributions.append(dict(component=component, baseline_iq=baseline, group_size=n,
                                              sampling=mode, reported_iq=int(iq),
                                              empirical_probability=float(ep), exact_probability=float(xp)))
        print(f"Completed simulations: {label} (N={len(sample)}, baseline={baseline})", flush=True)

    for n in SIZES:
        eligible = [t for t in tasks if n <= t["pool_n"]]
        rows = len(eligible)
        fig, axes = plt.subplots(rows, 2, figsize=(12, 3.6*rows+2.5), squeeze=False)
        fig.subplots_adjust(left=.075, right=.975, bottom=1.5/(3.6*rows+2.5),
                            top=1-1.3/(3.6*rows+2.5), hspace=.5, wspace=.17)
        fig.suptitle(f"Actual pilot data: feedback from {n} comparison draws", x=.075, y=.975,
                     ha="left", fontsize=19, fontweight="bold")
        fig.text(.075, 1-.85/(3.6*rows+2.5),
                 "Working memory: IQ 100 · Abstract and numerical reasoning: nearest available baseline IQ 101",
                 fontsize=10)
        for axs, task in zip(axes, eligible):
            ymax = max(results[task['component'], n, m][0].max() for m in MODES)*125
            for ax, mode in zip(axs, MODES):
                panel(ax, task, n, mode, results[task['component'], n, mode], ymax)
        missing = [t['label'] for t in tasks if n > t['pool_n']]
        footer = ("Source: actual pilot reference scores used by the IQ pilot (iq_scores_initial.json); 1,000,000 resamples per panel.\n"
                  "Preserves ties, task-specific pool sizes, full-pool correction and survey integer rounding. Dashed line: baseline IQ.\n"
                  "Bars: empirical simulation frequencies. Mean, SD and equal-tail 95% intervals: exact probabilities.")
        if missing:
            footer += "\nExcluded because n exceeds the actual pool: " + ", ".join(missing) + "."
        fig.text(.075, .03, footer, fontsize=9, color="#475569", linespacing=1.6)
        fig.savefig(OUT / f"pilot_n{n:03d}.png", dpi=170)
        plt.close(fig)

    for task in tasks:
        component = task['component']
        sizes = [n for n in SIZES if n <= task['pool_n']]
        for mode in MODES:
            fig, axes = plt.subplots(4, 3, figsize=(14, 15))
            fig.subplots_adjust(left=.075, right=.975, bottom=.14, top=.88, hspace=.64, wspace=.3)
            fig.suptitle(f"{task['label']}: baseline IQ {task['baseline_iq']}", x=.075, y=.965,
                         ha="left", fontsize=23, fontweight="bold")
            fig.text(.075, .93, f"Actual pilot N={task['pool_n']} · raw score {task['raw_score']}/15 · "
                     f"{mode.replace('_', ' ')}", fontsize=14)
            fig.text(.075, .905, f"Pilot respondents: {task['below']} below, {task['equal']} tied, "
                     f"{task['above']} above the focal score", fontsize=11)
            nondeg = [n for n in sizes if not (n == task['pool_n'] and mode == 'without_replacement')]
            common_y = math.ceil(max(results[component,n,mode][0].max() for n in nondeg)*115/5)*5
            for ax, n in zip(axes.flat, sizes):
                ymax = 105 if n == task['pool_n'] and mode == 'without_replacement' else common_y
                panel(ax, task, n, mode, results[component,n,mode], ymax, compact=True)
            for ax in list(axes.flat)[len(sizes):]:
                fig.delaxes(ax)
            fig.text(.075, .035,
                     "Source: deployed pilot reference scores, iq_scores_initial.json. 1,000,000 resamples per panel; ties retained.\n"
                     "Survey mid-P transform, full-pool correction and integer rounding. Dashed lines: baseline IQ; exact SD and 95% intervals.\n"
                     "Common axes except sampling the entire pool without replacement. Sizes exceeding the pilot pool are excluded.",
                     fontsize=10, color="#475569", linespacing=1.6)
            fig.savefig(OUT / f"{component}_{mode}.png", dpi=170)
            plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.8), sharey=True)
    fig.subplots_adjust(left=.07, right=.98, top=.74, bottom=.27, wspace=.14)
    fig.suptitle("Actual pilot data: feedback variability by comparison-group size",
                 x=.07, y=.95, ha="left", fontsize=19, fontweight="bold")
    for ax, task in zip(axes, tasks):
        for mode, color in zip(MODES, COLORS):
            rows = [r for r in summary if r['component']==task['component'] and r['sampling']==mode]
            ax.plot([r['group_size'] for r in rows], [r['exact_sd'] for r in rows],
                    color=color, marker='o', label=mode.replace('_',' ').capitalize())
        ax.set_title(f"{task['label']}\nBaseline IQ {task['baseline_iq']} · pilot N={task['pool_n']}", fontsize=12)
        ax.set(xlabel="Comparison-group size (draws)", ylim=(0, 5.5))
        ax.grid(color="#E2E8F0")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Feedback SD (IQ points)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5,.125), ncol=2, frameon=False)
    fig.text(.07, .035, "Source: actual pilot pools; exact sampling probabilities, checked against 1,000,000 simulations per setting.\n"
             "Task-specific ties and survey calculation retained. Sizes above the actual reference-pool size are excluded.",
             fontsize=10, color="#475569", linespacing=1.6)
    fig.savefig(OUT / "pilot_noise_by_group_size.png", dpi=180)
    plt.close(fig)

    for filename, rows in [("summary.csv",summary), ("distributions.csv",distributions), ("reference_profiles.csv",tasks)]:
        with (OUT / filename).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    provenance = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  [DATA/'iq_scores_initial.json', DATA/'iq_distribution_initial.json']}
    (OUT/'source_hashes.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (OUT/'README.md').write_text(
        "# Actual-pilot noisy IQ feedback\n\n"
        "These replace the idealized illustration in ../iq100_feedback for the user's actual-data request. "
        "Source: social_media/data/iq_scores_initial.json and iq_distribution_initial.json, the reference pools "
        "and calibrated score-to-IQ tables used by EXPERIMENT_PILOT=iq. Data hashes are included.\n\n"
        "## Baseline selection\n\n"
        "Working memory: 8/15 correct, calibrated IQ 100, N=82 (41 below, 9 tied, 32 above). "
        "Abstract reasoning: 7/15, calibrated IQ 101, N=60 (31 below, 5 tied, 24 above). "
        "Numerical reasoning: 9/15, calibrated IQ 101, N=105 (52 below, 14 tied, 39 above). "
        "Only working memory has an exact calibrated IQ of 100. The other tasks use the nearest available IQ, "
        "without interpolation or recentering. The focal participant is treated as a new participant compared "
        "with these full reference pools; no reference observation is removed. Spatial reasoning is omitted "
        "because it is not one of the three tasks in the current IQ pilot.\n\n"
        "## Calculation\n\n"
        "1,000,000 independent comparison groups per task, size and sampling method. Mid-P percentile is "
        "(number below + 0.5 * number tied)/n, clipped to [0.5/n,1-0.5/n]. The sampled percentile is converted "
        "to 100+15*inverse_normal(p). Subtract the analogous percentile IQ for the entire actual pilot pool, "
        "round the resulting offset to the nearest integer (halves away from zero), and add it to the "
        "calibrated baseline IQ. This follows _percentile_iq, iq_noise_offset and estimate_iq_for_player. "
        "There is no additional hard cap. A baseline IQ of 100 need not be the empirical 50th percentile "
        "because the calibrated lookup table and empirical distribution differ.\n\n"
        "Sampling with replacement follows the currently deployed mechanism. Without replacement is the "
        "alternative requested for comparison. Below/tied/above counts are sufficient statistics: draws "
        "from their multinomial or multivariate hypergeometric distribution are exactly equivalent to "
        "resampling individual records from the actual pilot pool for this feedback calculation. All ties "
        "and observed frequencies are retained. The observations are not forced into a 100-person pool. "
        "Sizes above a task's actual pool are excluded for both methods: the survey currently returns zero "
        "noise rather than sampling when its requested group size exceeds the pool.\n\n"
        "## Files and verification\n\n"
        "pilot_nNNN.png compares tasks and sampling methods at each size. working_memory_*.png gives "
        "the exact IQ-100 case over all eligible sizes. The other task overviews show IQ 101 and are labelled "
        "accordingly. pilot_noise_by_group_size.png summarizes variability. CSVs retain empirical and exact "
        "values; intervals are discrete equal-tail 95% quantiles and may cover more than 95%. "
        "Exact means are reported rather than assuming they equal baseline: the nonlinear transform, "
        "endpoint handling and rounding may shift the expected value.\n\n"
        "Validation checks every attainable percentile against the pure helper extracted directly from "
        "survey source, verifies exact probability mass, checks all empirical CDFs against exact probabilities "
        "within 0.003, and verifies deterministic feedback at the baseline when sampling the whole pool "
        "without replacement. Root random seed: 20260916, separate streams by task/size/method. "
        "Run python tools/simulate_pilot_iq_feedback.py (numpy, scipy, matplotlib). No survey configuration "
        "or database was changed.\n",encoding='utf-8')
    with zipfile.ZipFile(OUT/'actual_pilot_distribution_pngs.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):
            if p.suffix in {'.png','.csv','.md','.json'}:
                z.write(p,p.name)
        z.write(Path(__file__),Path(__file__).name)
    print(json.dumps(dict(output=str(OUT),png_count=len(list(OUT.glob('*.png'))),
                         n30=[{k:r[k] for k in ['component','baseline_iq','sampling','exact_mean','exact_sd','exact_p025','exact_p975']}
                              for r in summary if r['group_size']==30]),indent=2))


if __name__ == '__main__':
    main()
