"""Summarize saved quintile/tercile/half counterfactuals without changing the survey."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis/strata_comparison'
DESIGNS = [('quintiles', 'Quintiles (5)', '#315d86'), ('terciles', 'Terciles (3)', '#b1753b'), ('halves', 'Halves (2)', '#61666e')]
TASKS = [('sequences','Numerical reasoning'), ('working_memory','Working memory'), ('ravens','Abstract reasoning')]
FORMATS = ['quantitative','qualitative']


def compile_results():
    designs = []
    for name, label, color in DESIGNS:
        source = json.loads((OUT/name/'results.json').read_text())
        rows=[]
        for r in source['mixtures']:
            parts=[c['outcomes'][r['score']] for c in source['cells'] if c['task']==r['task'] and c['format']==r['format']]
            mass={}
            for part in parts:
                for x,p in zip(part['support'],part['probabilities']):
                    mass[x]=mass.get(x,0)+p/source['strata']
            support=sorted(mass)
            probabilities=[mass[x] for x in support]
            assert np.isclose(sum(probabilities),1)
            assert np.isclose(sum(x*p for x,p in zip(support,probabilities)),r['mean'])
            rows.append(dict(r,support=support,probabilities=probabilities))
        designs.append(dict(name=name,label=label,strata=source['strata'],rows=rows,cells=source['cells'],
                            message_sampling_policy=source.get('message_sampling_policy','legacy_draw_members'),
                            message_results=source['message_results'],max_cdf_error=source['maximum_validation_cdf_error'],
                            draws_per_cell=source['draws_per_cell'],source_hashes=source['source_hashes']))
    assert all(d['source_hashes']==designs[0]['source_hashes'] for d in designs)
    # The generalized five-stratum implementation must reproduce the original
    # exact distributions; message MC now uses matched task orders across designs.
    original=json.loads((ROOT/'analysis/stratified_feedback/results.json').read_text())
    for prior,new in zip(original['mixtures'],designs[0]['rows']):
        for key in ('mean','sd','p025','p975'):
            assert np.isclose(prior[key],new[key]),(key,prior,new)
    result=dict(group_size=20,seed=20261027,profile_task_order_seed=20261028,designs=designs)
    (OUT/'comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    return result


def focal(design,task,fmt):
    return min((r for r in design['rows'] if r['task']==task and r['format']==fmt),key=lambda r:abs(r['full_sample_iq']-100))


def plots(data):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':False})
    fig,axes=plt.subplots(3,2,figsize=(11,10),sharey=True)
    for i,(task,label) in enumerate(TASKS):
        for j,fmt in enumerate(FORMATS):
            ax=axes[i,j]
            vals=[focal(d,task,fmt)['sd'] for d in data['designs']]
            bars=ax.bar(range(3),vals,color=[v[2] for v in DESIGNS],width=.6)
            ax.bar_label(bars,fmt='%.2f',padding=3)
            r=focal(data['designs'][0],task,fmt)
            ax.set(xticks=range(3),xticklabels=['Quintiles','Terciles','Halves'],ylim=(0,30),ylabel='Displayed IQ SD (points)',title=f"{label} · {fmt}\nNumber correct {r['score']}/15 at IQ {r['full_sample_iq']}")
    fig.suptitle('Wider performance strata reduce IQ spread only modestly near full sample IQ 100',fontsize=14)
    fig.text(.08,.012,'Exact mixtures: each stratum is equally likely; N=20 with replacement. Source: actual pilot data.\nQuantitative-only eligibility is applied after forming full-domain strata; qualitative pools retain all formats.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(OUT/'spread_comparison.png',dpi=180);plt.close(fig)
    for fmt in FORMATS:
        fig,axes=plt.subplots(3,3,figsize=(13,10),sharex=True,sharey=True)
        for i,(task,label) in enumerate(TASKS):
            for j,d in enumerate(data['designs']):
                r=focal(d,task,fmt);ax=axes[i,j]
                ax.bar(r['support'],100*np.array(r['probabilities']),color=DESIGNS[j][2],width=.85)
                ax.axvline(r['full_sample_iq'],color='#333333',ls='--',lw=1)
                ax.set(xlim=(60,140),ylim=(0,55),xlabel='Displayed IQ (points)',ylabel='Probability (%)',
                       title=f"{label} · {d['label']}\nMean {r['mean']:.1f} · SD {r['sd']:.1f}\n95% {r['p025']:.0f}–{r['p975']:.0f}")
        fig.suptitle(f'{fmt.capitalize()} messages: IQ distributions across equally likely strata',fontsize=14)
        fig.text(.07,.012,'N=20 with replacement. Dashed: full sample IQ (100 working memory; 101 numerical/abstract reasoning).\nOwn number correct: working memory 8/15; numerical 9/15; abstract 7/15. Exact distributions, actual pilot data.',fontsize=9)
        fig.tight_layout(rect=(0,.05,1,.95));fig.savefig(OUT/f'{fmt}_distributions.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(11,11),sharex=True,sharey=True)
    for i,(task,label) in enumerate(TASKS):
        for j,fmt in enumerate(FORMATS):
            ax=axes[i,j]
            for d,(_,legend,color) in zip(data['designs'],DESIGNS):
                rows=[r for r in d['rows'] if r['task']==task and r['format']==fmt]
                ax.plot([r['score'] for r in rows],[r['sd'] for r in rows],color=color,label=legend)
            ax.set(title=f'{label} · {fmt}',xlabel='Own number correct (out of 15)',ylabel='Displayed IQ SD (points)',xticks=range(0,16,3),ylim=(0,31))
    axes[0,0].legend()
    fig.suptitle('The reduction in IQ spread depends on own performance',fontsize=15)
    fig.text(.08,.012,'Exact mixtures over equally likely strata; N=20 with replacement. Source: actual initial-pilot pools.\nThese are feedback-distribution SDs, not uncertainty about a participant’s true IQ.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.95));fig.savefig(OUT/'spread_by_own_score.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,8),sharey=True)
    for i,fmt in enumerate(FORMATS):
        for j,slot in enumerate((1,2)):
            ax=axes[i,j]
            vals=[100*next(r for r in d['message_results'] if r['format']==fmt and r['social_period_number']==slot)['probability_all_three'] for d in data['designs']]
            bars=ax.bar(range(3),vals,color=[v[2] for v in DESIGNS],width=.6)
            ax.bar_label(bars,labels=[f'{v:.1f}%' for v in vals],padding=3)
            ax.set(xticks=range(3),xticklabels=['Quintiles','Terciles','Halves'],ylim=(0,113),ylabel='Profiles receiving all 3 messages (%)',title=f'{fmt.capitalize()} · social period {slot}')
    fig.suptitle('Availability of three distinct messages per social period',fontsize=15)
    fig.text(.08,.015,'2,000 matched profiles per format/design; actual no-repeat message selector; N=20 with replacement.\nAssumes social/control/social and all three tasks completed. 100% means all simulated profiles, not a guarantee.',fontsize=9)
    fig.tight_layout(rect=(0,.07,1,.95));fig.savefig(OUT/'message_availability.png',dpi=180);plt.close(fig)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=OUT)
    OUT=parser.parse_args().output
    data=compile_results();plots(data)
    print('Verified source identity and exact quintile replication; saved comparison JSON and 5 comparison PNGs.')
    for d in data['designs']:
        print(d['name'], [(task,fmt,round(focal(d,task,fmt)['sd'],2)) for task,_ in TASKS for fmt in FORMATS])
