"""Filter known TestBot participants from wide or tidy exports without deleting raw data.

Usage: python tools/exclude_test_participants.py input.csv clean.csv
Excludes the whole participant when any row identifies their username as TestBot.
"""
import csv
from pathlib import Path
import sys


def is_test_row(row):
    name_fields = {'username', 'display_name', 'report_display_name'}
    return any(
        (key in name_fields or key.endswith('.player.report_display_name'))
        and str(value or '').strip().casefold() == 'testbot'
        for key, value in row.items()
    )


def participant_code(row):
    return row.get('participant.code') or row.get('pcode') or row.get('participant_code')


def exclude_test_rows(rows):
    excluded_codes = {participant_code(row) for row in rows if is_test_row(row)} - {None, ''}
    return [row for row in rows if not is_test_row(row) and participant_code(row) not in excluded_codes]


if __name__ == '__main__':
    source, target = map(Path, sys.argv[1:])
    if source.resolve() == target.resolve():
        raise ValueError('Write a separate cleaned file; preserve the original export.')
    with source.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        rows, fields = list(reader), reader.fieldnames
    clean = exclude_test_rows(rows)
    with target.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clean)
    print(f'Kept {len(clean)} rows; excluded {len(rows) - len(clean)} test rows.')
