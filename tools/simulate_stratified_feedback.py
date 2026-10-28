"""Linked-pilot stratification counterfactuals; aggregate-only, no database writes.

Run with PEER_REFERENCE_KEY available in .env: python tools/simulate_stratified_feedback.py
Use --strata 2/3/5 and --output to compare halves, terciles and quintiles.
Exports no reference identities, messages, or image data. N=20 with replacement.
"""
import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.special import ndtri
from scipy.stats import multinomial
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['EXPERIMENT_PILOT'] = 'iq'
os.environ['OTREE_IN_MEMORY'] = '1'
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
import social_media as survey
from social_media.peer_groups import reference, group_for, message_for, averages, message_fingerprint, stratum_records_for

OUT = ROOT / 'analysis' / 'stratified_feedback'
TASKS = ['sequences', 'working_memory', 'ravens']
FORMATS = ['quantitative', 'qualitative']
N = survey.IQ_COMPARISON_GROUP
SEED = 20261027
STATES = np.array([(b, t, N-b-t) for b in range(N+1) for t in range(N-b+1)])
GROUP_IQ = 100 + 15 * ndtri(np.clip((STATES[:, 0] + .5*STATES[:, 1])/N, .5/N, 1-.5/N))
COLORS = ['#254b72', '#507ca3', '#849cb0', '#b88452', '#874b2d']


def fake_player(code, task_order, fmt):
    return SimpleNamespace(round_number=5, participant=SimpleNamespace(code=code, vars={
        'linked_peer_groups': True, 'period_tasks': task_order, 'social_type': fmt + '_social',
        'peer_group_sampling': 'quantitative_only_v1'}))


def probability_summary(values, probabilities):
    p = probabilities / probabilities.sum()
    mean = float(values @ p)
    cdf = np.cumsum(p)
    return dict(mean=mean, sd=float(np.sqrt((values-mean)**2 @ p)),
                p025=float(values[np.searchsorted(cdf, .025)]),
                p975=float(values[np.searchsorted(cdf, .975)]))


def pmf(values, weights):
    support, reverse = np.unique(values, return_inverse=True)
    probability = np.bincount(reverse, weights=weights, minlength=len(support))
    keep = probability > 0
    return support[keep], probability[keep]


def finite_summary(values):
    values = values[np.isfinite(values)]
    if not len(values):
        return None
    lo, hi = np.quantile(values, [.025, .975])
    return dict(mean=float(values.mean()), sd=float(values.std()), p025=float(lo), p975=float(hi))


def ratios(numerator, denominator):
    return np.divide(numerator, denominator, out=np.full(len(numerator), np.nan), where=denominator != 0)


