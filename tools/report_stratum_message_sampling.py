"""Publish complete IQ ranges after the whole-stratum message-sampling rerun."""
import json
from pathlib import Path
import numpy as np
from simulate_pilot_iq_feedback import (
    SCORES, exact_distribution, load_survey_helper, mapping, stats,
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/stratum_message_sampling'
TASKS = {'sequences': 'Numerical reasoning', 'working_memory': 'Working memory', 'ravens': 'Abstract reasoning'}
FORMATS = ['quantitative', 'qualitative']


def previous_procedure():
    """Exact legacy N=20 whole-pool sampling without replacement.

    Matches the pre-stratification implementation (parent of 7329bae),
    including its full task pools, calibration, clipping and integer rounding.
    Unlike the new quantitative pool, this did not filter by message format.
    """
    directory = ROOT / 'social_media/data'
    pools = json.loads((directory / 'iq_scores_initial.json').read_text())
    calibration = json.loads((directory / 'iq_distribution_initial.json').read_text())
    percentile_iq = load_survey_helper()
    results = {}
    rng = np.random.default_rng(20261028)
    for task, component in [('sequences', 'numerical'), ('working_memory', 'working_memory'), ('ravens', 'fluid')]:
        pool = np.array(pools[component])
        outcomes = []
        for score in range(16):
            base = int(round(calibration[component][str(score)]))
            categories = np.array([(pool < score).sum(), (pool == score).sum(), (pool > score).sum()])
            iqmap = mapping(20, base, percentile_iq(pool, score))
            probabilities = exact_distribution(20, categories, iqmap, 'without_replacement')
            assert np.isclose(probabilities.sum(), 1)
            # Independent Monte Carlo check of the exact hypergeometric CDF.
            counts = rng.multivariate_hypergeometric(categories, 20, size=100000)
            observed = iqmap[2 * counts[:, 0] + counts[:, 1]]
            error = max(abs(np.mean(observed <= x) - probabilities[SCORES <= x].sum()) for x in np.unique(observed))
            assert error < .01, (task, score, error)
            keep = probabilities > 0
            outcomes.append(dict(score=score, full_sample_iq=base, **stats(probabilities, base),
                                 support=SCORES[keep].tolist(), probabilities=probabilities[keep].tolist()))
        results[task] = dict(pool_size=len(pool), outcomes=outcomes)
    return dict(group_size=20, replacement=False, source='full task-specific iq_scores_initial pools', tasks=results)


def panel_rows(data, task, fmt, scores, design=None):
    rows = []
    if design is None:
        headers = ['Correct\n/15', 'Full sample\nIQ', 'Whole pool\n(previous)', 'Quintiles', 'Terciles', 'Halves']
    else:
        unit = {5: 'Q', 3: 'T', 2: 'H'}[design['strata']]
        headers = ['Correct\n/15', 'Full sample\nIQ', 'Whole pool\n(previous)'] + [f'{unit}{i}' for i in range(1, design['strata'] + 1)]
    for score in scores:
        if design is None:
            selected = [next(r for r in d['rows'] if r['task'] == task and r['format'] == fmt and r['score'] == score) for d in data['designs']]
        else:
            selected = [c['outcomes'][score] for c in design['cells'] if c['task'] == task and c['format'] == fmt]
        previous = data['previous_procedure']['tasks'][task]['outcomes'][score]
        assert previous['full_sample_iq'] == selected[0]['full_sample_iq']
        selected = [previous] + selected
        rows.append([str(score), str(selected[0]['full_sample_iq'])] + [f"{r['p025']:.0f}-{r['p975']:.0f}" for r in selected])
        for r in selected:
            mass = sum(p for x, p in zip(r['support'], r['probabilities']) if r['p025'] <= x <= r['p975'])
            assert mass >= .95 - 1e-10
    return headers, rows


def figure(data, task, scores, design=None, page=None):
    short = len(scores) == 6
    fig, axes = plt.subplots(1, 2, figsize=(15.6, 5.7 if short else 8.2))
    suffix = f"Within each { {5:'quintile',3:'tercile',2:'half'}[design['strata']]}" if design else 'Pooling over assigned strata'
    fig.suptitle(f'{TASKS[task]}: central 95% IQ ranges', x=.045, ha='left', fontsize=18)
    fig.text(.045, .88 if short else .91, suffix, fontsize=13)
    for ax, fmt in zip(axes, FORMATS):
        ax.axis('off')
        headers, rows = panel_rows(data, task, fmt, scores, design)
        widths = [1, 1.5, 1.8] + [1] * (len(headers) - 3)
        table = ax.table(cellText=rows, colLabels=headers, cellLoc='center',
                         colWidths=np.array(widths) / sum(widths), bbox=[0, .02, 1, .91])
        table.auto_set_font_size(False)
        table.set_fontsize(10 if design and design['strata'] == 5 else 11)
        for (row, col), cell in table.get_celld().items():
            cell.set_linewidth(0)
            if row == 0:
                cell.set_facecolor('#e5ebf1')
                cell.set_text_props(weight='bold')
            elif row % 2:
                cell.set_facecolor('#f4f6f8')
        ax.set_title(f'{fmt.capitalize()} message condition', fontsize=13, loc='left')
    if page:
        fig.text(.965, .035, str(page), ha='right', fontsize=9)
    fig.subplots_adjust(left=.045, right=.97, bottom=.07, top=.75 if short else .84, wspace=.15)
    return fig


def main():
    data = json.loads((OUT / 'comparison.json').read_text())
    data['previous_procedure'] = previous_procedure()
    (OUT / 'previous_whole_pool.json').write_text(json.dumps(data['previous_procedure'], indent=2) + '\n')
    old = json.loads((ROOT / 'analysis/strata_comparison/comparison.json').read_text())
    for prior, new in zip(old['designs'], data['designs']):
        assert prior['rows'] == new['rows']
        for a, b in zip(prior['cells'], new['cells']):
            assert a['outcomes'] == b['outcomes']
    pdf_dir = ROOT / 'output/pdf'
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / 'iq-feedback-95-intervals-with-whole-pool.pdf'
    page = 0
    with PdfPages(pdf_path) as pdf:
        for task in TASKS:
            page += 1
            fig = figure(data, task, range(16), page=page)
            pdf.savefig(fig)
            fig.savefig(OUT / f'{task}_all_scores_pooled.png', dpi=150)
            plt.close(fig)
        for design in data['designs']:
            for task in TASKS:
                page += 1
                fig = figure(data, task, range(16), design, page)
                pdf.savefig(fig)
                fig.savefig(OUT / f"{task}_{design['name']}_conditional.png", dpi=150)
                plt.close(fig)
        pdf.infodict()['Title'] = 'IQ feedback: complete central 95% intervals'
        pdf.infodict()['Subject'] = 'Actual pilot data; every score 0-15, task, message format and performance stratum'
    assert page == 12
    for task in TASKS:
        fig = figure(data, task, range(0, 16, 3))
        fig.savefig(OUT / f'{task}_95pct_score_grid.png', dpi=170)
        plt.close(fig)
    print('Validated all interval masses >=95% and exact agreement with prior IQ calculations.')
    print('Created 12 PDF pages and 15 interval PNGs:', pdf_path)


if __name__ == '__main__':
    main()
