"""Reference membership, repeat prevention, numerical truth and image validation."""
import os
import sys
import math
import hashlib
import io
import base64
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['EXPERIMENT_PILOT'] = 'iq'
os.environ['OTREE_IN_MEMORY'] = '1'
from PIL import Image
import social_media as survey
from social_media.peer_groups import group_for, records_for, message_for, averages, reference
from social_media.new_pages import SelfieCapture, AverageBeliefs, AverageTruth


def player(code, kind='quantitative_social'):
    return SimpleNamespace(round_number=5, id_in_group=1,
                           participant=SimpleNamespace(code=code, vars={
                               'linked_peer_groups':True, 'period_tasks':['sequences','working_memory','ravens'],
                               'social_type':kind, 'image_treatment':'selfie',
                               'peer_group_sampling':'quantitative_only_v1'}))


unavailable = 0
seen_quintiles = set()
for kind in ('quantitative_social', 'qualitative_social'):
    for i in range(200):
        p = player(str(i),kind)
        fingerprints = set()
        senders = set()
        for period in range(1,4):
            group = group_for(p,period)
            seen_quintiles.add(group['quintile'])
            assert len(group['draw_ids']) == 20 and group == group_for(p,period)
            records = records_for(p,period)
            assert group['scores'] == [r['score'] for r in records]
            pool = sorted(reference(group['reference_source'])[group['task']], key=lambda r:
                          (r['score'], hashlib.sha256((group['task']+r['id']).encode()).hexdigest()))
            q=group['quintile']-1
            eligible=pool[len(pool)*q//5:len(pool)*(q+1)//5]
            assert set(group['draw_ids']) <= {r['id'] for r in eligible}
            if kind=='quantitative_social':
                assert group['sampling_policy']=='quantitative_only_v1'
                assert all(len(r['blocks'])==3 and all(b['report'] is not None for b in r['blocks']) for r in records)
                assert all(sum(b['score'] for b in r['blocks']) == r['score'] for r in records)
            else:
                assert group['sampling_policy']=='all_message_formats'
            for block in range(1,4):
                p.round_number=(period-1)*15+block*5
                message=message_for(p, 'quantitative' if kind=='quantitative_social' else 'qualitative')
                assert message == message_for(p, 'quantitative' if kind=='quantitative_social' else 'qualitative')
                if message:
                    assert message['id'].split('-')[0] in group['draw_ids']
                    assert message['fingerprint'] not in fingerprints
                    fingerprints.add(message['fingerprint'])
                    assert message['name'].strip().casefold() not in senders
                    senders.add(message['name'].strip().casefold())
            result=averages(p,period)
            if result['reported'] is None:
                unavailable+=1
            elif result['kind']=='score':
                assert result['numeric_blocks']==60
                assert math.isclose(result['actual'],sum(r['score'] for r in records)/20)
                assert math.isclose(result['reporting_subset'],0,abs_tol=1e-10)
                assert math.isclose(result['reported']-result['actual'],
                                    result['selection']+result['misreporting'],abs_tol=1e-10)
            else:
                assert 0 <= result['reported'] <= 100 and 0 <= result['actual'] <= 100
assert seen_quintiles == {1,2,3,4,5}
# Historical sampling and already-recorded groups must not be rewritten.
p=player('legacy'); p.participant.vars.pop('peer_group_sampling')
original=group_for(p,1)
assert original['sampling_policy']=='all_message_formats'
p.participant.vars['peer_group_sampling']='quantitative_only_v1'
assert group_for(p,1)==original
# The IQ adjustment uses the same group scores as the messages/averages.
p=player('iq-linked'); p.round_number=15
group=group_for(p,1)
with patch.object(survey,'_percentile_iq',return_value=100) as percentile:
    survey.iq_noise_offset(p,survey.TASK_IQ_COMPONENT['sequences'],9)
    assert percentile.call_args_list[0].args[0]==group['scores']
p=player('image')
assert 'error' in SelfieCapture.live_method(p,{'action':'confirm','image':'data:image/jpeg;base64,evil'})[1]
output=io.BytesIO(); Image.new('RGB',(512,512),'blue').save(output,'JPEG')
data='data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode()
assert SelfieCapture.live_method(p,{'action':'confirm','image':data})[1]['saved']
assert p.participant.vars['selfie']['blur']==10
assert SelfieCapture.error_message(p,{}) is None
from tools.manage_selfies import main as manage_selfies
with patch('otree.main.setup'), patch('otree.database.db') as database, patch.object(sys,'argv',['manage_selfies','--delete','image']):
    database.query.return_value.all.return_value = [p.participant]
    manage_selfies()
    assert 'image' not in p.participant.vars['selfie']
    assert 'deleted_at' in p.participant.vars['selfie']
    database.commit.assert_called_once()
toggle_player = SimpleNamespace(session=SimpleNamespace(config={'reaction_feedback_enabled':True}))
with patch.dict(os.environ, {'ENABLE_REACTION_FEEDBACK':'0'}):
    assert not survey.reaction_feedback_enabled(toggle_player)
with patch.dict(os.environ, {'ENABLE_REACTION_FEEDBACK':'1'}):
    assert survey.reaction_feedback_enabled(toggle_player)
    toggle_player.session.config['reaction_feedback_enabled']=False
    assert not survey.reaction_feedback_enabled(toggle_player)
for show_iq in (False,True):
    positions=set()
    with patch.dict(survey.CFG,show_iq=show_iq), patch.object(survey,'period_correct',return_value=3), patch.object(survey,'switched_disqualified_count',return_value=0), patch.object(survey,'round_spec',return_value={'task':'sequences'}):
        for i in range(60):
            p=player('order-'+str(i));p.round_number=15 if i%2 else 30
            context=survey.EndOfPeriodSurvey.vars_for_template(p)
            order=context['question_order']
            assert order.count('difficulty')==1
            assert order==survey.EndOfPeriodSurvey.vars_for_template(p)['question_order']
            positions.add(order.index('difficulty'))
        assert positions==set(range(6 if show_iq else 5)),positions
        p.participant.vars.pop('image_treatment')
        assert 'difficulty' not in survey.EndOfPeriodSurvey.vars_for_template(p)['question_order']
for kind in ('qualitative_social','quantitative_social'):
    p=player('belief',kind)
    with patch('social_media.new_pages.completed_periods',return_value=[1,2]):
        context = AverageBeliefs.vars_for_template(p)
        assert all('actual' not in row and 'actual_text' not in row for row in context['rows'])
        assert 'error' in AverageBeliefs.live_method(p,{'1':'nan','2':'nan'})[1]
        assert 'error' in AverageBeliefs.live_method(p,{'1':'','2':''})[1]
        assert AverageBeliefs.live_method(p,{'1':5,'2':5})[1]['saved']
# The displayed gap includes composition as well as sending and misreporting.
# Its sending share must not silently use a different denominator or be capped.
for reported, actual, selection, expected in [
    (12, 8, 2, '50'), (8, 12, -2, '50'),
    (10, 8, 3, '150'), (10, 8, -1, '-50'), (8, 8, 1, ''),
]:
    row = dict(period=1, kind='score', available=True, reported=reported, actual=actual,
               selection=selection, misreporting=1, reporting_subset=reported-actual-selection-1)
    with patch('social_media.new_pages.average_rows', return_value=[row]):
        result = AverageTruth.vars_for_template(player('correction'))['rows'][0]
    assert result['selection_percent'] == expected
    assert result['has_gap'] == (reported != actual)
print(f'Passed 400 participant plans / 1,200 groups; {unavailable} groups lacked a sent report and were explicitly marked unavailable. Correction percentages passed, including zero and offsetting gaps.')
