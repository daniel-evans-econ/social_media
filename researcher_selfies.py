"""Authenticated access to the participant report for the indexed Wave 1 cohort."""
import base64
import hashlib
import hmac
import json
import os
from contextlib import closing
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

from starlette.concurrency import run_in_threadpool
from starlette.responses import HTMLResponse, PlainTextResponse, Response
from starlette.routing import Route

PATH = '/research/wave-1/selfies'
SESSION = '2us5s6hg'
END = datetime(2027, 5, 12, tzinfo=timezone.utc)
HEADERS = {
    'Cache-Control': 'private, no-store',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
    'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
}
FORM = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Wave 1 participant report</title>
<style>body{font:1rem/1.55 system-ui,sans-serif;max-width:30rem;margin:8vh auto;padding:1rem;color:#203045}
h1{font-size:1.75rem}label{display:block;margin:1rem 0}input{display:block;font:inherit;padding:.4rem;width:90%}
button{font:inherit;padding:.5rem 1rem}</style><main><h1>Wave 1 participant report</h1>
<p>Download profiles, messages and comments for participants who finished the survey. Save the PDF on your password-protected research computer.</p>
<form method="post"><label>Researcher username<input name="username" autocomplete="username" required></label>
<label>Password<input type="password" name="password" autocomplete="current-password" required></label>
<button>Download PDF</button></form></main></html>"""


def participant_report(allowed, now):
    from sqlalchemy.orm import Session as DatabaseSession
    from otree.models import Session, Participant
    from survey_exports import download_engine
    from social_media import Player
    from participant_report import build_pdf, FIELDS

    with closing(DatabaseSession(bind=download_engine())) as db:
        rows = (db.query(Participant.id, Participant.id_in_session, Participant._vars)
                .join(Session, Session.id == Participant.session_id)
                .filter(Session.code == SESSION, Participant.id_in_session >= 13,
                        Participant._current_page_name == 'FinalResults')
                .order_by(Participant.id).yield_per(6))
        profiles = {}
        for pid, slot, values in rows:
            photo = values.get('selfie') or {}
            if values.get('selfie_consent') is not True or photo.get('deleted_at') or photo.get('blur') != 10:
                continue
            image = photo.get('image', '')
            if not image.startswith('data:image/jpeg;base64,'):
                continue
            try:
                confirmed = datetime.fromisoformat(photo['confirmed_at'])
                if not confirmed <= now < min(confirmed + timedelta(days=180), END):
                    continue
                raw = base64.b64decode(image.partition(',')[2], validate=True)
            except (ValueError, KeyError, TypeError):
                continue
            digest = hashlib.sha256(raw).hexdigest()
            if digest not in allowed:
                continue
            allowed.remove(digest)
            keys = ('display_name', 'social_type', 'image_treatment', 'avatar_choice', 'like_treatment',
                    'reveal_truth', 'iq_reference_asked', 'period_1_condition', 'period_2_condition',
                    'period_3_condition', 'third_period_accepted', 'period_tasks')
            profile = {k: values.get(k) for k in keys}
            profile['groups'] = {k: g.get('stratum') for k, g in values.get('peer_groups', {}).items()}
            profiles[pid] = dict(profile, slot=slot, photo=raw, rows=[])
        if not profiles:
            return None
        columns = [getattr(Player, name) for name in FIELDS]
        responses = (db.query(Player.participant_id, *columns)
                     .filter(Player.participant_id.in_(list(profiles)))
                     .order_by(Player.participant_id, Player.round_number))
        for record in responses.yield_per(128):
            profiles[record[0]]['rows'].append(dict(zip(FIELDS, record[1:])))
    return build_pdf(list(profiles.values()))


def message(text, code):
    return PlainTextResponse(text, status_code=code, headers=HEADERS)


async def download(request):
    scheme = request.url.scheme
    if os.environ.get('DYNO'):
        scheme = request.headers.get('x-forwarded-proto', scheme)
    if scheme != 'https':
        return message('Please open this page using HTTPS.', 403)
    now = datetime.now(timezone.utc)
    if now >= END or not os.environ.get('WAVE1_SELFIE_ACCESS'):
        return message('Downloads are closed.', 404)
    if request.method in ('GET', 'HEAD'):
        return HTMLResponse(FORM, headers=HEADERS)
    if request.headers.get('content-type', '').split(';')[0] != 'application/x-www-form-urlencoded':
        return message('Please use the download form.', 400)
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 1024:
            return message('Form too large.', 413)
        body.extend(chunk)
    fields = parse_qs(body.decode('utf-8', errors='replace'))
    name = fields.get('username', [''])[0]
    password = fields.get('password', [''])[0]
    config = json.loads(os.environ['WAVE1_SELFIE_ACCESS'])
    # Passwords are 256-bit random values. Only their digests are configured.
    expected = config['accounts'].get(name, '')
    if not hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), expected):
        return message('Incorrect username or password. Go back and try again.', 401)
    data = await run_in_threadpool(participant_report, set(config['photos']), now)
    if data is None:
        return message('No eligible selfies are available.', 404)
    return Response(data, media_type='application/pdf', headers={
        **HEADERS, 'Content-Disposition': 'attachment; filename="wave-1-participant-report.pdf"'})


researcher_routes = [Route(PATH, download, methods=['GET', 'POST'])]
