"""Run with python -m tools.test_researcher_selfies. Uses only an in-memory oTree database."""
import base64
import hashlib
import io
import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from zipfile import ZipFile

os.environ.update(OTREE_IN_MEMORY='1', DATABASE_URL='sqlite://')
import otree.database
otree.database.load_in_memory_db = lambda: None
from otree.database import db, init_orm
init_orm()
from otree.models import Session, Participant
from starlette.applications import Starlette
from starlette.testclient import TestClient
from PIL import Image
import researcher_selfies as portal


def photo(color):
    buf = io.BytesIO()
    Image.new('RGB', (72, 72), color).save(buf, 'JPEG')
    return buf.getvalue()


def run():
    now = datetime(2026, 11, 13, tzinfo=timezone.utc)
    with patch.object(portal, 'datetime', wraps=datetime) as clock:
        clock.now.return_value = now
        session, other = Session(), Session()
        db.add(session)
        db.add(other)
        records = [Participant(session=session, id_in_session=i) for i in [1, *range(13, 19)]]
        records.append(Participant(session=other, id_in_session=13))
        for person in records:
            db.add(person)
        db.commit()
        raw = [photo(n * 31) for n in range(len(records))]
        for person, img in zip(records, raw):
            person.vars['selfie_consent'] = True
            person.vars['selfie'] = dict(image='data:image/jpeg;base64,' + base64.b64encode(img).decode(),
                                        confirmed_at=now.isoformat(), blur=10)
        records[2].vars['selfie_consent'] = False
        records[3].vars['selfie'] = dict(deleted_at=now.isoformat())
        records[4].vars['selfie'] = dict(records[4].vars['selfie'],
                                         confirmed_at=(now-timedelta(days=181)).isoformat())
        db.commit()
        client = TestClient(Starlette(routes=portal.researcher_routes), base_url='https://testserver')
        body = dict(username='test', password='synthetic-only')
        with patch.object(portal, 'SESSION', session.code), patch.dict(os.environ):
            os.environ.pop('WAVE1_SELFIE_ACCESS', None)
            assert client.get(portal.PATH).status_code == 404
            os.environ['WAVE1_SELFIE_ACCESS'] = json.dumps({
                'accounts': {'test': hashlib.sha256(body['password'].encode()).hexdigest()},
                'photos': [hashlib.sha256(x).hexdigest() for x in raw if x != raw[5]]})
            assert client.get(portal.PATH).status_code == 200
            assert client.post(portal.PATH, data={'username': ''}).status_code == 401
            assert client.post(portal.PATH, data=dict(body, password='wrong')).status_code == 401
            assert client.get('http://testserver'+portal.PATH).status_code == 403
            resp = client.post(portal.PATH, data=body)
            assert resp.status_code == 200 and 'no-store' in resp.headers['cache-control']
            with ZipFile(io.BytesIO(resp.content)) as result:
                assert result.namelist() == ['selfie-001.jpg', 'selfie-002.jpg']
                assert [result.read(name) for name in result.namelist()] == [raw[1], raw[6]]
            clock.now.return_value = portal.END
            assert client.post(portal.PATH, data=body).status_code == 404
    print('Passed: personal login, HTTPS, session and index scope, consent, withdrawal, expiry, JPEG-only ZIP.')


if __name__ == '__main__':
    run()
