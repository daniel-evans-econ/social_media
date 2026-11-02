"""IQ feedback at 9/15, conditional on comparison half; aggregate-only output.

Run python tools/simulate_iq9_halves.py with PEER_REFERENCE_KEY in .env.
One million multinomial simulations per task/format/half, checked against the
exact distribution and the live survey functions. No participant data modified.
"""
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import multinomial
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')
os.environ['EXPERIMENT_PILOT'] = 'iq'
os.environ['OTREE_IN_MEMORY'] = '1'
import social_media as survey
from social_media.peer_groups import reference, group_for

OUT = ROOT / 'analysis' / 'iq9_halves'
N, SCORE, DRAWS, SEED = survey.IQ_COMPARISON_GROUP, 9, 1_000_000, 20261102
TASKS = ['sequences', 'ravens', 'working_memory']
FORMATS = ['quantitative', 'qualitative']
STATES = np.array([(b, t, N-b-t) for b in range(N+1) for t in range(N-b+1)])


def player_for(task, fmt, code='analysis'):
    return SimpleNamespace(round_number=15, participant=SimpleNamespace(code=code, vars=dict(
        linked_peer_groups=True, peer_group_strata=2, peer_group_sampling='quantitative_only_v1',
        period_tasks=[task], social_type=fmt+'_social')))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pools = reference(survey.CFG['iq_distribution_source'])
    rng = np.random.default_rng(SEED)
    cells, probability_rows = [], []
    for fmt in FORMATS:
        for task in TASKS:
            rows = sorted(pools[task], key=lambda r: (r['score'], hashlib.sha256((task+r['id']).encode()).hexdigest()))
            component = survey.TASK_IQ_COMPONENT[task]
            full_iq = survey.estimate_iq(component, SCORE, 15)
            # Evaluate every attainable count combination through the live rule,
            # including tie weights, endpoint clipping, calibration and rounding.
            player = player_for(task, fmt)
            values = []
            for below, tied, above in STATES:
                player.participant.vars['peer_groups'] = {'1': dict(scores=[8]*int(below)+[9]*int(tied)+[10]*int(above))}
                values.append(survey.estimate_iq_for_player(player, component, SCORE, 15))
            values = np.asarray(values, dtype=int)
            support, inverse = np.unique(values, return_inverse=True)
            lookup = np.zeros((N+1, N+1), dtype=int)
            lookup[STATES[:,0], STATES[:,1]] = values
            for half in (1, 2):
                stratum = rows[len(rows)*(half-1)//2:len(rows)*half//2]
                eligible = stratum if fmt == 'qualitative' else [r for r in stratum if len(r['blocks']) == 3 and all(b['report'] is not None for b in r['blocks'])]
                scores = np.array([r['score'] for r in eligible])
                p = np.array([np.mean(scores<SCORE), np.mean(scores==SCORE), np.mean(scores>SCORE)])
                exact = np.bincount(inverse, weights=multinomial.pmf(STATES, N, p), minlength=len(support))
                assert np.isclose(exact.sum(), 1)
                exact /= exact.sum()
                counts = rng.multinomial(N, p, size=DRAWS)
                simulated = lookup[counts[:,0], counts[:,1]]
                mc = np.array([np.mean(simulated==s) for s in support])
                cdf_error = float(np.max(np.abs(np.cumsum(mc)-np.cumsum(exact))))
                assert cdf_error < .003, (task, fmt, half, cdf_error)
                # Independently check ordinary live draws use this exact pool
                # and produce the same IQ as the count-based simulation.
                checked = 0
                for i in range(100):
                    live = player_for(task, fmt, f'iq9-validation-{task}-{fmt}-{i}')
                    group = group_for(live, 1)
                    if group['stratum'] != half:
                        continue
                    assert set(group['draw_ids']).issubset({r['id'] for r in eligible})
                    b = sum(s<SCORE for s in group['scores'])
                    t = sum(s==SCORE for s in group['scores'])
                    assert survey.estimate_iq_for_player(live, component, SCORE, 15) == lookup[b,t]
                    checked += 1
                assert checked > 20
                cdf = np.cumsum(exact)
                mean = float(support@exact)
                cell = dict(format=fmt, task=task, label=survey.TASK_LABELS[task],
                    half='lower' if half==1 else 'upper', score=SCORE, full_sample_iq=full_iq,
                    eligible_n=len(eligible), below=int(sum(scores<SCORE)), tied=int(sum(scores==SCORE)), above=int(sum(scores>SCORE)),
                    mean=mean, sd=float(np.sqrt((support-mean)**2@exact)),
                    p025=int(support[np.searchsorted(cdf,.025)]), p975=int(support[np.searchsorted(cdf,.975)]),
                    mode=int(support[np.argmax(exact)]), mode_probability=float(exact.max()),
                    monte_carlo_max_cdf_error=cdf_error, live_draws_checked=checked,
                    support=support.tolist(), exact_probabilities=exact.tolist(), simulated_probabilities=mc.tolist())
                cells.append(cell)
                for s,e,m in zip(support,exact,mc):
                    probability_rows.append(dict(format=fmt,task=task,half=cell['half'],reported_iq=int(s),exact_probability=float(e),simulated_probability=float(m)))
    for fmt in FORMATS:
        fig, axes = plt.subplots(3,2,figsize=(13,10),sharex=True,sharey=True)
        for r,task in enumerate(TASKS):
            for c,half in enumerate(('lower','upper')):
                ax=axes[r,c]
                cell=next(x for x in cells if x['format']==fmt and x['task']==task and x['half']==half)
                ax.bar(cell['support'],np.array(cell['simulated_probabilities'])*100,width=.85,
                       color='#3575a5' if half=='lower' else '#bb633d',linewidth=0)
                ax.axvline(cell['full_sample_iq'],color='#4b5563',ls='--',lw=1.2)
                ax.set_title(f"{cell['label']} — {half} half",loc='left',fontsize=12,fontweight='bold',pad=10)
                ax.text(.03,.94,f"Mean {cell['mean']:.1f}  |  SD {cell['sd']:.1f}\n95% interval: {cell['p025']}–{cell['p975']}\nFull sample IQ: {cell['full_sample_iq']}",
                        transform=ax.transAxes,va='top',fontsize=10)
                ax.set_xlim(65,140);ax.set_ylim(0,106)
                ax.set_xticks(range(70,141,10));ax.set_yticks([0,25,50,75,100])
                ax.grid(False);ax.spines[['top','right']].set_visible(False)
                ax.set_ylabel('Simulated draws (%)')
                if r==2:ax.set_xlabel('Reported IQ score')
        fig.suptitle(f"Number correct: 9/15 in each task\n{fmt.capitalize()} participants",fontsize=17,fontweight='bold',y=.98)
        fig.text(.5,.018,'20 draws with replacement within the assigned half · Dashed line: full sample IQ',ha='center',fontsize=10,color='#4b5563')
        fig.tight_layout(rect=(0,.04,1,.93),h_pad=2)
        fig.savefig(OUT/f'{fmt}_iq9_halves.png',dpi=180)
        plt.close(fig)
    simple=[{k:v for k,v in x.items() if k not in ('support','exact_probabilities','simulated_probabilities')} for x in cells]
    for filename,rows in [('summary.csv',simple),('distributions.csv',probability_rows)]:
        with (OUT/filename).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    source_paths=[ROOT/'social_media/__init__.py',ROOT/'social_media/peer_groups.py',
                  ROOT/'social_media/data/peer_reference_initial.fernet',
                  ROOT/'social_media/data/iq_scores_initial.json',
                  ROOT/'social_media/data/iq_distribution_initial.json']
    data=dict(score=SCORE,n=N,simulations_per_cell=DRAWS,seed=SEED,
              source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},cells=cells)
    (OUT/'results.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(simple,indent=2))


if __name__=='__main__':
    main()
