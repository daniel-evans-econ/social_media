"""Publish complete IQ ranges after the whole-stratum message-sampling rerun."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/stratum_message_sampling'
TASKS = {'sequences': 'Numerical reasoning', 'working_memory': 'Working memory', 'ravens': 'Abstract reasoning'}
FORMATS = ['quantitative', 'qualitative']


def panel_rows(data, task, fmt, scores, design=None):
    rows = []
    if design is None:
        headers = ['Correct\n/15', 'Full sample\nIQ', 'Quintiles', 'Terciles', 'Halves']
    else:
        unit = {5: 'Q', 3: 'T', 2: 'H'}[design['strata']]
        headers = ['Correct\n/15', 'Full sample\nIQ'] + [f'{unit}{i}' for i in range(1, design['strata'] + 1)]
    for score in scores:
        if design is None:
            selected = [next(r for r in d['rows'] if r['task'] == task and r['format'] == fmt and r['score'] == score) for d in data['designs']]
        else:
            selected = [c['outcomes'][score] for c in design['cells'] if c['task'] == task and c['format'] == fmt]
        rows.append([str(score), str(selected[0]['full_sample_iq'])] + [f"{r['p025']:.0f}-{r['p975']:.0f}" for r in selected])
        for r in selected:
            mass = sum(p for x, p in zip(r['support'], r['probabilities']) if r['p025'] <= x <= r['p975'])
            assert mass >= .95 - 1e-10
    return headers, rows


def figure(data, task, scores, design=None, page=None):
    short = len(scores) == 6
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.7 if short else 8.2))
    suffix = f"Within each { {5:'quintile',3:'tercile',2:'half'}[design['strata']]}" if design else 'Pooling over assigned strata'
    fig.suptitle(f'{TASKS[task]}: central 95% IQ ranges', x=.045, ha='left', fontsize=18)
    fig.text(.045, .88 if short else .91, suffix, fontsize=13)
    for ax, fmt in zip(axes, FORMATS):
        ax.axis('off')
        headers, rows = panel_rows(data, task, fmt, scores, design)
        table = ax.table(cellText=rows, colLabels=headers, cellLoc='center', bbox=[0, .02, 1, .91])
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
    note = 'Groups are ordered from lowest to highest historical performance.' if design else 'Each performance stratum is equally likely; these ranges include variation between strata.'
    fig.text(.045, .035, 'Actual pilot data | 20 draws with replacement | Exact 2.5th-97.5th percentiles of displayed IQ.\n'
             + note + '\nThese are feedback-distribution ranges, not confidence intervals for true IQ. Rerun: 28 October 2026.', fontsize=9)
    if page:
        fig.text(.965, .035, str(page), ha='right', fontsize=9)
    fig.subplots_adjust(left=.045, right=.97, bottom=.16 if short else .12, top=.75 if short else .84, wspace=.15)
    return fig


def main():
    data = json.loads((OUT / 'comparison.json').read_text())
    old = json.loads((ROOT / 'analysis/strata_comparison/comparison.json').read_text())
    for prior, new in zip(old['designs'], data['designs']):
        assert prior['rows'] == new['rows']
        for a, b in zip(prior['cells'], new['cells']):
            assert a['outcomes'] == b['outcomes']
    pdf_dir = ROOT / 'output/pdf'
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / 'iq-feedback-95-intervals.pdf'
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
