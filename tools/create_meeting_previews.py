"""Independent direct-entry researcher previews; never alter real participants.

Only this CLI creates the shortcuts. There is no public survey skip mechanism.
TestBot labels and researcher_preview flags distinguish example own responses;
comparison records and reported/actual statistics remain real pilot observations.
Each page has an independent review and QA slot, so QA cannot advance review links.
"""
import base64
import copy
import io
import json
import statistics
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# key, page, round, message format, image, correction
CASES = [
    ('consent', 'Consent', 1, 'quantitative', 'avatar', True),
    ('camera', 'SelfieCapture', 1, 'quantitative', 'selfie', True),
    ('username_avatar', 'Intro', 1, 'quantitative', 'avatar', True),
    ('username_selfie', 'Intro', 1, 'quantitative', 'selfie', True),
    ('message_quant_avatar', 'BlockFeedback', 5, 'quantitative', 'avatar', True),
    ('message_quant_selfie', 'BlockFeedback', 5, 'quantitative', 'selfie', True),
    ('message_qual_avatar', 'BlockFeedback', 5, 'qualitative', 'avatar', True),
    ('message_qual_selfie', 'BlockFeedback', 5, 'qualitative', 'selfie', True),
    ('subjective', 'EndOfPeriodSurvey', 15, 'quantitative', 'avatar', True),
    ('beliefs_quant_correction', 'AverageBeliefs', 45, 'quantitative', 'avatar', True),
    ('beliefs_quant_control', 'AverageBeliefs', 45, 'quantitative', 'avatar', False),
    ('beliefs_qual_correction', 'AverageBeliefs', 45, 'qualitative', 'avatar', True),
    ('beliefs_qual_control', 'AverageBeliefs', 45, 'qualitative', 'avatar', False),
    ('correction_quant', 'AverageBeliefs', 45, 'quantitative', 'avatar', True),
    ('correction_qual', 'AverageBeliefs', 45, 'qualitative', 'avatar', True),
    ('final_questions', 'AverageBeliefs', 45, 'quantitative', 'avatar', True),
    ('final_questions_control', 'AverageBeliefs', 45, 'quantitative', 'avatar', False),
    ('satisfaction_bonus', 'FinalResults', 45, 'qualitative', 'selfie', True),
    ('quantitative_bonus', 'FinalResults', 45, 'quantitative', 'avatar', True),
]


def treatment_cases():
    cases = [
        ('consent', 'Consent', 1, 'quantitative', 'avatar', True),
        ('camera', 'SelfieCapture', 1, 'quantitative', 'selfie', True),
        ('reference_on', 'IQReferencePoint', 1, 'quantitative', 'avatar', True),
        ('reference_off', 'IQReferencePoint', 1, 'quantitative', 'avatar', True),
        ('username_avatar', 'Intro', 1, 'quantitative', 'avatar', True),
        ('username_selfie', 'Intro', 1, 'quantitative', 'selfie', True),
        ('iq_lower_half', 'IQFeedback', 15, 'quantitative', 'avatar', True),
        ('iq_upper_half', 'IQFeedback', 15, 'quantitative', 'avatar', True),
        ('ranked_feed', 'MessageReactionFeedback', 15, 'quantitative', 'avatar', True),
        ('subjective', 'EndOfPeriodSurvey', 15, 'quantitative', 'avatar', True),
        ('effort', 'TaskEffort', 45, 'quantitative', 'avatar', True),
        ('credibility', 'IQCredibility', 45, 'quantitative', 'avatar', True),
        ('payment', 'FinalResults', 45, 'quantitative', 'avatar', True),
        ('payment_no_initial_iq', 'FinalResults', 45, 'qualitative', 'avatar', False),
        ('debrief', 'IQDebrief', 45, 'quantitative', 'avatar', True),
        ('debrief_two_periods', 'IQDebrief', 45, 'qualitative', 'avatar', False),
        ('percentile', 'PerceivedPercentile', 15, 'quantitative', 'avatar', True),
    ]
    for kind in ('quantitative', 'qualitative'):
        for reacts in (False, True):
            key = f'message_{kind}_' + ('reactions' if reacts else 'no_reactions')
            cases.append((key, 'BlockFeedback', 5, kind, 'avatar', True))
        for truth in (False, True):
            suffix = 'correction' if truth else 'control'
            cases.append((f'beliefs_{kind}_{suffix}', 'AverageBeliefs', 45, kind, 'avatar', truth))
            cases.append((f'correction_{kind}_{suffix}', 'AverageBeliefs', 45, kind, 'avatar', truth))
    return cases


