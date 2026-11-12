"""Bounded CSV downloads for this single-app oTree study."""
import csv
import datetime
import io
from contextlib import closing
from functools import lru_cache

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session as DatabaseSession, load_only, selectinload
from sqlalchemy.pool import NullPool
from starlette.concurrency import run_in_threadpool
from starlette.responses import PlainTextResponse, StreamingResponse

from otree import export, settings
from otree.database import engine
from otree.models import Participant, Session
from otree.session import SessionConfig

from social_media import Group, Player, Subsession, custom_export


@lru_cache(maxsize=1)
def download_engine():
    if engine.dialect.name == 'postgresql':
        # The survey uses a shared connection. Downloads get a separate,
        # consistent snapshot and release the connection on disconnect.
        return create_engine(engine.url, poolclass=NullPool, isolation_level='REPEATABLE READ')
    return engine


def pages(query, key, size):
    last_id = 0
    while True:
        batch = query.filter(key > last_id).order_by(key).limit(size).all()
        if not batch:
            return
        yield batch
        last_id = batch[-1].id


def columns(model):
    return export.get_fields_for_csv(model)


def values(obj, fields):
    # Player's oTree attribute accessor raises for unfilled survey fields.
    data = vars(obj)
    if isinstance(obj, Player):
        data = dict(data)
        export.tweak_player_values_dict(data)
    return [data[name] for name in fields]


def wide_rows(db, session_code):
    sessions = db.query(Session).order_by(Session.id)
    if session_code:
        sessions = sessions.filter_by(code=session_code)
    sessions = sessions.all()
    config_fields = ['name']
    for session in sessions:
        for name in SessionConfig(session.config).editable_fields():
            if name not in config_fields:
                config_fields.append(name)
    pfields, sfields = columns(Participant), columns(Session)
    period_models = (Player, Group, Subsession)
    fields = [columns(model) for model in period_models]
    people = db.query(Participant)
    if session_code:
        people = people.filter(Participant.session_id.in_([s.id for s in sessions]))
    if people.first() is None:
        yield []
        return
    session_by_id = {s.id: s for s in sessions}
    rounds = db.query(func.max(Subsession.round_number)).scalar() or 0
    header = [f'participant.{f}' for f in pfields + list(settings.PARTICIPANT_FIELDS)]
    header += [f'session.{f}' for f in sfields]
    header += [f'session.config.{f}' for f in config_fields]
    header += [f'session.{f}' for f in settings.SESSION_FIELDS]
    header += [f'social_media.{period}.{model.__name__.lower()}.{f}'
               for period in range(1, rounds+1) for model, names in zip(period_models, fields) for f in names]
    yield header
    for batch in pages(people, Participant.id, 6):
        ids = [person.id for person in batch]
        players = db.query(Player).filter(Player.participant_id.in_(ids)).options(
            selectinload(Player.group), selectinload(Player.subsession))
        by_period = {(p.participant_id, p.round_number): p for p in players}
        for person in batch:
            session = session_by_id[person.session_id]
            row = values(person, pfields) + [person.vars.get(f) for f in settings.PARTICIPANT_FIELDS]
            row += values(session, sfields) + [session.config.get(f) for f in config_fields]
            row += [session.vars.get(f) for f in settings.SESSION_FIELDS]
            for period in range(1, rounds+1):
                player = by_period.get((person.id, period))
                if player is None:
                    row.extend([''] * sum(map(len, fields)))
                else:
                    for obj, names in zip((player, player.group, player.subsession), fields):
                        row.extend(values(obj, names))
            yield row


def app_rows(db, session_code, custom):
    players = db.query(Player)
    if session_code:
        session_id = db.query(Session.id).filter_by(code=session_code).scalar()
        players = players.filter(Player.session_id == session_id)
    if custom:
        # These are the only rounds consumed by the study's custom export.
        players = players.filter(Player.round_number.in_((15, 30, 45))).options(
            load_only(Player.id, Player.round_number, Player.participant_id, Player.session_id))
    relations = [Player.participant, Player.session]
    if not custom:
        relations.extend((Player.group, Player.subsession))
    players = players.options(*(selectinload(rel) for rel in relations))
    records = (p for batch in pages(players, Player.id, 90) for p in batch)
    if custom:
        yield from custom_export(records)
        return
    models = (Participant, Player, Group, Subsession, Session)
    fields = [columns(model) for model in models]
    yield [f'{model.__name__.lower()}.{f}' for model, names in zip(models, fields) for f in names]
    for p in records:
        objects = (p.participant, p, p.group, p.subsession, p.session)
        yield [v for obj, names in zip(objects, fields) for v in values(obj, names)]


def csv_chunks(kind, session_code, excel):
    with closing(DatabaseSession(bind=download_engine())) as db:
        rows = wide_rows(db, session_code) if kind == 'wide' else app_rows(db, session_code, kind == 'custom')
        buf = io.StringIO()
        if excel:
            buf.write(export.BOM)
        writer = csv.writer(buf)
        for row in rows:
            writer.writerow(map(export.sanitize_for_csv, row))
            if buf.tell() >= 32768:
                yield buf.getvalue().encode()
                buf.seek(0)
                buf.truncate()
        if buf.tell():
            yield buf.getvalue().encode()


async def stream_chunks(source):
    try:
        while True:
            chunk = await run_in_threadpool(next, source, None)
            if chunk is None:
                break
            yield chunk
    finally:
        source.close()


def download(request, kind):
    params = request.query_params
    session_code = params.get('session_code')
    if session_code and not Session.objects_filter(code=session_code).first():
        return PlainTextResponse('Unknown session.', status_code=404)
    if kind not in ('wide', 'app', 'custom') or params.get('app', 'social_media') != 'social_media':
        return PlainTextResponse('Unknown export.', status_code=404)
    if kind == 'custom' and params.get('function_name', 'custom_export') != 'custom_export':
        return PlainTextResponse('Unknown custom export.', status_code=404)
    stem = {'wide': 'all_apps_wide', 'app': 'social_media', 'custom': 'social_media_custom_export'}[kind]
    scope = f'-{session_code}' if session_code else ''
    filename = f'{stem}{scope}-{datetime.date.today().isoformat()}.csv'
    return StreamingResponse(
        stream_chunks(csv_chunks(kind, session_code, params.get('format') == 'csv_bom')),
        media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"',
                                       'Cache-Control': 'no-store'},
    )