def stratified_group(player, period, pools, strata):
    """Analysis-only counterfactual; the live survey still assigns quintiles."""
    task = player.participant.vars['period_tasks'][period-1]
    rows = sorted(pools[task], key=lambda r: (r['score'], hashlib.sha256((task+r['id']).encode()).hexdigest()))
    rng = random.Random(f'{player.participant.code}-peer-group-{period}-{task}')
    stratum = rng.randrange(strata)
    eligible = rows[len(rows)*stratum//strata:len(rows)*(stratum+1)//strata]
    if player.participant.vars['social_type'] == 'quantitative_social':
        eligible = [r for r in eligible if len(r['blocks']) == 3 and all(b['report'] is not None for b in r['blocks'])]
    draws = rng.choices(eligible, k=N)
    snapshot = dict(task=task, stratum=stratum+1, strata=strata, reference_source='initial',
                    replacement=True, draw_ids=[r['id'] for r in draws], scores=[r['score'] for r in draws])
    if strata == 5:
        live = group_for(player, period)
        assert live['draw_ids'] == snapshot['draw_ids'] and live['quintile'] == stratum+1
    player.participant.vars.setdefault('peer_groups', {})[str(period)] = snapshot
    return snapshot


def simulate(draws, profiles, strata=5):
    # Check the vectorized inverse-normal helper against the actual survey helper
    # for every attainable mid-rank percentile, including both clipped endpoints.
    for state, expected in zip(STATES, GROUP_IQ):
        sample = [4]*int(state[0]) + [5]*int(state[1]) + [6]*int(state[2])
        assert np.isclose(survey._percentile_iq(sample, 5), expected, atol=1e-10, rtol=0)
    pools = reference('initial')
    full_scores = survey.iq_reference_scores()
    rng = np.random.default_rng(SEED)
    cells, mixtures = [], []
    max_cdf_error = 0.
    for task in TASKS:
        full = sorted(pools[task], key=lambda r: (r['score'], hashlib.sha256((task+r['id']).encode()).hexdigest()))
        component = survey.TASK_IQ_COMPONENT[task]
        for fmt in FORMATS:
            for q in range(strata):
                stratum = full[len(full)*q//strata:len(full)*(q+1)//strata]
                eligible = stratum if fmt == 'qualitative' else [r for r in stratum if len(r['blocks']) == 3 and all(b['report'] is not None for b in r['blocks'])]
                # MC identity counts retain repeated draws in all weighted means.
                counts = rng.multinomial(N, np.ones(len(eligible))/len(eligible), size=draws).astype(np.int16)
                scores = np.array([r['score'] for r in eligible])
                assert np.all(counts.sum(axis=1) == N)
                unique = (counts > 0).sum(axis=1)
                names = sorted({m['name'].strip().casefold() for r in eligible for m in r['messages'] if m['kind'] == fmt})
                membership = np.array([[any(m['name'].strip().casefold() == name and m['kind'] == fmt for m in r['messages']) for name in names] for r in eligible], dtype=np.int16)
                sender_count = ((counts @ membership) > 0).sum(axis=1) if names else np.zeros(draws)
                stratum_messages = {message_fingerprint(m): m for r in stratum for m in r['messages'] if m['kind'] == fmt}
                actual = counts @ scores / N
                if fmt == 'quantitative':
                    number_sent = np.array([sum(b['sent'] for b in r['blocks']) for r in eligible])
                    reported_sum = np.array([sum(b['report'] for b in r['blocks'] if b['sent']) for r in eligible])
                    actual_sent_sum = np.array([sum(b['score'] for b in r['blocks'] if b['sent']) for r in eligible])
                    sent_n = counts @ number_sent
                    reported = 3*ratios(counts @ reported_sum, sent_n)
                    sent_actual = 3*ratios(counts @ actual_sent_sum, sent_n)
                    selection = sent_actual - actual
                    misreporting = reported - sent_actual
                    gap = reported - actual
                    valid = np.isfinite(gap)
                    assert np.allclose(gap[valid], (selection+misreporting)[valid])
                    nonzero = valid & ~np.isclose(gap, 0, atol=1e-10, rtol=0)
                    share = ratios(100*selection, np.where(nonzero, gap, 0))
                    correction = dict(actual=finite_summary(actual), reported=finite_summary(reported),
                                      gap=finite_summary(gap), selection=finite_summary(selection),
                                      misreporting=finite_summary(misreporting),
                                      unavailable_rate=float((~valid).mean()),
                                      zero_gap_rate_among_available=float((~nonzero[valid]).mean()) if valid.any() else None,
                                      share_outside_0_100_rate_among_nonzero=float(((share[nonzero] < -1e-8) | (share[nonzero] > 100+1e-8)).mean()) if nonzero.any() else None)
                else:
                    blocks = [[b for b in r['blocks'] if b.get('emoji')] for r in eligible]
                    composed_n = np.array([len(bs) for bs in blocks])
                    sent_n = np.array([sum(b['sent'] for b in bs) for bs in blocks])
                    happy_n = np.array([sum(b['emoji'] == '😃' for b in bs) for bs in blocks])
                    sent_happy_n = np.array([sum(b['sent'] and b['emoji'] == '😃' for b in bs) for bs in blocks])
                    reported = 100*ratios(counts @ sent_happy_n, counts @ sent_n)
                    all_written = 100*ratios(counts @ happy_n, counts @ composed_n)
                    correction = dict(reported=finite_summary(reported), actual=finite_summary(all_written),
                                      gap=finite_summary(reported-all_written),
                                      unavailable_rate=float((~np.isfinite(reported) | ~np.isfinite(all_written)).mean()))
                outcomes = []
                for score in range(16):
                    baseline = survey.estimate_iq(component, score, 15)
                    full_iq = survey._percentile_iq(full_scores[component], score)
                    probabilities = multinomial.pmf(STATES, N, [np.mean(scores < score), np.mean(scores == score), np.mean(scores > score)])
                    assert np.isclose(probabilities.sum(), 1)
                    raw_offsets = GROUP_IQ - full_iq
                    rounded = np.sign(raw_offsets)*np.floor(np.abs(raw_offsets)+.5)
                    support, prob = pmf(baseline + rounded, probabilities)
                    stat = probability_summary(support, prob)
                    raw_mean = float(raw_offsets @ probabilities)
                    outcome = dict(score=score, full_sample_iq=baseline, full_pool_percentile_iq=full_iq,
                                   **stat, raw_offset_mean=raw_mean,
                                   raw_offset_sd=float(np.sqrt((raw_offsets-raw_mean)**2 @ probabilities)),
                                   mean_adjustment=stat['mean']-baseline,
                                   probability_over_10_points=float(prob[np.abs(support-baseline)>10].sum()),
                                   support=support.astype(int).tolist(), probabilities=prob.tolist())
                    # Validate the exact distribution against identity-level MC.
                    if score in {min(range(16), key=lambda s: abs(survey.estimate_iq(component,s,15)-target)) for target in (85,100,115)}:
                        below = counts @ (scores < score).astype(int)
                        ties = counts @ (scores == score).astype(int)
                        offset = 100+15*ndtri(np.clip((below+.5*ties)/N,.5/N,1-.5/N))-full_iq
                        observed = baseline+np.sign(offset)*np.floor(np.abs(offset)+.5)
                        error = max(abs(np.mean(observed <= x)-np.sum(prob[support <= x])) for x in support)
                        max_cdf_error = max(max_cdf_error, float(error))
                        assert error < .01, (task, fmt, q, score, error)
                    outcomes.append(outcome)
                cells.append(dict(task=task, label=survey.TASK_LABELS[task], format=fmt, stratum=q+1,
                                  **({'quintile':q+1} if strata == 5 else {}),
                                  full_linked_pool=len(full), full_iq_pool=len(full_scores[component]),
                                  stratum_size=len(stratum), eligible_size=len(eligible),
                                  eligible_score_min=int(scores.min()), eligible_score_max=int(scores.max()),
                                  unique_peers_mean=float(unique.mean()),
                                  unique_peers_expected=float(len(eligible)*(1-(1-1/len(eligible))**N)),
                                  available_distinct_senders_mean=float(sender_count.mean()),
                                  fewer_than_three_senders_rate=float(np.mean(sender_count < 3)),
                                  stratum_distinct_messages=len(stratum_messages),
                                  stratum_message_senders=len({m['name'].strip().casefold() for m in stratum_messages.values()}),
                                  correction=correction, outcomes=outcomes))
            chosen = [c for c in cells if c['task']==task and c['format']==fmt]
            for score in range(16):
                parts = [c['outcomes'][score] for c in chosen]
                means = np.array([x['mean'] for x in parts])
                within = float(np.mean([x['sd']**2 for x in parts]))
                between = float(means.var())
                support, prob = pmf(np.concatenate([x['support'] for x in parts]), np.concatenate([np.array(x['probabilities'])/strata for x in parts]))
                stat = probability_summary(support, prob)
                assert np.isclose(stat['sd']**2, within+between)
                mixtures.append(dict(task=task, format=fmt, score=score, full_sample_iq=parts[0]['full_sample_iq'],
                                     **stat, within_stratum_variance=within, between_stratum_variance=between,
                                     **(dict(within_quintile_variance=within, between_quintile_variance=between) if strata==5 else {}),
                                     between_fraction=between/(within+between) if within+between > 1e-12 else None))
        print('Simulated', task, flush=True)
    # Use the actual message selector for two social periods separated by control.
    # This captures the across-period no-repeat-message rule (counts above
    # still describe distinct senders, not available distinct messages).
    message_results = []
    # Separate stream gives each design the same task orders for these profiles.
    profile_rng = np.random.default_rng(SEED + 1)
    for fmt in FORMATS:
        by_slot = [[], []]
        for i in range(profiles):
            order = list(profile_rng.permutation(TASKS))
            p = fake_player(f'stratified-{SEED}-{fmt}-{i}', order, fmt)
            used_messages = set()
            for slot, period in enumerate((1, 3)):
                stratified_group(p, period, pools, strata)
                group_before = dict(group_for(p, period))
                stratum_ids = {r['id'] for r in stratum_records_for(p, period)}
                seen = 0
                for block in range(1, 4):
                    p.round_number = (period-1)*15+block*5
                    group_for(p, period)
                    message = message_for(p, fmt)
                    if message:
                        assert message['id'].split('-')[0] in stratum_ids
                        assert message['fingerprint'] not in used_messages
                        assert message['sampling_policy'] == 'performance_stratum_messages_v1'
                        used_messages.add(message['fingerprint'])
                        seen += 1
                assert group_for(p, period) == group_before
                by_slot[slot].append(seen)
            # Validate a real draw's average against its records through the live helper.
            if i < 10:
                r = averages(p, 1)
                if fmt == 'quantitative':
                    assert np.isclose(r['actual'], np.mean(group_for(p,1)['scores']))
                p.round_number = 15
                component = survey.TASK_IQ_COMPONENT[order[0]]
                for own_score in range(16):
                    group = group_for(p, 1)
                    offset = survey._percentile_iq(group['scores'], own_score) - survey._percentile_iq(full_scores[component], own_score)
                    expected = survey.estimate_iq(component, own_score, 15) + int(np.sign(offset)*np.floor(abs(offset)+.5))
                    assert survey.estimate_iq_for_player(p, component, own_score, 15) == expected
        for slot, counts in enumerate(by_slot):
            counts = np.array(counts)
            message_results.append(dict(format=fmt, social_period_number=slot+1, profiles=profiles,
                                        mean_messages=float(counts.mean()), probability_all_three=float(np.mean(counts==3)),
                                        probability_no_messages=float(np.mean(counts==0)),
                                        probabilities_0_1_2_3=[float(np.mean(counts==n)) for n in range(4)]))
    return dict(seed=SEED, strata=strata, draws_per_cell=draws, group_size=N, cells=cells, mixtures=mixtures,
                message_sampling_policy='performance_stratum_messages_v1',
                message_results=message_results, maximum_validation_cdf_error=max_cdf_error,
                source_hashes={name:hashlib.sha256((ROOT/'social_media/data'/name).read_bytes()).hexdigest()
                               for name in ('peer_reference_initial.fernet','iq_scores_initial.json','iq_distribution_initial.json')})


def plots(data, output=OUT):
    strata = data.get('strata', 5)
    unit = {2:'half', 3:'tercile', 5:'quintile'}[strata]
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False, 'axes.grid':False})
    for task in TASKS:
        fig, axes = plt.subplots(strata, 2, figsize=(12, 2.5*strata+1.5), sharey=True)
        for col, fmt in enumerate(FORMATS):
            for q in range(1, strata+1):
                c = next(c for c in data['cells'] if c['task']==task and c['format']==fmt and c.get('stratum', c.get('quintile'))==q)
                r = min(c['outcomes'], key=lambda r: abs(r['full_sample_iq']-100))
                ax = axes[q-1, col]
                ax.bar(r['support'], 100*np.array(r['probabilities']), width=.85, color=COLORS[q-1])
                ax.axvline(r['full_sample_iq'], color='#333333', ls='--', lw=1)
                ax.set(xlim=(55,150), ylim=(0,105), xlabel='Displayed IQ (points)', ylabel='Probability (%)')
                ax.set_title(f"{fmt.capitalize()} · {unit} {q} · {c['eligible_size']} eligible peers\nMean {r['mean']:.1f} · SD {r['sd']:.1f} · 95% {r['p025']:.0f}–{r['p975']:.0f}", loc='left', fontsize=10)
        fig.suptitle(f"{survey.TASK_LABELS[task]}: number correct {r['score']}/15 at IQ {r['full_sample_iq']}\nN=20 with replacement within one assigned {unit}", fontsize=15)
        fig.text(.08,.012,'Exact distribution from actual pilot data. Dashed line: full sample IQ (calibrated, before adjustment).\nQuantitative pools are restricted within full-domain strata; qualitative pools contain all message formats.', fontsize=10)
        fig.tight_layout(rect=(0,.05,1,.94))
        fig.savefig(output/f'{task}_iq100.png', dpi=170)
        plt.close(fig)
    fig, axes = plt.subplots(3,2,figsize=(12,12),sharex=True,sharey=True)
    for row, task in enumerate(TASKS):
        for col, fmt in enumerate(FORMATS):
            ax=axes[row,col]
            for q in range(1,strata+1):
                c=next(c for c in data['cells'] if c['task']==task and c['format']==fmt and c.get('stratum', c.get('quintile'))==q)
                ax.plot([r['score'] for r in c['outcomes']], [r['mean_adjustment'] for r in c['outcomes']], color=COLORS[q-1],label=f'{unit.capitalize()} {q}')
            ax.axhline(0,color='#777777',lw=.7)
            ax.set(title=f'{survey.TASK_LABELS[task]} · {fmt}', xlabel='Own number correct (out of 15)', ylabel='Mean IQ adjustment (points)', xticks=range(0,16,3))
    axes[0,0].legend(fontsize=9, ncol=2)
    fig.suptitle(f'The assigned {unit} changes the IQ adjustment differently across own scores',fontsize=15)
    fig.text(.08,.012,'Exact expectation, N=20 with replacement. Adjustment is relative to the calibrated full sample IQ.\nSource: linked initial-pilot reference data and current survey calibration; 27 October 2026.',fontsize=10)
    fig.tight_layout(rect=(0,.05,1,.96)); fig.savefig(output/'mean_adjustment_by_score.png',dpi=170); plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(12,10))
    for row,task in enumerate(TASKS):
        for col,fmt in enumerate(FORMATS):
            candidates=[r for r in data['mixtures'] if r['task']==task and r['format']==fmt]
            chosen=[min(candidates,key=lambda r:abs(r['full_sample_iq']-target)) for target in (85,100,115)]
            within=np.array([r['within_stratum_variance'] for r in chosen]); between=np.array([r['between_stratum_variance'] for r in chosen])
            ax=axes[row,col]; ax.bar(range(3),within,label=f'Within assigned {unit}',color='#91a9bf'); ax.bar(range(3),between,bottom=within,label='Between assigned strata',color='#254b72')
            ax.set(xticks=range(3),xticklabels=[str(r['full_sample_iq']) for r in chosen],xlabel='Full sample IQ (nearest to 85, 100, 115)',ylabel='Displayed IQ variance (points²)',title=f'{survey.TASK_LABELS[task]} · {fmt}')
    axes[0,0].legend(fontsize=9)
    fig.suptitle(f'Sources of IQ-feedback variation when each {unit} is equally likely',fontsize=15)
    fig.text(.08,.01,'Exact law-of-total-variance decomposition. Source: actual initial-pilot pools; N=20 with replacement.',fontsize=10)
    fig.tight_layout(rect=(0,.04,1,.95)); fig.savefig(output/'variance_sources.png',dpi=170); plt.close(fig)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--draws',type=int,default=100_000)
    parser.add_argument('--profiles',type=int,default=2_000)
    parser.add_argument('--strata',type=int,choices=(2,3,5),default=5)
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    data=simulate(args.draws,args.profiles,args.strata)
    (args.output/'results.json').write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
    plots(data,args.output)
    print('Saved aggregate results and five PNGs to',args.output)
    print('Maximum exact-vs-Monte-Carlo CDF error:',data['maximum_validation_cdf_error'])
