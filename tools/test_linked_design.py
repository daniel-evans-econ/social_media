"""Reference membership, repeat prevention, numerical truth and image validation."""
import os
import sys
import math
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
from social_media.peer_groups import group_for, records_for, message_for, averages
from social_media.new_pages import SelfieCapture, AverageBeliefs


def player(code, kind='quantitative_social'):
    return SimpleNamespace(round_number=5, id_in_group=1,
                           participant=SimpleNamespace(code=code, vars={
                               'linked_peer_groups':True, 'period_tasks':['sequences','working_memory','ravens'],
                               'social_type':kind, 'image_treatment':'selfie'}))


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
                assert math.isclose(result['reported']-result['actual'],
                                    result['selection']+result['misreporting']+result['reporting_subset'])
            else:
                assert 0 <= result['reported'] <= 100 and 0 <= result['actual'] <= 100
assert seen_quintiles == {1,2,3,4,5}
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
assert survey.avatar_for_name('Sarah23').startswith('feminine')
assert survey.avatar_for_name('JohnSmith').startswith('masculine')
for name in ('Seb', 'seb', 'SEB', 'Seb123', 'Seb_Smith', 'Sebastian'):
    assert survey.avatar_for_name(name).startswith('masculine'), name
assert survey.avatar_for_name('user82')==survey.avatar_for_name('user82')
for kind in ('qualitative_social','quantitative_social'):
    p=player('belief',kind)
    with patch('social_media.new_pages.completed_periods',return_value=[1,2]):
        context = AverageBeliefs.vars_for_template(p)
        assert all('actual' not in row and 'actual_text' not in row for row in context['rows'])
        assert 'error' in AverageBeliefs.live_method(p,{'1':'nan','2':'nan'})[1]
        assert 'error' in AverageBeliefs.live_method(p,{'1':'','2':''})[1]
        assert AverageBeliefs.live_method(p,{'1':5,'2':5})[1]['saved']
print(f'Passed 400 participant plans / 1,200 groups; {unavailable} groups lacked a sent report and were explicitly marked unavailable.')
