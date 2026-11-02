"""All index mappings, terminal-page continuation, preserved data and repeat safety."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['OTREE_IN_MEMORY'] = '1'
os.environ['OTREE_EPHEMERAL'] = '1'
os.environ['EXPERIMENT_PILOT'] = 'iq'
from otree.database import init_orm
import otree.database as database
database.ephemeral_connection = database.engine.connect()
init_orm()
from otree.session import create_session
import social_media as s
from tools.migrate_debrief_before_bonus import MAX_INDEX, remap, migrate

for i in range(1, MAX_INDEX + 1):
    j = remap(i)
    assert (i - 1) // 38 == (j - 1) // 38
    assert remap(j) == i
assert remap(None) is None and remap(0) == 0 and remap(1711) == 1711
parts = create_session('cognitive_tasks', num_participants=6).get_participants()
for part, index in zip(parts, (0, 1692, 1709, 1710, 1711, 1709)):
    part._index_in_pages = index
    part._max_page_index = MAX_INDEX
    part._current_form_page_url = f'/p/{part.code}/social_media/FinalResults/{index}' if index else None
    part.get_player('social_media', 45).payoff = s.cu(3.25)
    part.get_player('social_media', 1).iq_reference_score = 110
for part in parts[:-1]:
    part.vars.pop('debrief_before_bonus_version')
dry = migrate()
assert dry['count'] == 5
assert [p._index_in_pages for p in parts] == [0, 1692, 1709, 1710, 1711, 1709]
assert migrate(True)['records'] == dry['records']
assert [p._index_in_pages for p in parts] == [0, 1692, 1709, 1709, 1711, 1709]
assert all(float(p.payoff) == 3.25 and p.get_player('social_media', 1).iq_reference_score == 110 for p in parts)
assert all(p._current_form_page_url is None for p in parts[2:4])
assert migrate(True)['count'] == 0
print('Passed all 1,710 index mappings, final-page continuation, finished/new sessions, preserved payoffs/answers and repeat-safe migration.')
