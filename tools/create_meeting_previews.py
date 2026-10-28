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
import sys
from pathlib import Path

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


def create_previews():
    from PIL import Image, ImageDraw
    from otree.database import db, init_orm
    init_orm()
    from otree.session import create_session
    from otree.lookup import _get_session_lookups
    import social_media as survey
    from social_media.peer_groups import averages, message_for
    from social_media.new_pages import average_rows

    session = create_session('cognitive_tasks', num_participants=2 * len(CASES),
                             label='RESEARCHER PREVIEWS ONLY - meeting page shortcuts')
    participants = session.get_participants()
    # Keep comparisons identical WITHIN format; quantitative participants now
    # require quantitative-only reference groups, while qualitative is unchanged.
    shared_by_kind = {}
    for kind in ('quantitative_social', 'qualitative_social'):
        for source in participants:
            source.vars.pop('peer_groups', None)
            source.vars.pop('linked_message_plan', None)
            source.vars['social_type'] = kind
            source_player = source.get_player('social_media', 45)
            usable = all(averages(source_player, period)['reported'] is not None for period in (1, 2, 3))
            usable &= bool(message_for(source.get_player('social_media', 5), kind.removesuffix('_social')))
            if usable:
                shared_by_kind[kind] = {key: copy.deepcopy(source.vars[key]) for key in
                    ('period_tasks', 'period_sets', 'round_plan', 'period_task_labels', 'peer_groups')}
                break
        else:
            raise RuntimeError('No complete comparison example; session left labelled as preview only.')

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
                    str(row['period']): 50 if kind == 'qualitative' else 7.5 for row in rows}
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
    print(json.dumps(dict(session=session.code, links=links,
                         comparison_quintiles={kind: {p: g['quintile'] for p, g in shared['peer_groups'].items()}
                                               for kind, shared in shared_by_kind.items()})))


if __name__ == '__main__':
    create_previews()
