"""Check end-of-task ordering and safe continuation of existing sessions."""
import os
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['OTREE_IN_MEMORY']='1'
os.environ['EXPERIMENT_PILOT']='iq'
from otree.database import init_orm
init_orm()
from otree.session import create_session
import social_media as s
from tools.migrate_posttask_order import OLD,NEW,MOVED,OLD_MAX,NEW_MAX,old_final_index,remap,migrate

expected=['Results','TaskEffort','IQCredibility','AverageBeliefs','AverageTruth','AverageOutcomes','BigFiveSurvey1']
start=NEW.index('Results')
assert NEW[start:start+len(expected)]==expected
assert NEW.count('TaskEffort')==NEW.count('IQCredibility')==1
assert 'trust_own_iq_estimate' not in s.Demographics.get_form_fields(None)
assert s.IQCredibility.form_fields==['trust_own_iq_estimate']
for old in range(1,OLD_MAX+1):
    new=remap(old)
    assert (old-1)//len(OLD)==(new-1)//len(NEW)
    assert OLD[(old-1)%len(OLD)]==NEW[(new-1)%len(NEW)]
assert remap(OLD_MAX+1)==NEW_MAX+1 and remap(0)==0 and remap(None) is None

cases=MOVED+['PlatformUsage','FinalResults','IQDebrief','completed','unstarted']
parts=create_session('cognitive_tasks',num_participants=len(cases)+1).get_participants()
for part,name in zip(parts,cases):
    part._max_page_index=OLD_MAX
    part._index_in_pages=(OLD_MAX+1 if name=='completed' else 0 if name=='unstarted' else old_final_index(name))
    part._current_form_page_url=None
    part.vars.pop('posttask_order_version')
    player=part.get_player('social_media',45)
    player.payoff=s.cu(2.25)
    if part._index_in_pages>old_final_index('Demographics'):
        player.trust_own_iq_estimate=3
dry=migrate();assert dry['count']==len(cases)
assert all(part._max_page_index==OLD_MAX for part in parts[:-1])
result=migrate(True);assert result['records']==dry['records']
for part,name in zip(parts,cases):
    player=part.get_player('social_media',45)
    assert float(part.payoff)==2.25 and part._max_page_index==NEW_MAX
    for done in part.vars['completed_before_posttask_reorder']:
        assert not getattr(s,done).is_displayed(player),(name,done)
    if name in MOVED:
        assert NEW[(part._index_in_pages-1)%len(NEW)]=='TaskEffort'
        # Every previously unanswered old page is still available later.
        for pending in MOVED[MOVED.index(name):]:
            if pending not in ('AverageTruth','AverageOutcomes'):
                assert getattr(s,pending).is_displayed(player),(name,pending)
    if name=='TaskEffort':
        assert player.trust_own_iq_estimate==3 and not s.IQCredibility.is_displayed(player)
    if name=='BigFiveSurvey1':
        assert s.TaskEffort.is_displayed(player) and s.IQCredibility.is_displayed(player)
    if name=='completed':assert part._index_in_pages==NEW_MAX+1
fresh=parts[-1].get_player('social_media',45)
assert s.TaskEffort.is_displayed(fresh) and s.IQCredibility.is_displayed(fresh)
assert s.IQCredibility.error_message(fresh,{})
assert not s.IQCredibility.error_message(fresh,dict(trust_own_iq_estimate=3))
with patch.dict(s.CFG,show_iq=False):assert not s.IQCredibility.is_displayed(fresh)
assert migrate(True)['count']==0
print('Passed effort -> IQ credibility -> beliefs -> personality, unchanged trust scale/field, all 1,665 old index mappings, preserved answers/payoffs and repeat-safe migration.')
