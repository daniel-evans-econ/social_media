"""New pilot pages. Responses live in participant.vars and the custom export.

No schema reset is required; existing participants keep their previous flow.
"""
import base64
import io
import math
import random
from datetime import datetime, timezone
from otree.api import Page
from .peer_groups import averages


def image_url(player):
    from . import own_avatar
    if player.participant.vars.get('image_treatment') == 'selfie':
        return player.participant.vars.get('selfie', {}).get('image', '')
    return '/static/social/avatars/' + own_avatar(player) + '.svg'


def completed_periods(player):
    from . import CFG, third_period_played
    return [1, 2, 3] if not CFG['use_wta'] or third_period_played(player) else [1, 2]


def average_periods(player):
    """Fix one completed social period, independently of correction assignment.

    Preserve previously displayed multi-period snapshots and their responses.
    Select before checking message availability: missing reports must not change
    which period is selected or silently change the randomization population.
    """
    part = player.participant
    if 'average_feedback' in part.vars:
        return [row['period'] for row in part.vars['average_feedback']]
    selection = part.vars.get('average_period_selection')
    if selection is None:
        conditions = {1: part.period_1_condition, 2: part.period_2_condition,
                      3: part.vars.get('period_3_condition', 'control')}
        eligible = [p for p in completed_periods(player)
                    if conditions[p] in ('quantitative_social', 'qualitative_social')]
        if not eligible:
            raise ValueError('Average elicitation requires a completed social period.')
        period = random.Random(f'{part.code}-average-period').choice(eligible)
        selection = dict(version=1, eligible_periods=eligible, period=period)
        part.vars['average_period_selection'] = selection
    return [selection['period']]


def average_rows(player):
    from . import TASK_LABELS
    snapshots = player.participant.vars.get('average_feedback')
    if snapshots is None:
        snapshots = [averages(player, p) for p in average_periods(player)]
        player.participant.vars['average_feedback'] = snapshots
    return [dict(row, task_label=TASK_LABELS[player.participant.vars['period_tasks'][row['period']-1]],
                 available=row['reported'] is not None and row['actual'] is not None,
                 reported_text=f"{row['reported']:.1f}" if row['reported'] is not None else '',
                 actual_text=f"{row['actual']:.1f}" if row['actual'] is not None else '')
            for row in snapshots]


