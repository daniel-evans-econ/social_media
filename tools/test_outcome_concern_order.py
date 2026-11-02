"""Verify ordering, all index mappings and safe existing-session continuation."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['OTREE_IN_MEMORY'] = '1'
os.environ['OTREE_EPHEMERAL'] = '1'
os.environ['EXPERIMENT_PILOT'] = 'iq'
import otree.database as database
database.ephemeral_connection = database.engine.connect()
database.init_orm()
from otree.session import create_session
import social_media as s
from tools.migrate_outcome_concern_order import OLD, NEW, MAX_INDEX, MOVED, final_index, remap, migrate

assert NEW[NEW.index('TaskEffort'):NEW.index('AverageBeliefs') + 1] == ['TaskEffort', 'OutcomeConcern', 'IQCredibility', 'AverageBeliefs']
assert NEW.count('OutcomeConcern') == 1
for i in range(1, MAX_INDEX + 1):
    j = remap(i)
    assert (i - 1) // 38 == (j - 1) // 38
    assert OLD[(i - 1) % 38] == NEW[(j - 1) % 38]
assert remap(None) is None and remap(0) == 0 and remap(MAX_INDEX + 1) == MAX_INDEX + 1
cases = ['TaskEffort'] + MOVED + ['PlatformUsage', 'completed', 'unstarted']
parts = create_session('cognitive_tasks', num_participants=len(cases) + 1).get_participants()
for part, name in zip(parts, cases):
    part.vars.pop('outcome_concern_order_version')
    part._max_page_index = MAX_INDEX
    part._index_in_pages = MAX_INDEX + 1 if name == 'completed' else 0 if name == 'unstarted' else final_index(name)
    part._current_form_page_url = None
    player = part.get_player('social_media', 45)
    player.payoff = s.cu(2.25)
    player.task_effort = 75
    part.vars['completed_before_posttask_reorder'] = ['SelfEsteemSurvey']
dry = migrate()
assert dry['count'] == len(cases)
assert migrate(True)['records'] == dry['records']
for part, name in zip(parts, cases):
    player = part.get_player('social_media', 45)
    assert float(part.payoff) == 2.25 and player.task_effort == 75
    assert 'SelfEsteemSurvey' in part.vars['completed_before_posttask_reorder']
    if name in MOVED:
        assert NEW[(part._index_in_pages - 1) % 38] == 'OutcomeConcern'
        assert s.OutcomeConcern.is_displayed(player)
        for done in MOVED[:MOVED.index(name)]:
            assert not getattr(s, done).is_displayed(player)
    if name == 'completed':
        assert part._index_in_pages == MAX_INDEX + 1
assert migrate(True)['count'] == 0
fresh = parts[-1].get_player('social_media', 45)
assert s.OutcomeConcern.is_displayed(fresh)
assert s.OutcomeConcern.vars_for_template(fresh) == s.OutcomeConcern.vars_for_template(fresh)
print('Passed page order, all 1,710 mappings, preserved answers/payoffs, completed-page skipping and repeat-safe migration.')
