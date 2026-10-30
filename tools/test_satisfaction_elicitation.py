"""Check satisfaction denominators, incentives, disclosure and final item order."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['OTREE_IN_MEMORY'] = '1'
os.environ['EXPERIMENT_PILOT'] = 'iq'
import social_media as survey
from social_media.peer_groups import averages
from social_media.new_pages import AverageBeliefs, AverageOutcomes


def player(code='check'):
    return SimpleNamespace(id_in_group=1, round_number=45, in_rounds=lambda a,b: [],
        participant=SimpleNamespace(code=code, vars=dict(
            social_type='qualitative_social', qualitative_target='private_satisfaction_v1',
            period_tasks=['sequences','working_memory','ravens'], like_treatment=False)))


# Three drawn copies of a satisfied sender, two copies of a non-sender, and
# fifteen control/quantitative records. Every draw counts in the private target.
records = ([dict(performance_satisfaction=5, blocks=[dict(emoji='😃',sent=True),dict(emoji='😞',sent=False)])]*3
           + [dict(performance_satisfaction=5, blocks=[dict(emoji='😃',sent=False)])]*2
           + [dict(performance_satisfaction=2, blocks=[dict(emoji='',sent=False)])]*15)
p = player()
with patch('social_media.peer_groups.records_for', return_value=records):
    result = averages(p,1)
    assert result['reported']==100 and result['actual']==25 and result['n_draws']==20
    p.participant.vars.pop('qualitative_target')
    legacy = averages(p,1)
    assert legacy['kind']=='happy' and legacy['actual']==62.5

row = dict(period=1,task_label='Numerical reasoning',available=True,kind='satisfaction',
           reported=75,reported_text='75.0',actual=25,actual_text='25.0',
           incentive_amount=.25,incentive_tolerance=10)
with patch('social_media.new_pages.average_rows', return_value=[row]):
    for answer,expected in [(15,.25),(35,.25),(14.9,0),(35.1,0),(25,.25),(0,0),(100,0)]:
        p=player()
        context=AverageBeliefs.vars_for_template(p)
        assert context['satisfaction_target']
        assert 'actual' not in context['rows'][0] and 'actual_text' not in context['rows'][0]
        assert AverageBeliefs.live_method(p,{'1':answer})=={1:{'saved':True}}
        assert p.participant.vars['average_belief_bonus']['amount']==expected
        assert AverageBeliefs.live_method(p,{'1':answer})=={1:{'saved':True}}
        assert 'error' in AverageBeliefs.live_method(p,{'1':answer+.1})[1]
        with patch.object(survey,'third_period_played',return_value=False), \
             patch.object(survey,'switched_disqualified_count',return_value=0):
            final=survey.FinalResults.vars_for_template(p)
            assert float(p.payoff)==expected and final['belief_bonus_display']==f'{expected:.2f}'
            survey.FinalResults.vars_for_template(p)
            assert float(p.payoff)==expected, 'Refresh must not double-pay'
    for invalid in (True,'nan','inf',-1,101,'',None):
        p=player()
        assert 'error' in AverageBeliefs.live_method(p,{'1':invalid})[1]
        assert 'average_belief_bonus' not in p.participant.vars
    for show_iq in (True,False):
        orders=set()
        with patch.dict(survey.CFG,show_iq=show_iq):
            for i in range(100):
                p=player(str(i))
                context=AverageOutcomes.vars_for_template(p)
                order=tuple(q['key'] for q in context['questions'])
                assert set(order)==({'mood','satisfaction_1','iq_perception'} if show_iq else {'mood','satisfaction_1'})
                assert context==AverageOutcomes.vars_for_template(p)
                orders.add(order)
        assert len(orders)==(6 if show_iq else 2)
    legacy=dict(row,kind='happy')
    with patch('social_media.new_pages.average_rows',return_value=[legacy]):
        p=player()
        assert not AverageBeliefs.vars_for_template(p)['satisfaction_target']
        assert AverageBeliefs.live_method(p,{'1':25})[1]['saved']
        assert 'average_belief_bonus' not in p.participant.vars
quantitative = dict(row, kind='score', actual=7.5, actual_text='7.5', incentive_tolerance=1)
p=player()
p.participant.vars.update(social_type='quantitative_social', quantitative_estimate_incentive=True)
with patch('social_media.peer_groups.records_for', return_value=[dict(score=9, blocks=[dict(report=3,score=3,sent=True)]*3)]*20):
    assert averages(p,1)['incentive_tolerance'] == 1
with patch('social_media.new_pages.average_rows',return_value=[quantitative]):
    for answer,expected in [(6.5,.25),(8.5,.25),(7.5,.25),(6.4,0),(8.6,0)]:
        p=player()
        p.participant.vars['social_type']='quantitative_social'
        context=AverageBeliefs.vars_for_template(p)
        assert context['rows'][0]['incentivized'] and not context['satisfaction_target']
        assert context['rows'][0]['incentive_tolerance'] == 1
        assert AverageBeliefs.live_method(p,{'1':answer})[1]['saved']
        assert p.participant.vars['average_belief_bonus']['amount']==expected
        with patch.object(survey,'third_period_played',return_value=False), \
             patch.object(survey,'switched_disqualified_count',return_value=0):
            final=survey.FinalResults.vars_for_template(p)
            assert final['belief_bonus_label']=='Comparison-group belief accuracy'
            assert float(p.payoff)==expected
            survey.FinalResults.vars_for_template(p)
            assert float(p.payoff)==expected
    # An already displayed snapshot retains its announced cutoff and payment.
    with patch('social_media.new_pages.average_rows', return_value=[dict(quantitative, incentive_tolerance=.5)]):
        p=player()
        assert AverageBeliefs.vars_for_template(p)['rows'][0]['incentive_tolerance'] == .5
        assert AverageBeliefs.live_method(p, {'1': 8.1})[1]['saved']
        assert p.participant.vars['average_belief_bonus']['amount'] == 0
    legacy=dict(quantitative)
    del legacy['incentive_amount']
    del legacy['incentive_tolerance']
    with patch('social_media.new_pages.average_rows',return_value=[legacy]):
        p=player()
        assert not AverageBeliefs.vars_for_template(p)['rows'][0]['incentivized']
        assert AverageBeliefs.live_method(p,{'1':7.5})[1]['saved']
        assert 'average_belief_bonus' not in p.participant.vars
# Filled examples must require the researcher-preview flag, never affect regular users.
p=player()
p.participant.vars.update(iq_reference_asked=True,
    researcher_bonus_preview=dict(iq=.5,percentiles={'1':.25,'2':.25,'3':.25}))
with patch.object(survey,'third_period_played',return_value=True), \
     patch.object(survey,'switched_disqualified_count',return_value=0):
    assert not survey.FinalResults.vars_for_template(p)['fully_filled_bonus_preview']
    assert float(p.payoff)==0
    p.participant.vars['researcher_preview']=True
    result=survey.FinalResults.vars_for_template(p)
    assert len(result['preview_guess_rows'])==4 and float(p.payoff)==1.25
    survey.FinalResults.vars_for_template(p)
    assert float(p.payoff)==1.25
print('Passed: full-group satisfaction, legacy targets, inclusive bonus threshold, hidden truth, repeat-safe payment, stable randomized final questions.')