class SelfieCapture(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1 and player.participant.vars.get('image_treatment') is not None

    @staticmethod
    def live_method(player, data):
        from PIL import Image
        if not isinstance(data, dict) or data.get('action') != 'confirm':
            return
        try:
            value = data.get('image', '')
            if not isinstance(value, str) or not value.startswith('data:image/jpeg;base64,') or len(value) > 400000:
                raise ValueError()
            raw = base64.b64decode(value.split(',', 1)[1], validate=True)
            with Image.open(io.BytesIO(raw)) as image:
                if image.size != (512, 512) or image.format != 'JPEG':
                    raise ValueError()
                output = io.BytesIO()
                image.convert('RGB').save(output, format='JPEG', quality=90)
            player.participant.vars['selfie'] = dict(
                image='data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode(),
                confirmed_at=datetime.now(timezone.utc).isoformat(), blur=10, version=1)
            return {player.id_in_group: dict(saved=True)}
        except (ValueError, OSError, TypeError):
            return {player.id_in_group: dict(error='Please take and confirm your selfie again.')}

    @staticmethod
    def error_message(player, values):
        if not player.participant.vars.get('selfie', {}).get('image'):
            return 'Please take and confirm your selfie before continuing.'


class AverageBeliefs(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 45 and player.participant.vars.get('linked_peer_groups', False)

    @staticmethod
    def vars_for_template(player):
        from . import REACTION_OPTIONS
        # Do not even send the unrevealed values to the template/debug context.
        allowed = {'period', 'task_label', 'available', 'reported_text', 'kind'}
        rows = [dict({key:value for key,value in row.items() if key in allowed},
                     incentivized=row.get('incentive_amount', 0) > 0)
                for row in average_rows(player)]
        return dict(rows=rows, single_period=len(rows) == 1,
                    qualitative=player.participant.vars['social_type'] == 'qualitative_social',
                    satisfaction_target=any(row['kind'] == 'satisfaction' for row in rows),
                    reaction_options=REACTION_OPTIONS)

    @staticmethod
    def live_method(player, data):
        if not isinstance(data, dict):
            return
        answers = {}
        try:
            for row in average_rows(player):
                if not row['available']:
                    continue
                raw = data.get(str(row['period']))
                if raw is None or isinstance(raw, bool) or str(raw).strip() == '':
                    raise ValueError()
                value = float(raw)
                if not math.isfinite(value) or not 0 <= value <= (15 if row['kind'] == 'score' else 100):
                    raise ValueError()
                answers[str(row['period'])] = value
        except (ValueError, TypeError):
            return {player.id_in_group: dict(error='Please answer each question within the displayed range.')}
        # Lock the incentivized estimate on first submission, before revelation.
        bonus = player.participant.vars.get('average_belief_bonus')
        if bonus is not None and answers != player.participant.vars.get('average_beliefs'):
            return {player.id_in_group: dict(error='Your estimate has already been submitted.')}
        if bonus is None:
            eligible = [row for row in average_rows(player)
                        if row['kind'] in ('score', 'satisfaction')
                        and row.get('incentive_amount', 0) > 0 and row['available']]
            if eligible:
                items = []
                for row in eligible:
                    guess = answers[str(row['period'])]
                    error = abs(guess - row['actual'])
                    earned = error <= row['incentive_tolerance'] + 1e-10
                    items.append(dict(period=row['period'], guess=guess, actual=row['actual'],
                                      absolute_error=error, tolerance=row['incentive_tolerance'],
                                      amount=row['incentive_amount'] if earned else 0))
                player.participant.vars['average_belief_bonus'] = dict(
                    version=1, items=items, amount=sum(item['amount'] for item in items))
        player.participant.vars['average_beliefs'] = answers
        return {player.id_in_group: dict(saved=True)}

    @staticmethod
    def error_message(player, values):
        if 'average_beliefs' not in player.participant.vars:
            return 'Please save your estimates before continuing.'


class AverageTruth(Page):
    @staticmethod
    def is_displayed(player):
        return AverageBeliefs.is_displayed(player) and player.participant.vars.get('reveal_truth', False)

    @staticmethod
    def vars_for_template(player):
        rows = average_rows(player)
        for row in rows:
            row['guess'] = player.participant.vars.get('average_beliefs', {}).get(str(row['period']), '')
            if row['kind'] == 'score' and row['available']:
                gap = row['reported'] - row['actual']
                row['has_gap'] = not math.isclose(gap, 0, abs_tol=1e-10)
                # New quantitative-only groups have exactly two components.
                # Keep the displayed gap as denominator for historical groups
                # too. Do not clamp signed shares when components offset.
                row['selection_percent'] = (
                    str(round(100 * row['selection'] / gap)) if row['has_gap'] else '')
        return dict(rows=rows, qualitative=player.participant.vars['social_type'] == 'qualitative_social')


class AverageOutcomes(Page):
    @staticmethod
    def is_displayed(player):
        return AverageBeliefs.is_displayed(player)

    @staticmethod
    def vars_for_template(player):
        from . import MOOD_CHOICES, LIKERT_CHOICES, IQ_PERCEPTION_CHOICES, CFG, _stable_shuffled, TASK_CONSTRUCT
        rows = [dict(period=row['period'], task_label=row['task_label'],
                     task_construct=TASK_CONSTRUCT[player.participant.vars['period_tasks'][row['period']-1]])
                for row in average_rows(player)]
        questions = [dict(key='mood')] + [dict(row, key=f"satisfaction_{row['period']}") for row in rows]
        if CFG['show_iq']:
            questions.append(dict(key='iq_perception'))
        questions = _stable_shuffled(player, 'average-outcomes', questions)
        player.participant.vars['average_outcome_order'] = [q['key'] for q in questions]
        return dict(rows=rows, mood_choices=MOOD_CHOICES, satisfaction_choices=LIKERT_CHOICES,
                    show_iq=CFG['show_iq'], iq_perception_choices=IQ_PERCEPTION_CHOICES,
                    questions=questions)

    @staticmethod
    def live_method(player, data):
        from . import CFG
        keys = ['mood'] + [f"satisfaction_{row['period']}" for row in average_rows(player)]
        if CFG['show_iq']:
            keys.append('iq_perception')
        try:
            if not isinstance(data, dict) or any(isinstance(data.get(key), bool)
                                               or str(data.get(key)) not in ('1', '2', '3', '4', '5')
                                               for key in keys):
                raise ValueError()
            answers = {key: int(data[key]) for key in keys}
            if any(value not in range(1, 6) for value in answers.values()):
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            return {player.id_in_group: dict(error='Please answer every question.')}
        player.participant.vars['average_outcomes'] = answers
        return {player.id_in_group: dict(saved=True)}

    @staticmethod
    def error_message(player, values):
        if 'average_outcomes' not in player.participant.vars:
            return 'Please answer every question.'
