"""Real oTree accounting across all treatment cells, rates and accuracy awards."""
import itertools
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
from social_media.new_pages import image_url
from tools.reconcile_payment_totals import reconcile

session = create_session('cognitive_tasks', num_participants=32, label='LOCAL PAYMENT TEST')
checked = 0
cells = itertools.product(('quantitative_social', 'qualitative_social'), (False, True),
                          ('avatar', 'selfie'), (False, True), (False, True))
for part, (fmt, reactions, image, truth, prior) in zip(session.get_participants(), cells):
    part.vars.update(social_type=fmt, like_treatment=reactions, image_treatment=image,
                     reveal_truth=truth, iq_reference_asked=prior)
    rounds = part.get_players()
    p1, p15, p30, p45 = [part.get_player('social_media', r) for r in (1, 15, 30, 45)]
    for p in rounds:
        p.q_correct = p.round_number <= 30 and (p.round_number - 1) % 15 < 10
        p.q_tab_switches = 1 if p.round_number in (1, 16, 31) else 0
    p15.iq_estimate, p30.iq_estimate, p45.iq_estimate = 100, 110, 160
    p30.global_iq_estimate = 105
    for col in ('t', 'c'):
        for i in range(1, len(s.WTA_AMOUNTS) + 1):
            setattr(p30, f'wta_{col}_{i}', 'No')
    s.Results.vars_for_template(p30)
    assert float(p30.payoff) == 4.5
    for accepted, rate in [(False, 0)] + [(True, r) for r in s.WTA_AMOUNTS]:
        part.vars.update(third_period_accepted=accepted, third_period_pay_rate=rate)
        for p in rounds:
            if p.round_number > 30:
                p.q_correct = accepted and p.round_number - 31 < 8
        for belief, accurate in itertools.product((0, .25), (False, True)):
            part.vars['average_belief_bonus'] = dict(amount=belief)
            full_sample_target = int(sum(s.estimate_iq(s.TASK_IQ_COMPONENT[t], 10, 15)
                                         for t in part.vars['period_tasks'][:2]) / 2 + .5)
            p1.iq_reference_score = full_sample_target + (10 if accurate else 11)
            for p in (p15, p30, p45):
                p.perceived_relative_performance = 60 if accurate else 61
            # No historical reference-group draw may determine percentile pay.
            with patch.object(s, 'group_for', side_effect=AssertionError('Percentile payment queried historical data')):
                result = s.FinalResults.vars_for_template(p45)
                expected_accuracy = .5 if accurate and prior else 0
                expected = round(4.5 + (7 * rate if accepted else 0) + belief + expected_accuracy, 2)
                assert float(result['total_payoff']) == expected
                assert float(part.payoff) == expected, 'oTree aggregate must equal displayed total'
                assert float(p45.payoff) == round(expected - 4.5, 2)
                assert len(result['preview_guess_rows']) == int(prior)
                assert len(result['pending_guess_rows']) == (3 if accepted else 2)
                assert result['guess_bonus_max_display'] == ('0.75' if accepted else '0.50')
                assert not result['pending_iq_bonus']
                assert not result['fully_filled_bonus_preview']
                assert len(result['task_rows']) == (3 if accepted else 2)
                assert float(result['switched_subtracted']) == round(.5 + (rate if accepted else 0), 2)
                awards = part.vars['accuracy_bonus_results']['awards']
                assert not any(k.startswith('percentile') for k in awards)
                assert all(r['reason'] == 'awaiting_current_question_set_data' and 'amount' not in r and 'actual' not in r
                           for r in part.vars['accuracy_bonus_results']['pending'])
                if prior:
                    assert awards['initial_iq']['actual'] == full_sample_target and awards['initial_iq']['components'] == 2
                    assert awards['initial_iq']['source'] == 'full_sample'
                    assert s.IQDebrief.vars_for_template(p45)['overall_iq'] == full_sample_target
                s.FinalResults.vars_for_template(p45)
                assert float(part.payoff) == expected, 'Refresh must not double-pay'
                # An existing old final-round full-total credit is repaired.
                p45.payoff = s.cu(expected)
                s.FinalResults.vars_for_template(p45)
                assert float(part.payoff) == expected
            checked += 1

# All percentile responses remain pending, including endpoints and old demo overrides.
part.vars.update(third_period_accepted=False, iq_reference_asked=False)
for guess in (0, 50, 100):
    p15.perceived_relative_performance = guess
    part.vars.update(researcher_preview=True, researcher_bonus_preview=dict(iq=.5, percentiles={'1':.25,'2':.25,'3':.25}))
    with patch.object(s, 'group_for', side_effect=AssertionError('No historic percentile scoring')):
        s.FinalResults.vars_for_template(p45)
    assert not part.vars['accuracy_bonus_results']['awards']
    pending = part.vars['accuracy_bonus_results']['pending'][0]
    assert pending['guess'] == guess and 'amount' not in pending and 'actual' not in pending

# Missing historical responses are pending, never fabricated zero awards.
p15.perceived_relative_performance = None
p15.perceived_outperformed_count = None
result = s.FinalResults.vars_for_template(p45)
assert any(r['label'] == 'Period 1 percentile estimate' for r in result['pending_guess_rows'])

part.vars.update(image_treatment='avatar')
part.vars.pop('avatar_choice', None)
assert s.own_avatar(p1) == 'unselected'
assert image_url(p1).endswith('/unselected.svg')
assert s.Intro.vars_for_template(p1)['selected_avatar'] == ''
assert s.Intro.error_message(p1, dict(display_name='Test')) == 'Please choose an avatar.'
choice = s.AVATAR_OPTIONS[-1]['value']
s.Intro.live_method(p1, dict(avatar=choice))
assert s.own_avatar(p1) == choice and image_url(p1).endswith('/' + choice + '.svg')
assert not s.Intro.error_message(p1, dict(display_name='Test'))
assert s.Intro.vars_for_template(p1)['selected_avatar'] == choice

part.vars.pop('payment_accounting_version')
p30.payoff = s.cu(4.5)
p45.payoff = s.cu(6)
assert float(part.payoff) == 10.5
assert reconcile()['count'] == 1 and float(part.payoff) == 10.5
assert reconcile(True)['count'] == 1 and float(part.payoff) == 6
assert reconcile(True)['count'] == 0
print(f'Passed {checked} real-ORM payment scenarios across 32 cells: deferred percentile awards, no historical scoring or demo override, initial IQ boundary, all WTA rates, optional period, refresh and aggregate accounting.')
