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
        Round(5, report_shared=True, report_number=3, report_message='I got 3 out of 5 abstract reasoning questions in this block correct.',
              report_display_name='Me', received_signal_name='Peer', received_signal_text='I got 4 out of 5 correct.'),
        Round(10, report_shared=False, report_number=1, report_message='UNSENT'),
        Round(15, report_shared=False, iq_report_shared=True, iq_report_message='IQ MUST NOT APPEAR'),
    ]
    player = SimpleNamespace(round_number=15, participant=SimpleNamespace(code='qa', vars={
        'display_name': 'Me', 'avatar_choice': 'feminine-v2-3',
        'sent_message_times': {'block-5': '2026-10-06T12:00:00Z'},
        'received_message_times': {'5': '2026-10-06T11:59:00Z'},
    }), in_rounds=lambda start, end: rounds)
    with patch.object(survey.random.Random, 'randint', return_value=0):
        messages = survey.reaction_feedback_messages(player)
    assert [m['key'] for m in messages] == ['block-5', 'received-5']
    assert all(m['total'] == 0 and m['reactions'] == [] for m in messages)
    assert all(len(m['all_reactions']) == 6 for m in messages)
    assert messages[0]['avatar'] == 'feminine-v2-3'
    assert messages[0]['text'] == 'I got 3 out of 5 correct.'
    assert messages[1]['avatar'] is None
    assert messages[1]['initial'] == 'P'
    assert messages[0]['timestamp'] == '2026-10-06T12:00:00Z'
    assert messages[1]['timestamp'] == '2026-10-06T11:59:00Z'
    assert len(survey.AVATAR_OPTIONS) == 10
    assert 'wow' not in survey.REACTION_VALUES
    assert all('neutral' not in option['value'] for option in survey.AVATAR_OPTIONS)
    player.participant.vars['avatar_choice'] = 'neutral-3'
    assert survey.own_avatar(player) == 'neutral-3'  # Preserve historical selections.
    player.participant.vars['avatar_choice'] = 'fox'
    assert survey.own_avatar(player) in [option['value'] for option in survey.AVATAR_OPTIONS]
    assert survey.own_avatar(player) == survey.avatar_for_name('Me')
    player.participant.vars['avatar_choice'] = 'feminine-v2-3'
    first = survey.reaction_feedback_messages(player)
    assert all(0 <= m['total'] <= 6 and len(m['reactions']) <= min(6, m['total']) for m in first)
    assert first == survey.reaction_feedback_messages(player)
    baseline = {m['key']: m for m in first}
    base_counts = {r['value']: r['count'] for r in baseline['received-5']['all_reactions']}
    base_names = {r['value']: r['reactors'] for r in baseline['received-5']['all_reactions']}
    for option in survey.REACTION_OPTIONS:
        rounds[0].fields['received_reaction'] = option['value']
        updated = {m['key']: m for m in survey.reaction_feedback_messages(player)}
        assert updated['block-5'] == baseline['block-5']
        peer = updated['received-5']
        assert peer['viewer_reaction'] == option['value']
        assert peer['total'] == baseline['received-5']['total'] + 1
        assert {r['value']: r['count'] for r in peer['all_reactions']} == {
            value: count + int(value == option['value']) for value, count in base_counts.items()}
        for reaction in peer['all_reactions']:
            expected = base_names[reaction['value']] + (['Me (You)'] if reaction['value'] == option['value'] else [])
            assert reaction['reactors'] == expected
            assert len(reaction['reactors']) == reaction['count']
        assert updated == {m['key']: m for m in survey.reaction_feedback_messages(player)}
    rounds[0].fields['received_reaction'] = 'none'
    assert survey.reaction_feedback_messages(player) == first
    with patch.object(survey.random.Random, 'randint', return_value=0):
        rounds[0].fields['received_reaction'] = 'love'
        peer = next(m for m in survey.reaction_feedback_messages(player) if not m['is_own'])
        assert peer['synthetic_total'] == 0 and peer['total'] == 1
        assert [(r['value'], r['count']) for r in peer['reactions']] == [('love', 1)]
    rounds[0].fields['received_reaction'] = 'none'
    assert [m['total'] for m in first] == sorted((m['total'] for m in first), reverse=True)
    assert all([r['count'] for r in m['reactions']] == sorted((r['count'] for r in m['reactions']), reverse=True) for m in first)
    totals = []
    distinct_types = set()
    for seed in range(1000):
        player.participant.code = f'sparse-qa-{seed}'
        for message in survey.reaction_feedback_messages(player):
            assert 0 <= message['total'] <= 6 and len(message['reactions']) <= min(6, message['total'])
            names = [name for reaction in message['all_reactions'] for name in reaction['reactors']]
            assert len(names) == len(set(names)) == message['total']
            assert all(len(r['reactors']) == r['count'] for r in message['all_reactions'])
            assert all(name.startswith('PreviewUser') for name in names)
            totals.append(message['total'])
            distinct_types.add(len(message['reactions']))
    assert max(distinct_types) > 2
    assert 2.8 < sum(totals) / len(totals) < 3.2
    print(f"Synthetic counts: mean {sum(totals) / len(totals):.2f}, range {min(totals)}–{max(totals)}, across {len(totals)} messages.")
    print('Passed: membership, zero-count messages and badges, stable ties, timestamps, avatars, and ranking.')


if __name__ == '__main__':
    main()
