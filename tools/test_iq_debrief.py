"""Debrief calculations, recalled feedback and payment neutrality."""
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

part = create_session('cognitive_tasks', num_participants=1).get_participants()[0]
part.vars['period_tasks'] = ['sequences', 'ravens', 'working_memory']
part.vars['full_sample_iq_debrief'] = True
player = part.get_player('social_media', 45)
for p in part.get_players():
    period = (p.round_number - 1) // 15
    p.q_correct = (p.round_number - 1) % 15 < [9, 10, 12][period]
    p.q_tab_switches = 1  # Disqualified earnings must not reduce measured IQ.
    if p.round_number in (15, 30, 45):
        p.iq_estimate = [180, 100, 65][period]  # Recall these without using them for full-sample IQ.
player.payoff = s.cu(2.75)
part.get_player('social_media', 30).global_iq_estimate = 140
for accepted in (False, True):
    part.vars['third_period_accepted'] = accepted
    context = s.IQDebrief.vars_for_template(player)
    expected = [s.estimate_iq(s.TASK_IQ_COMPONENT[task], n, 15)
                for task, n in zip(part.vars['period_tasks'], [9, 10, 12])][:3 if accepted else 2]
    assert [r['iq'] for r in context['debrief_rows']] == expected
    assert [r['earlier_iq'] for r in context['debrief_rows']] == [180, 100, 65][:3 if accepted else 2]
    assert context['earlier_overall_iq'] == 140
    assert context['earlier_overall_periods'] == ('the first two' if accepted else 'both')
    assert context['overall_iq'] == int(sum(expected) / len(expected) + .5)
    assert float(part.payoff) == 2.75 and float(player.payoff) == 2.75
    assert s.IQDebrief.is_displayed(player)
    assert not s.IQDebrief.is_displayed(part.get_player('social_media', 30))
with patch.object(s, 'estimate_iq', side_effect=[100, 101]):
    part.vars['third_period_accepted'] = False
    assert s.IQDebrief.vars_for_template(player)['overall_iq'] == 101
part.get_player('social_media', 30).global_iq_estimate = None
assert s.IQDebrief.vars_for_template(player)['earlier_overall_iq'] is None
with patch.dict(s.CFG, show_iq=False):
    assert not s.IQDebrief.is_displayed(player)
assert s.page_sequence.index(s.IQDebrief) == s.page_sequence.index(s.FinalResults) + 1

print('Passed two/three-period full-sample debrief, recorded earlier feedback, half-up overall rounding and unchanged payoffs.')
