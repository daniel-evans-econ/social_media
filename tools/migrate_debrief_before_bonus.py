"""Back up and remap current-format preview progress without changing answers/payoffs.

Run first without --apply and save JSON, then apply while Heroku is in maintenance.
Participants on either final screen resume at the debrief, then see the bonus
summary. Finished participants remain finished; their recorded payments stay put.
"""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from otree.database import init_orm, db
init_orm()
from otree.models import Participant
import social_media as s

PAGE_COUNT = 38
MAX_INDEX = PAGE_COUNT * s.C.NUM_ROUNDS


def remap(index, current=False):
    if index is None or index == 0 or index == MAX_INDEX + 1:
        return index
    if not 1 <= index <= MAX_INDEX:
        raise ValueError(f'Unexpected index: {index}')
    rd, offset = divmod(index - 1, PAGE_COUNT)
    if current and rd == s.C.NUM_ROUNDS - 1 and offset in (36, 37):
        return rd * PAGE_COUNT + 37
    return rd * PAGE_COUNT + (38 if offset == 36 else 37 if offset == 37 else offset + 1)


def migrate(apply=False):
    assert len(s.page_sequence) == PAGE_COUNT
    assert [p.__name__ for p in s.page_sequence[-2:]] == ['IQDebrief', 'FinalResults']
    records, skipped = [], []
    for part in Participant.objects_filter():
        if part.session.config['app_sequence'] != ['social_media'] or part.vars.get('debrief_before_bonus_version'):
            continue
        if part._max_page_index != MAX_INDEX:
            skipped.append(part.code)
            continue
        fields = ('_index_in_pages', '_timeout_page_index', '_gbat_page_index', '_current_form_page_url')
        before = {key: getattr(part, key) for key in fields}
        after = {key: remap(before[key], current=key == '_index_in_pages') for key in fields[:3]}
        url = before['_current_form_page_url']
        after['_current_form_page_url'] = re.sub(r'/(\d+)/?$', lambda m: '/' + str(remap(int(m[1]))), url) if url else url
        if before['_index_in_pages'] in (MAX_INDEX - 1, MAX_INDEX):
            after['_current_form_page_url'] = None
        record = dict(code=part.code, before=before, after=after,
                      payoff=float(part.payoff), accuracy_bonus_results=part.vars.get('accuracy_bonus_results'))
        records.append(record)
        if apply:
            for key, value in after.items():
                setattr(part, key, value)
            part.vars['debrief_before_bonus_version'] = 1
            part.vars['debrief_before_bonus_migration'] = record
    if apply:
        db.commit()
    return dict(applied=apply, count=len(records), records=records, skipped=skipped)


if __name__ == '__main__':
    print(json.dumps(migrate('--apply' in sys.argv)))
