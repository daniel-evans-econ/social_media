"""Preserve existing participants' positions when IQDebrief is appended.

Run a dry run and save its JSON before --apply, with the survey in maintenance
mode. This changes navigation metadata only, not responses or payments.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from otree.database import init_orm, db
init_orm()
from otree.models import Participant
import social_media as survey

OLD_COUNT = 36
NEW_COUNT = 37
OLD_MAX = OLD_COUNT * survey.C.NUM_ROUNDS
NEW_MAX = NEW_COUNT * survey.C.NUM_ROUNDS


def remap(index):
    if index is None or index == 0:
        return index
    if index == OLD_MAX + 1:
        return NEW_MAX + 1
    if not 1 <= index <= OLD_MAX:
        raise ValueError(f'Unexpected old page index: {index}')
    return index + (index - 1) // OLD_COUNT


def migrate(apply=False):
    assert len(survey.page_sequence) == NEW_COUNT
    assert survey.page_sequence[-1] is survey.IQDebrief
    records, skipped = [], []
    for part in Participant.objects_filter():
        if part.session.config['app_sequence'] != ['social_media']:
            continue
        if part._max_page_index == NEW_MAX:
            continue
        if part._max_page_index != OLD_MAX:
            skipped.append(dict(code=part.code, maximum=part._max_page_index))
            continue
        fields = ('_index_in_pages', '_max_page_index', '_timeout_page_index',
                  '_gbat_page_index', '_current_form_page_url')
        before = {key: getattr(part, key) for key in fields}
        after = {key: remap(before[key]) for key in fields[:4]}
        after['_max_page_index'] = NEW_MAX
        url = before['_current_form_page_url']
        after['_current_form_page_url'] = re.sub(
            r'/(\d+)/?$', lambda m: '/' + str(remap(int(m[1]))), url) if url else url
        record = dict(code=part.code, session=part.session.code, before=before, after=after)
        records.append(record)
        if apply:
            for key, value in after.items():
                setattr(part, key, value)
            part.vars['debrief_navigation_migration'] = record
    if apply:
        db.commit()
    return dict(applied=apply, count=len(records), records=records, skipped=skipped)


if __name__ == '__main__':
    print(json.dumps(migrate('--apply' in sys.argv)))
