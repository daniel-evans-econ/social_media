"""Preserve current-format sessions when belief feedback moves before usage.

Save the dry-run JSON, then --apply in maintenance mode. Previously answered
platform questions are not repeated. A participant waiting on platform usage
starts the belief page first, then returns to their unanswered platform page.
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
OLD = [name for name in NEW if name != 'PlatformUsage']
OLD.insert(OLD.index('AverageBeliefs'), 'PlatformUsage')
COUNT = len(NEW)
MAXIMUM = COUNT * s.C.NUM_ROUNDS


def remap(index, current=False):
    if index is None or index == 0 or index == MAXIMUM + 1:
        return index
    if not 1 <= index <= MAXIMUM:
        raise ValueError(f'Unexpected index {index}')
    rd, offset = divmod(index - 1, COUNT)
    name = OLD[offset]
    if current and name == 'PlatformUsage':
        name = 'AverageBeliefs'
    return rd * COUNT + NEW.index(name) + 1


def migrate(apply=False):
    records = []
    assert NEW.index('AverageOutcomes') < NEW.index('PlatformUsage')
    old_platform = (s.C.NUM_ROUNDS - 1) * COUNT + OLD.index('PlatformUsage') + 1
    for part in Participant.objects_filter():
        if (part.session.config['app_sequence'] != ['social_media']
                or part._max_page_index != MAXIMUM or part.vars.get('belief_before_platform')):
            continue
        fields = ('_index_in_pages', '_timeout_page_index', '_gbat_page_index', '_current_form_page_url')
        before = {key: getattr(part, key) for key in fields}
        after = {key: remap(before[key], current=key == '_index_in_pages') for key in fields[:3]}
        url = before['_current_form_page_url']
        after['_current_form_page_url'] = re.sub(
            r'/(\d+)/?$', lambda m: '/' + str(remap(int(m[1]))), url) if url else url
        if before['_index_in_pages'] == old_platform:
            after['_current_form_page_url'] = None
        completed = before['_index_in_pages'] > old_platform
        record = dict(code=part.code, before=before, after=after, platform_already_completed=completed)
        records.append(record)
        if apply:
            for key, value in after.items():
                setattr(part, key, value)
            part.vars['platform_usage_completed_before_reorder'] = completed
            part.vars['belief_before_platform'] = True
            part.vars['belief_order_migration'] = record
    if apply:
        db.commit()
    return dict(applied=apply, count=len(records), records=records)


if __name__ == '__main__':
    print(json.dumps(migrate('--apply' in sys.argv)))
