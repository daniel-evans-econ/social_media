"""Preserve progress when performance concern moves immediately after effort.

Save the dry-run output before applying under maintenance mode. Existing
answers and payments are untouched; completed pages are skipped on resumption.
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

NEW = [page.__name__ for page in s.page_sequence]
OLD = NEW.copy()
OLD.remove('OutcomeConcern')
OLD.insert(OLD.index('Demographics') + 1, 'OutcomeConcern')
MAX_INDEX = len(NEW) * s.C.NUM_ROUNDS
MOVED = OLD[OLD.index('IQCredibility'):OLD.index('OutcomeConcern') + 1]


def final_index(name):
    return (s.C.NUM_ROUNDS - 1) * len(OLD) + OLD.index(name) + 1


def remap(index, current=False):
    if index in (None, 0, MAX_INDEX + 1):
        return index
    if not 1 <= index <= MAX_INDEX:
        raise ValueError(f'Unexpected index: {index}')
    rd, offset = divmod(index - 1, len(OLD))
    name = OLD[offset]
    if current and rd == s.C.NUM_ROUNDS - 1 and name in MOVED:
        name = 'OutcomeConcern'
    return rd * len(NEW) + NEW.index(name) + 1


def migrate(apply=False):
    assert len(NEW) == 38
    assert NEW[NEW.index('TaskEffort') + 1:NEW.index('TaskEffort') + 3] == ['OutcomeConcern', 'IQCredibility']
    records, skipped = [], []
    for part in Participant.objects_filter():
        if part.session.config['app_sequence'] != ['social_media'] or part.vars.get('outcome_concern_order_version'):
            continue
        if part._max_page_index != MAX_INDEX or not part.vars.get('debrief_before_bonus_version'):
            skipped.append(part.code)
            continue
        fields = ('_index_in_pages', '_timeout_page_index', '_gbat_page_index', '_current_form_page_url')
        before = {key: getattr(part, key) for key in fields}
        after = {key: remap(before[key], current=key == '_index_in_pages') for key in fields[:3]}
        url = before['_current_form_page_url']
        after['_current_form_page_url'] = re.sub(r'/(\d+)/?$', lambda m: '/' + str(remap(int(m[1]))), url) if url else url
        if final_index('IQCredibility') <= before['_index_in_pages'] <= final_index('OutcomeConcern'):
            after['_current_form_page_url'] = None
        completed_before = list(part.vars.get('completed_before_posttask_reorder', []))
        completed = list(dict.fromkeys(completed_before + [name for name in MOVED if final_index(name) < before['_index_in_pages']]))
        record = dict(code=part.code, before=before, after=after,
                      completed_before=completed_before, completed=completed, payoff=float(part.payoff))
        records.append(record)
        if apply:
            for key, value in after.items():
                setattr(part, key, value)
            part.vars['completed_before_posttask_reorder'] = completed
            part.vars['outcome_concern_order_version'] = 1
            part.vars['outcome_concern_order_migration'] = record
    if apply:
        db.commit()
    return dict(applied=apply, count=len(records), records=records, skipped=skipped)


if __name__ == '__main__':
    print(json.dumps(migrate('--apply' in sys.argv)))
