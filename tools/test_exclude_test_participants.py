"""Checks that test participants cannot enter future message or norming pools."""
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.exclude_test_participants import exclude_test_rows
from tools import build_messages_from_coded, export_pilot_data


class TestParticipantExclusion(unittest.TestCase):
    def test_all_rows_of_identified_participant_are_excluded(self):
        rows = [
            {'pcode': 'test', 'username': ' TestBot '},
            {'pcode': 'test', 'username': ''},
            {'pcode': 'real', 'username': 'Other'},
            {'username': 'testbot'},
            {'username': 'Real'},
        ]
        self.assertEqual(exclude_test_rows(rows), [rows[2], rows[4]])

    def test_wide_export_excludes_test_name_from_any_round(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wide.csv'
            fields = ['participant.code', 'social_media.5.player.report_display_name',
                      'social_media.1.player.q_task']
            with path.open('w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(fields)
                writer.writerow(['test', 'TESTBOT', 'ravens'])
                writer.writerow(['real', 'Other', 'sequences'])
            participants = export_pilot_data._read_wide_csv(path)
            self.assertEqual(len(participants), 1)
            self.assertEqual(participants[0][1]['q_task'], 'sequences')

    def test_coded_builder_excludes_across_sources(self):
        block = [{'pcode': 'test', 'username': 'TestBot'}]
        notes = [dict(pcode=code, username='Other', sent='1', task_specific='0',
                      time_specific='0', nonsense='0', task_label='Abstract reasoning',
                      set_id='easy', msg='A message') for code in ('test', 'real')]
        quant = [dict(pcode=code, username='Other', task='ravens', set_id='easy',
                      report_number='3') for code in ('test', 'real')]
        with patch.object(build_messages_from_coded, '_read_csv', side_effect=[block, notes, quant]), \
             patch.object(Path, 'exists', return_value=True):
            pool, n_quant, n_qual = build_messages_from_coded.build(Path('unused'))
        self.assertEqual((n_quant, n_qual), (1, 1))
        self.assertEqual(len(pool['ravens']['easy']['quantitative']), 1)


if __name__ == '__main__':
    unittest.main()