def representative_groups(sample_size=1000):
    """Select real draws near the joint medians, only for researcher previews.

    Both formats use numerical reasoning in period 1. Each candidate follows
    the survey's ordinary half/replacement rule. No observations or values
    are edited; the chosen candidate minimizes squared distance to the reported
    and actual medians across available candidates. Both axes have equal units.
    """
    import social_media as survey
    from social_media.peer_groups import averages, message_for

    for seed in range(100):
        tasks, sets, plan = survey._build_plan(SimpleNamespace(code=f'preview-plan-{seed}'))
        if tasks[0] == 'sequences':
            break
    else:
        raise RuntimeError('No numerical-reasoning preview plan.')
    shared, audit = {}, {}
    for kind in ('quantitative_social', 'qualitative_social'):
        candidates = []
        for i in range(sample_size):
            code = f'representative-v1-{kind}-{i}'
            part = SimpleNamespace(code=code, vars=dict(
                period_tasks=tasks, period_sets=sets, round_plan=plan,
                period_task_labels=' → '.join(survey.TASK_LABELS[t] for t in tasks),
                linked_peer_groups=True, peer_group_sampling='quantitative_only_v1', peer_group_strata=2,
                qualitative_target='private_satisfaction_v1', quantitative_estimate_incentive=True,
                social_type=kind))
            player = SimpleNamespace(participant=part, round_number=5)
            row = averages(player, 1)
            if row['reported'] is not None:
                candidates.append((player, row))
        med_reported = statistics.median(row['reported'] for _, row in candidates)
        med_actual = statistics.median(row['actual'] for _, row in candidates)
        candidates.sort(key=lambda pair: (pair[1]['reported']-med_reported)**2
                                        + (pair[1]['actual']-med_actual)**2)
        for player, row in candidates:
            if all(averages(player, p)['reported'] is not None for p in (2, 3)) and message_for(player, kind.removesuffix('_social')):
                shared[kind] = {key: copy.deepcopy(player.participant.vars[key]) for key in
                    ('period_tasks', 'period_sets', 'round_plan', 'period_task_labels', 'peer_groups', 'linked_message_plan')}
                audit[kind] = dict(candidate_seed=player.participant.code, sample_size=sample_size,
                    available_candidates=len(candidates), median_reported=med_reported, median_actual=med_actual,
                    reported=row['reported'], actual=row['actual'], task=tasks[0],
                    selection='nearest joint medians among feasible real draws')
                break
        else:
            raise RuntimeError('No complete comparison example.')
    return shared, audit


