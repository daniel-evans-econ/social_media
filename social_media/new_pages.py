"""New pilot pages. Responses live in participant.vars and the custom export.

No schema reset is required; existing participants keep their previous flow.
"""
import base64
import io
import math
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


def average_rows(player):
    from . import TASK_LABELS
    snapshots = player.participant.vars.get('average_feedback')
    if snapshots is None:
        snapshots = [averages(player, p) for p in completed_periods(player)]
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
            return {player.id_in_group: dict(error='Please take and confirm your photograph again.')}

    @staticmethod
    def error_message(player, values):
        if not player.participant.vars.get('selfie', {}).get('image'):
            return 'Please take and confirm your photograph before continuing.'


class AverageBeliefs(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 45 and player.participant.vars.get('linked_peer_groups', False)

    @staticmethod
    def vars_for_template(player):
        # Do not even send the unrevealed values to the template/debug context.
        allowed = {'period', 'task_label', 'available', 'reported_text', 'kind'}
        rows = [{key:value for key,value in row.items() if key in allowed}
                for row in average_rows(player)]
        return dict(rows=rows,
                    qualitative=player.participant.vars['social_type'] == 'qualitative_social')

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
                if not math.isfinite(value) or not 0 <= value <= (100 if row['kind'] == 'happy' else 15):
                    raise ValueError()
                answers[str(row['period'])] = value
        except (ValueError, TypeError):
            return {player.id_in_group: dict(error='Please answer each question within the displayed range.')}
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
                # Never call this a complete two-part decomposition: the numeric
                # reporting subset can differ from the entire comparison group.
                row['components'] = [
                    dict(label='Selective sending within the numerical-reporting group', value=f"{row['selection']:+.1f}"),
                    dict(label='Differences between reported and actual scores in sent messages', value=f"{row['misreporting']:+.1f}"),
                    dict(label='Differences between numerical reporters and the whole comparison group', value=f"{row['reporting_subset']:+.1f}"),
                ]
        return dict(rows=rows, qualitative=player.participant.vars['social_type'] == 'qualitative_social')


class AverageOutcomes(Page):
    @staticmethod
    def is_displayed(player):
        return AverageBeliefs.is_displayed(player)

    @staticmethod
    def vars_for_template(player):
        from . import MOOD_CHOICES, LIKERT_CHOICES
        rows = [dict(period=row['period'], task_label=row['task_label']) for row in average_rows(player)]
        return dict(rows=rows, mood_choices=MOOD_CHOICES, satisfaction_choices=LIKERT_CHOICES)

    @staticmethod
    def live_method(player, data):
        keys = ['mood'] + [f'satisfaction_{p}' for p in completed_periods(player)]
        try:
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
