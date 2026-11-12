"""Debrief calculations, recalled feedback and payment neutrality."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

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
    assert context['overall_iq'] == int(sum(expected[:2]) / 2 + .5)
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
assert s.page_sequence.index(s.IQDebrief) + 1 == s.page_sequence.index(s.FinalResults)

# Follow the same participant from block feedback to the final bonus summary.
test_part = create_session('cognitive_tasks', num_participants=1).get_participants()[0]
test_part.period_1_condition = 'control'
test_part.vars.update(third_period_accepted=False, full_sample_iq_debrief=True)
for row in test_part.get_players():
    row.q_correct = row.round_number <= 10
    row.q_tab_switches = 2 if row.round_number in (1, 2, 11) else 0
end = test_part.get_player('social_media', 15)
last = test_part.get_player('social_media', 45)
assert s.block_correct(test_part.get_player('social_media', 5)) == 5
component = s.component_for_player(end)
expected_iq = s.estimate_iq_for_player(end, component, 10, 15)
feedback = s.IQFeedback.vars_for_template(end)
assert feedback['n_correct'] == 10 and feedback['iq'] == expected_iq
s.IQFeedback.before_next_page(end, False)
snapshot = json.loads(end.iq_feedback_snapshot)
assert snapshot['n_correct'] == 10 and snapshot['iq'] == expected_iq
debrief = s.IQDebrief.vars_for_template(last)['debrief_rows'][0]
assert debrief['correct'] == 10 and debrief['earlier_iq'] == expected_iq
assert debrief['iq'] == s.estimate_iq(component, 10, 15)
earnings = s.EndOfPeriodSurvey.vars_for_template(end)
amount = 8 * float(s.C.PAY_PER_CORRECT)
assert earnings['switched_count'] == 2 and float(earnings['period_earnings']) == amount
payment = s.FinalResults.vars_for_template(last)['task_rows'][0]
assert payment['correct'] == 8 and float(payment['amount']) == amount

print('Passed two/three-period full-sample debrief, recorded earlier feedback, half-up overall rounding and unchanged payoffs.')
