"""Build linked reference records; never export Prolific IDs or raw demographics.

Scores and reports are historical pilot observations, not scores on the new
fixed question set. Keep this distinction in participant-facing descriptions.
"""
import csv
import hashlib
import json
import random
from pathlib import Path
from tools.exclude_test_participants import exclude_test_rows, is_test_row


def build(root):
    def read(name):
        with (root / name).open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream))
    blocks = read('block_level.csv')
    # Assign once per sender from reported demographics, never from usernames.
    avatars = {}
    for participant in read('participant_level.csv'):
        style = {'woman': 'feminine', 'man': 'masculine'}.get(participant['gender'].strip().lower())
        avatars[participant['pcode']] = (
            random.Random('peer-avatar-' + participant['pcode']).choice(
                [f'{style}-v2-{i}' for i in (1, 3, 2, 5, 4)]) if style else None)
    excluded = {r['pcode'] for r in blocks if is_test_row(r)}
    notes = {(r['pcode'], r['block_global']): r for r in read('notes_coded.csv')}
    periods = exclude_test_rows(read('period_level.csv'))
    result = {}
    for period in periods:
        if period['pcode'] in excluded or period['finished'].lower() not in ('true', '1') or int(float(period['n_q'])) != 15:
            continue
        rows = [r for r in blocks if r['pcode'] == period['pcode'] and r['period'] == period['period']]
        if len(rows) != 3:
            continue
        key = hashlib.sha256((period['pcode'] + ':' + period['period']).encode()).hexdigest()[:16]
        satisfaction = float(period['perf_sat'])
        if satisfaction not in (1, 2, 3, 4, 5):
            raise ValueError('Completed reference period lacks a valid satisfaction response.')
        record = dict(id=key, score=int(float(period['score15'])),
                      performance_satisfaction=int(satisfaction), blocks=[], messages=[])
        for row in rows:
            shared = row['shared'].lower() in ('true', '1', '1.0')
            numeric = row['report_number'] not in ('', 'NA', 'nan')
            number = int(float(row['report_number'])) if numeric else None
            record['blocks'].append(dict(score=int(float(row['score'])), report=number, sent=shared,
                                         emoji=row['report_emoji'] if row['condition'] == 'qualitative_social' else ''))
            if not shared:
                continue
            message = dict(id=key + '-' + row['block_global'], name=row['username'],
                           avatar=avatars.get(period['pcode']),
                           source_task=period['task'], source_set_id=row['set_id'])
            if numeric:
                message.update(kind='quantitative', number=number)
            else:
                note = notes.get((row['pcode'], row['block_global']))
                if not note or any(note.get(k) not in ('0', '0.0', 'False', 'false') for k in
                                   ('task_specific', 'time_specific', 'nonsense')):
                    continue
                message.update(kind='qualitative', sentence=row['report_message'], emoji=row['report_emoji'])
            record['messages'].append(message)
        result.setdefault(period['task'], []).append(record)
    return result


if __name__ == '__main__':
    import sys
    import os
    from dotenv import load_dotenv
    from cryptography.fernet import Fernet
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    key = os.environ.get('PEER_REFERENCE_KEY')
    if not key:
        raise SystemExit('Set PEER_REFERENCE_KEY before building the encrypted reference file.')
    root = Path(sys.argv[1])
    target = Path(__file__).resolve().parents[1] / 'social_media/data/peer_reference_initial.fernet'
    data = build(root)
    target.write_bytes(Fernet(key.encode()).encrypt(json.dumps(data, ensure_ascii=False).encode('utf-8')))
    print({task: len(rows) for task, rows in data.items()})
