"""Focused checks for ranked feedback membership, zero counts, and stable ties."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('OTREE_IN_MEMORY', '1')
os.environ.setdefault('DATABASE_URL', 'sqlite:///db.sqlite3')
import social_media as survey


class Round:
    def __init__(self, number, **fields):
        self.round_number = number
        self.fields = fields

    def field_maybe_none(self, name):
        return self.fields.get(name)


def main():
    rounds = [
        Round(5, report_shared=True, report_number=3, report_message='I got 3 out of 5 correct.',
              report_display_name='Me', received_signal_name='Peer', received_signal_text='I got 4 out of 5 correct.'),
        Round(10, report_shared=False, report_number=1, report_message='UNSENT'),
        Round(15, report_shared=False, iq_report_shared=True, iq_report_message='IQ MUST NOT APPEAR'),
    ]
    player = SimpleNamespace(round_number=15, participant=SimpleNamespace(code='qa', vars={
        'display_name': 'Me', 'avatar_choice': 'fox',
        'sent_message_times': {'block-5': '2026-10-06T12:00:00Z'},
        'received_message_times': {'5': '2026-10-06T11:59:00Z'},
    }), in_rounds=lambda start, end: rounds)
    with patch.object(survey.random.Random, 'randint', return_value=0):
        messages = survey.reaction_feedback_messages(player)
    assert [m['key'] for m in messages] == ['block-5', 'received-5']
    assert all(m['total'] == 0 and m['reactions'] == [] for m in messages)
    assert all(len(m['all_reactions']) == 7 for m in messages)
    assert messages[0]['avatar'] == 'fox'
    assert messages[1]['avatar'] == survey.avatar_for_name('Peer')
    assert messages[0]['timestamp'] == '2026-10-06T12:00:00Z'
    assert messages[1]['timestamp'] == '2026-10-06T11:59:00Z'
    first = survey.reaction_feedback_messages(player)
    assert first == survey.reaction_feedback_messages(player)
    assert [m['total'] for m in first] == sorted((m['total'] for m in first), reverse=True)
    assert all([r['count'] for r in m['reactions']] == sorted((r['count'] for r in m['reactions']), reverse=True) for m in first)
    print('Passed: membership, zero-count messages and badges, stable ties, timestamps, avatars, and ranking.')


if __name__ == '__main__':
    main()
