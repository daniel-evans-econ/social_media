"""Exercise oTree CSV compatibility on two isolated sessions, including unplayed rounds."""
import csv
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(OTREE_IN_MEMORY='1', DATABASE_URL='sqlite://')
os.environ.pop('OTREE_EPHEMERAL', None)
import otree.database
otree.database.load_in_memory_db = lambda: None
from otree.database import db, init_orm
init_orm()
from otree.session import create_session
from otree import export
from survey_exports import csv_chunks
from social_media import Player

sessions = [create_session('cognitive_tasks', num_participants=n) for n in (7, 2)]
p = sessions[0].get_participants()[0]
p.label = 'example, ""label""'
p.initialize(p.label)
p.vars['selfie'] = {'confirmed_at': '2026-01-01'}
p.get_player('social_media', 1).display_name = 'Café, tester'
db.commit()
for code in (sessions[1].code, None):
    for kind in ('wide', 'custom', 'app'):
        expected = io.StringIO()
        if kind == 'wide':
            export.export_wide(expected, session_code=code)
        else:
            fn = export.custom_export_app if kind == 'custom' else export.export_app
            fn('social_media', expected, session_code=code)
        actual = b''.join(csv_chunks(kind, code, True)).decode('utf-8-sig')
        if actual != expected.getvalue():
            wanted = list(csv.reader(io.StringIO(expected.getvalue())))
            got = list(csv.reader(io.StringIO(actual)))
            for i, (a,b) in enumerate(zip(wanted, got)):
                for j,(x,y) in enumerate(zip(a,b)):
                    if x!=y:
                        raise AssertionError((kind, i, j, wanted[0][j], x, y))
            raise AssertionError((kind,len(wanted),len(got)))
        print('Exact CSV match:',kind,'scoped' if code else 'all sessions')
