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
    ('correction_quant', 'AverageTruth', 45, 'quantitative', 'avatar', True),
    ('correction_qual', 'AverageTruth', 45, 'qualitative', 'avatar', True),
    ('final_questions', 'AverageOutcomes', 45, 'quantitative', 'avatar', True),
    ('final_questions_control', 'AverageOutcomes', 45, 'quantitative', 'avatar', False),
    ('satisfaction_bonus', 'FinalResults', 45, 'qualitative', 'selfie', True),
    ('quantitative_bonus', 'FinalResults', 45, 'quantitative', 'avatar', True),
]


def representative_groups(sample_size=1000):
    """Select real draws near the joint medians, only for researcher previews.

    Both formats use numerical reasoning in period 1. Each candidate follows
    the survey's ordinary quintile/replacement rule. No observations or values
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
                linked_peer_groups=True, peer_group_sampling='quantitative_only_v1',
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
                    ('period_tasks', 'period_sets', 'round_plan', 'period_task_labels', 'peer_groups')}
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
            offset = 0 if purpose == 'review' else len(CASES)
            participant = participants[offset + case_number]
            participant.label = f'TestBot-meeting-{purpose}-{key}'
            participant.vars.pop('linked_message_plan', None)
            participant.vars.update(copy.deepcopy(shared_by_kind[kind + '_social']))
            participant.vars.update(
                social_type=kind + '_social', image_treatment=image_arm,
                like_treatment=True, reveal_truth=truth, linked_peer_groups=True,
                third_period_accepted=True, period_3_condition=kind + '_social',
                researcher_preview=True, display_name='TestBot',
                avatar_choice='masculine-v2-1', iq_reference_asked=True,
                # Match the displayed period across review contrasts. This
                # override is confined to labelled researcher preview sessions.
                average_period_selection=dict(version=1, eligible_periods=[1, 3], period=1,
                                              source='researcher_preview'),
            )
            participant.period_1_condition = kind + '_social'
            participant.period_2_condition = 'control'
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
                player.like_treatment = True
            target = participant.get_player('social_media', round_number)
            assert getattr(survey, page_name).is_displayed(target)
            if page_name == 'BlockFeedback':
                target.report_number = 3
                if kind == 'qualitative':
                    target.report_emoji = survey.QUAL_EMOJIS[0]
                    target.report_message = 'I felt good about that block.'
                assert survey.pilot_feedback_signals(target).get('name'), 'Preview needs a received message'
            if page_name.startswith('Average') or bonus_preview:
                rows = average_rows(target)
                assert all(row['available'] for row in rows)
                participant.vars['average_beliefs'] = {
                    str(row['period']): round((row['reported'] + row['actual']) / 2, 1) for row in rows}
                if bonus_preview:
                    answers = {str(row['period']): row['actual'] for row in rows}
                    assert survey.AverageBeliefs.live_method(target, answers)[target.id_in_group]['saved']
            participant.initialize(participant.label)
            participant._index_in_pages = next(i for i, lookup in lookups.items()
                if lookup.round_number == round_number and lookup.page_class.__name__ == page_name)
            links.append(dict(key=key, purpose=purpose, page=page_name,
                              path=participant._url_i_should_be_on(), code=participant.code,
                              message_format=kind, image=image_arm, correction=truth))
    db.commit()
    print(json.dumps(dict(session=session.code, links=links, representative_examples=representative_audit,
                         comparison_quintiles={kind: {p: g['quintile'] for p, g in shared['peer_groups'].items()}
                                               for kind, shared in shared_by_kind.items()})))


if __name__ == '__main__':
    create_previews()