def create_previews():
    from PIL import Image, ImageDraw
    from otree.database import db, init_orm
    init_orm()
    from otree.session import create_session
    from otree.lookup import _get_session_lookups
    import social_media as survey
    from social_media.new_pages import average_rows
    from social_media.peer_groups import group_for

    shared_by_kind, representative_audit = representative_groups()
    session = create_session('cognitive_tasks', num_participants=2 * len(CASES),
                             label='RESEARCHER PREVIEWS ONLY - meeting page shortcuts')
    participants = session.get_participants()

    image = Image.new('RGB', (512, 512), '#cbd6df')
    draw = ImageDraw.Draw(image)
    draw.text((160, 245), 'DEMO IMAGE - NOT A SELFIE', fill='#394958')
    stream = io.BytesIO()
    image.save(stream, 'JPEG')
    placeholder = 'data:image/jpeg;base64,' + base64.b64encode(stream.getvalue()).decode()
    lookups = _get_session_lookups(session.code)
    links = []
    for purpose in ('review', 'qa'):
        for case_number, (key, page_name, round_number, kind, image_arm, truth) in enumerate(CASES):
            reacts = not key.endswith('no_reactions')
            offset = 0 if purpose == 'review' else len(CASES)
            participant = participants[offset + case_number]
            participant.label = f'TestBot-meeting-{purpose}-{key}'
            participant.vars.pop('linked_message_plan', None)
            participant.vars.update(copy.deepcopy(shared_by_kind[kind + '_social']))
            participant.vars.update(
                social_type=kind + '_social', image_treatment=image_arm,
                like_treatment=reacts, reveal_truth=truth, linked_peer_groups=True,
                third_period_accepted=True, period_3_condition=kind + '_social',
                researcher_preview=True, display_name='TestBot',
                avatar_choice='masculine-v2-1', iq_reference_asked=key not in ('reference_off', 'payment_no_initial_iq'),
                # Match the displayed period across review contrasts. This
                # override is confined to labelled researcher preview sessions.
                average_period_selection=dict(version=1, eligible_periods=[1, 3], period=1,
                                              source='researcher_preview'),
            )
            participant.period_1_condition = kind + '_social'
            participant.period_2_condition = 'control'
            if page_name == 'Intro':
                participant.vars.pop('avatar_choice', None)
            if key in ('iq_lower_half', 'iq_upper_half'):
                half = 1 if key == 'iq_lower_half' else 2
                for i in range(100):
                    candidate = SimpleNamespace(code=f'preview-half-{half}-{i}',
                        vars=dict(participant.vars, peer_groups={}))
                    group = group_for(SimpleNamespace(participant=candidate, round_number=15), 1)
                    if group['stratum'] == half:
                        groups = copy.deepcopy(participant.vars['peer_groups'])
                        groups['1'] = group
                        participant.vars['peer_groups'] = groups
                        break
                else:
                    raise RuntimeError('Could not find a comparison-half example')
            if key not in ('camera', 'consent'):
                participant.vars['selfie'] = dict(image=placeholder, blur=10, source='researcher_preview_placeholder')
            if key == 'consent':
                participant.vars.pop('selfie_consent', None)
            bonus_preview = key in ('satisfaction_bonus', 'quantitative_bonus')
            if bonus_preview:
                participant.vars['third_period_pay_rate'] = float(survey.C.PAY_PER_CORRECT)
                # Explicit, labelled researcher-only examples of deferred bonuses.
                participant.vars['researcher_bonus_preview'] = dict(iq=.50, percentiles={str(p):.25 for p in (1,2,3)})
            for player in participant.get_players():
                player.condition = survey.get_condition(player)
                player.q_correct = bonus_preview or (player.round_number - 1) % 5 < 3
                spec = survey.round_spec(player)
                player.q_task = spec['task']
                player.q_item_id = spec['item_id']
                player.q_set_id = spec['set_id']
                player.q_difficulty = spec['difficulty']
                player.like_treatment = reacts
            target = participant.get_player('social_media', round_number)
            if key == 'debrief_two_periods':
                participant.vars['third_period_accepted'] = False
            if page_name in ('FinalResults', 'IQDebrief'):
                # Representative task responses, scored by the real payment
                # calculation, rather than hard-coded example bonus amounts.
                participant.vars['third_period_pay_rate'] = .25
                for period in (1, 2, 3):
                    end = participant.get_player('social_media', period * 15)
                    task = participant.vars['period_tasks'][period - 1]
                    end.iq_estimate = survey.estimate_iq_for_player(end, survey.TASK_IQ_COMPONENT[task], 15 if bonus_preview else 9, 15)
                    group = group_for(end, period)
                    score = 15 if bonus_preview else 9
                    rank = (sum(v < score for v in group['scores']) + .5 * sum(v == score for v in group['scores'])) / len(group['scores'])
                    end.perceived_outperformed_count = round(20 * rank)
                    survey.PerceivedPercentile.before_next_page(end, False)
                p30 = participant.get_player('social_media', 30)
                p30.global_iq_estimate = survey.global_iq_for_player(p30)
                participant.get_player('social_media', 1).iq_reference_score = p30.global_iq_estimate
                if key == 'payment_no_initial_iq':
                    participant.vars['third_period_accepted'] = False
            assert getattr(survey, page_name).is_displayed(target)
            if page_name == 'BlockFeedback':
                target.report_number = 3
                if kind == 'qualitative':
                    target.report_emoji = survey.QUAL_EMOJIS[0]
                    target.report_message = 'I felt good about that block.'
                assert survey.pilot_feedback_signals(target).get('name'), 'Preview needs a received message'
            if page_name == 'MessageReactionFeedback':
                # Exercise the real message-recording path before rendering the
                # ranked preview. Counts/usernames remain labelled synthetic.
                for rnd in (5, 10, 15):
                    source = participant.get_player('social_media', rnd)
                    source.report_number = 3
                    source.report_shared = True
                    source.received_reaction = 'love' if rnd == 5 else 'none'
                    survey.BlockFeedback.before_next_page(source, False)
                    survey.record_sent_message_time(source, 'block')
                assert survey.MessageReactionFeedback.vars_for_template(target)['messages']
            if page_name.startswith('Average') or page_name == 'FinalResults':
                rows = average_rows(target)
                assert all(row['available'] for row in rows)
                participant.vars['average_beliefs'] = {
                    str(row['period']): round((row['reported'] + row['actual']) / 2, 1) for row in rows}
                if page_name == 'FinalResults' or key.startswith(('correction_', 'final_questions')):
                    answers = {str(row['period']): row['actual'] if bonus_preview else round((row['reported']+row['actual'])/2,1) for row in rows}
                    assert survey.AverageBeliefs.live_method(target, dict(action='belief',answers=answers))[target.id_in_group]['saved']
            participant.initialize(participant.label)
            participant._index_in_pages = next(i for i, lookup in lookups.items()
                if lookup.round_number == round_number and lookup.page_class.__name__ == page_name)
            links.append(dict(key=key, purpose=purpose, page=page_name,
                              path=participant._url_i_should_be_on(), code=participant.code,
                              message_format=kind, image=image_arm, correction=truth,
                              reactions=reacts, iq_reference=participant.vars['iq_reference_asked']))
    db.commit()
    print(json.dumps(dict(session=session.code, links=links, representative_examples=representative_audit,
                         comparison_strata={kind: {p: g['stratum'] for p, g in shared['peer_groups'].items()}
                                               for kind, shared in shared_by_kind.items()})))


if __name__ == '__main__':
    if '--treatments' in sys.argv:
        CASES = treatment_cases()
    elif '--debrief' in sys.argv:
        CASES = [case for case in treatment_cases() if case[1] == 'IQDebrief']
    create_previews()
