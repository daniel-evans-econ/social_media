"""Debrief calculations, payment neutrality and old-session navigation."""
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['OTREE_IN_MEMORY'] = '1'
os.environ['EXPERIMENT_PILOT'] = 'iq'
from otree.database import init_orm
init_orm()
from otree.session import create_session
import social_media as s
from tools.migrate_debrief_page import migrate, remap, OLD_MAX, NEW_MAX

part = create_session('cognitive_tasks', num_participants=1).get_participants()[0]
part.vars['period_tasks'] = ['sequences', 'ravens', 'working_memory']
part.vars['full_sample_iq_debrief'] = True
player = part.get_player('social_media', 45)
for p in part.get_players():
    period = (p.round_number - 1) // 15
    p.q_correct = (p.round_number - 1) % 15 < [9, 10, 12][period]
    p.q_tab_switches = 1  # Disqualified earnings must not reduce measured IQ.
    if p.round_number in (15, 30, 45):
        p.iq_estimate = 180  # Debrief must ignore the earlier noisy estimate.
player.payoff = s.cu(2.75)
for accepted in (False, True):
    part.vars['third_period_accepted'] = accepted
    context = s.IQDebrief.vars_for_template(player)
    expected = [s.estimate_iq(s.TASK_IQ_COMPONENT[task], n, 15)
                for task, n in zip(part.vars['period_tasks'], [9, 10, 12])][:3 if accepted else 2]
    assert [r['iq'] for r in context['debrief_rows']] == expected
    assert context['overall_iq'] == int(sum(expected) / len(expected) + .5)
    assert float(part.payoff) == 2.75 and float(player.payoff) == 2.75
    assert s.IQDebrief.is_displayed(player)
    assert not s.IQDebrief.is_displayed(part.get_player('social_media', 30))
with patch.object(s, 'estimate_iq', side_effect=[100, 101]):
    part.vars['third_period_accepted'] = False
    assert s.IQDebrief.vars_for_template(player)['overall_iq'] == 101
with patch.dict(s.CFG, show_iq=False):
    assert not s.IQDebrief.is_displayed(player)
assert s.page_sequence.index(s.IQDebrief) == s.page_sequence.index(s.FinalResults) + 1

# Every old page retains its class and round; completion stays completed.
for old in range(1, OLD_MAX + 1):
    new = remap(old)
    assert (old - 1) // 36 == (new - 1) // 37
    assert s.page_sequence[(old - 1) % 36] is s.page_sequence[(new - 1) % 37]
assert remap(OLD_MAX + 1) == NEW_MAX + 1
assert remap(None) is None and remap(0) == 0
part._max_page_index = OLD_MAX
part._index_in_pages = 1610
part._timeout_page_index = 1520
part._current_form_page_url = '/p/' + part.code + '/cognitive_tasks/AverageBeliefs/1610'
before_payoff = float(part.payoff)
dry = migrate()
assert dry['count'] == 1 and part._index_in_pages == 1610
result = migrate(True)
assert result['records'] == dry['records']
assert part._index_in_pages == 1654 and part._max_page_index == NEW_MAX
assert part._current_form_page_url.endswith('/1654')
assert float(part.payoff) == before_payoff
assert migrate(True)['count'] == 0
print('Passed two/three-period full-sample debrief, half-up overall rounding, unchanged payoffs, all 1,620 old page mappings and idempotent navigation migration.')
