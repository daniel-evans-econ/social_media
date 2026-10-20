"""List/delete blurred images in the configured study database.

Read-only by default. Examples:
  heroku run "python -m tools.manage_selfies" --app cognitive-tasks
  heroku run "python -m tools.manage_selfies --delete CODE" --app cognitive-tasks
  heroku run "python -m tools.manage_selfies --delete-expired" --app cognitive-tasks
  heroku run "python -m tools.manage_selfies --delete-all" --app cognitive-tasks

Delete earlier at the end of phase two. Expiry uses 180 days, conservatively
within six calendar months. This does not delete external database backups.
"""
import argparse
from datetime import datetime, timedelta, timezone


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--delete', metavar='PARTICIPANT_CODE')
    group.add_argument('--delete-expired', action='store_true')
    group.add_argument('--delete-all', action='store_true')
    args = parser.parse_args()
    from otree.main import setup
    setup()
    from otree.database import db
    from otree.models import Participant
    now = datetime.now(timezone.utc)
    changed = 0
    for participant in db.query(Participant).all():
        photo = participant.vars.get('selfie', {})
        if not photo.get('image'):
            continue
        expires = datetime.fromisoformat(photo['confirmed_at']) + timedelta(days=180)
        delete = args.delete_all or participant.code == args.delete or (args.delete_expired and now >= expires)
        if delete:
            participant.vars['selfie'] = dict(confirmed_at=photo['confirmed_at'], deleted_at=now.isoformat())
            changed += 1
        print(participant.code, 'DELETED' if delete else 'stored', 'delete-by', expires.date())
    if changed:
        db.commit()
    print(f'Deleted {changed} stored images.')


if __name__ == '__main__':
    main()
