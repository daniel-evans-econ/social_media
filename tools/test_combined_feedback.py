"""Submission ordering, disclosure, half sampling, thumbnail and debrief checks."""
import base64
import copy
import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['OTREE_IN_MEMORY'] = '1'
os.environ['EXPERIMENT_PILOT'] = 'iq'
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')
from PIL import Image
import social_media as survey
from social_media.new_pages import AverageBeliefs, AverageTruth, AverageOutcomes, SelfieCapture
from social_media.peer_groups import group_for, records_for, stratum_records_for, message_for


def player(code='combined', kind='quantitative_social', truth=True):
    return SimpleNamespace(id_in_group=1, round_number=45, participant=SimpleNamespace(
        code=code, period_1_condition=kind, period_2_condition='control', vars=dict(
            combined_average_flow=True, linked_peer_groups=True, peer_group_strata=2,
            peer_group_sampling='quantitative_only_v1', social_type=kind, reveal_truth=truth,
            quantitative_estimate_incentive=True, qualitative_target='private_satisfaction_v1',
            period_tasks=['sequences','working_memory','ravens'],
            average_period_selection=dict(period=1), image_treatment='selfie',
            full_sample_iq_debrief=True, like_treatment=False)))


for kind,actual,guess in [('score',8.7,8), ('satisfaction',25,30)]:
    row=dict(period=1,kind=kind,reported=10 if kind=='score' else 40,reported_text='10.0' if kind=='score' else '40.0',
             actual=actual,actual_text=str(actual),available=True,task_label='Numerical reasoning',
             incentive_amount=.25,incentive_tolerance=1 if kind=='score' else 10)
    for truth in (False,True):
        p=player(kind='quantitative_social' if kind=='score' else 'qualitative_social', truth=truth)
        with patch('social_media.new_pages.average_rows',return_value=[row]):
            before=AverageBeliefs.vars_for_template(p)
            assert not before['submitted'] and before['rows'][0]['revealed_actual']==''
            assert 'actual' not in before['rows'][0] and 'actual_text' not in before['rows'][0]
            assert not AverageTruth.is_displayed(p) and not AverageOutcomes.is_displayed(p)
            assert AverageBeliefs.error_message(p,{})
            outcomes=dict(mood=3,satisfaction_1=4,iq_perception=3,human_nature=2)
            assert 'error' in AverageBeliefs.live_method(p,dict(action='outcomes',answers=outcomes))[1]
            response=AverageBeliefs.live_method(p,dict(action='belief',answers={'1':guess}))[1]
            assert response['saved'] and response['stage']=='belief'
            assert bool(response['corrections'])==truth
            after=AverageBeliefs.vars_for_template(p)
            assert after['submitted'] and after['rows'][0]['guess']==guess
            assert bool(after['rows'][0]['revealed_actual'])==truth
            assert AverageBeliefs.error_message(p,{})
            assert 'error' in AverageBeliefs.live_method(p,dict(action='belief',answers={'1':guess+1}))[1]
            assert AverageBeliefs.live_method(p,dict(action='belief',answers={'1':guess}))[1]==response
            assert p.participant.vars['average_belief_bonus']['amount']==.25
            assert 'error' in AverageBeliefs.live_method(p,dict(action='outcomes',answers=dict(outcomes,human_nature=True)))[1]
            assert AverageBeliefs.live_method(p,dict(action='outcomes',answers=outcomes))[1]['saved']
            assert AverageBeliefs.error_message(p,{}) is None
            assert p.participant.vars['average_outcomes']==outcomes

# No sent reports: unlock the common outcome questions without a fabricated
# statistic or reward. Even the empty guess has a stable submission state.
p=player()
with patch('social_media.new_pages.average_rows',return_value=[dict(row,available=False,reported=None,actual=None)]):
    response=AverageBeliefs.live_method(p,dict(action='belief',answers={}))[1]
    assert response['saved'] and response['corrections']==[]

seen=set(); missing=0
for kind in ('quantitative_social','qualitative_social'):
    for i in range(200):
        p=player(str(i),kind); used=set()
        for period in (1,2,3):
            group=group_for(p,period); seen.add(group['stratum'])
            assert group['strata']==2 and 'quintile' not in group
            assert len(group['scores'])==20 and group==group_for(p,period)
            records=records_for(p,period); eligible=stratum_records_for(p,period)
            assert set(group['draw_ids']) <= {r['id'] for r in eligible}
            if kind=='quantitative_social':
                assert all(len(r['blocks'])==3 and all(b['report'] is not None for b in r['blocks']) for r in records)
            for block in (1,2,3):
                p.round_number=(period-1)*15+block*5
                m=message_for(p,kind.removesuffix('_social'))
                if not m: missing+=1; continue
                assert m['fingerprint'] not in used; used.add(m['fingerprint'])
        old=copy.deepcopy(p.participant.vars['peer_groups'])
        p.participant.vars['peer_group_strata']=5
        assert all(group_for(p,period)==old[str(period)] for period in (1,2,3))
assert seen=={1,2}

orders=set()
for i in range(100):
    p=player('order-'+str(i))
    order=tuple(q['key'] for q in AverageOutcomes.vars_for_template(p)['questions'])
    assert set(order)=={'mood','satisfaction_1','iq_perception','human_nature'}
    assert order==tuple(q['key'] for q in AverageOutcomes.vars_for_template(p)['questions'])
    orders.add(order)
assert len(orders)==24

for size in (72,512):
    p=player(); raw=io.BytesIO();Image.new('RGB',(size,size),'blue').save(raw,'JPEG')
    assert SelfieCapture.live_method(p,dict(action='confirm',image='data:image/jpeg;base64,'+base64.b64encode(raw.getvalue()).decode()))[1]['saved']
    stored=base64.b64decode(p.participant.vars['selfie']['image'].split(',')[1])
    assert Image.open(io.BytesIO(stored)).size==(72,72)

# Full-sample IQ uses actual correct answers, not bonus-eligible correct answers,
# and excludes the optional task when it was not played.
for accepted in (False,True):
    p=player(); p.in_rounds=lambda start,end: [SimpleNamespace(field_maybe_none=lambda key:True)]*15
    with patch.object(survey,'third_period_played',return_value=accepted), \
         patch.object(survey,'q_answer_earns_bonus',return_value=False), \
         patch.object(survey,'switched_disqualified_count',return_value=0):
        final=survey.FinalResults.vars_for_template(p)
    assert all(r['correct']==0 for r in final['task_rows'])
    assert len(final['debrief_rows'])==(3 if accepted else 2)
    for r in final['debrief_rows']:
        task=p.participant.vars['period_tasks'][r['period']-1]
        assert r['correct']==15 and r['iq']==survey.estimate_iq(survey.TASK_IQ_COMPONENT[task],15,15)
print(f'Passed combined flow, locked bonuses, withheld truth, all 24 item orders, 1,200 half draws, thumbnails and debrief; {missing} unavailable message slots.')
