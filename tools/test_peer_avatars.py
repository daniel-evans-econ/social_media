"""Verify peer avatars use reported demographics, not username cues."""
import csv
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['OTREE_IN_MEMORY'] = '1'
from tools.build_peer_reference import build
from social_media import peer_groups


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    participants = [dict(pcode='a', username='John', gender='woman'),
                    dict(pcode='b', username='mousegirl', gender='man'),
                    dict(pcode='c', username='Seb', gender=''),
                    dict(pcode='d', username='Jane', gender='nonbinary')]
    periods, blocks = [], []
    for participant in participants:
        for period in (1, 2):
            periods.append(dict(pcode=participant['pcode'], period=period,
                                finished='True', n_q=15, score15=6, perf_sat=4, task='sequences'))
            for block in range(1, 4):
                blocks.append(dict(pcode=participant['pcode'], username=participant['username'],
                                   period=period, block_global=(period-1)*3+block,
                                   shared='True', report_number=2, score=2, report_emoji='',
                                   condition='quantitative_social', set_id='test'))
    def write(name, fields, rows):
        with (root/name).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    write('participant_level.csv', list(participants[0]), participants)
    write('period_level.csv', list(periods[0]), periods)
    write('block_level.csv', list(blocks[0]), blocks)
    write('notes_coded.csv', ['pcode', 'block_global'], [])
    result = build(root)
    assert result == build(root)
    by_name = {}
    for row in result['sequences']:
        for message in row['messages']:
            by_name.setdefault(message['name'], set()).add(message['avatar'])
    assert all(len(avatars)==1 for avatars in by_name.values())
    assert next(iter(by_name['John'])).startswith('feminine')
    assert next(iter(by_name['mousegirl'])).startswith('masculine')
    assert by_name['Seb'] == by_name['Jane'] == {None}
    peer_groups._avatar_index.cache_clear()
    with patch.object(peer_groups, 'reference', return_value=result):
        assert peer_groups.reference_avatar('test', name='John').startswith('feminine')
        message = result['sequences'][0]['messages'][0]
        assert peer_groups.reference_avatar('test', message_id=message['id']) == message['avatar']
        assert peer_groups.reference_avatar('test', message_id='missing', name='John') is None
        assert peer_groups.reference_avatar('test', name='Unlisted') is None
        # Identical usernames belonging to different people are not resolved by guessing.
        result['sequences'][1]['messages'][0] = dict(message, id='collision', avatar='masculine-v2-1')
        peer_groups._avatar_index.cache_clear()
        assert peer_groups.reference_avatar('test', name='John') is None
    peer_groups._avatar_index.cache_clear()
print('Passed: reported gender overrides name cues, stable sender avatars, missing gender and duplicate-name handling.')
