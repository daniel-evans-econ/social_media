"""Create researcher-only slots starting at the real correction pages.

Run from the repository root (on Heroku via a one-off dyno). This creates a
separate, clearly labelled test session; it never changes existing participants.
Comparison data are drawn by the normal historical-data code, not fabricated.
The first two slots are for review; the other two can be used for browser QA.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def create_previews():
    from otree.database import db, init_orm
    init_orm()
    from otree.session import create_session
    from otree.lookup import _get_session_lookups
    from social_media.new_pages import AverageBeliefs, average_rows

    session = create_session('cognitive_tasks', num_participants=4,
                             label='RESEARCHER PREVIEW ONLY - statistical correction')
    index = next(i for i, lookup in _get_session_lookups(session.code).items()
                 if lookup.round_number == 45 and lookup.page_class is AverageBeliefs)
    links = []
    for i, participant in enumerate(session.get_participants()):
        kind = 'quantitative_social' if i % 2 == 0 else 'qualitative_social'
        participant.label = 'TestBot-correction-preview-' + str(i + 1)
        participant.vars.update(social_type=kind, reveal_truth=True,
                                third_period_accepted=True, researcher_preview=True)
        participant.initialize(participant.label)
        participant._index_in_pages = index
        rows = average_rows(participant.get_player('social_media', 45))
        links.append(dict(kind=kind, purpose='review' if i < 2 else 'qa',
                          path=participant._url_i_should_be_on(),
                          available_periods=sum(row['available'] for row in rows)))
    db.commit()
    print(json.dumps(dict(session=session.code, links=links)))


if __name__ == '__main__':
    create_previews()
