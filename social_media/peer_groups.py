"""Persistent task-specific reference draws shared by feedback and messages."""
import hashlib
import json
import random
import os
from functools import lru_cache
from pathlib import Path


@lru_cache()
def reference(source):
    path = Path(__file__).parent / 'data' / f'peer_reference_{source}.fernet'
    if not path.exists():
        return {}
    from cryptography.fernet import Fernet
    key = os.environ.get('PEER_REFERENCE_KEY')
    if not key:
        raise RuntimeError('PEER_REFERENCE_KEY is required for the linked reference pool.')
    return json.loads(Fernet(key.encode()).decrypt(path.read_bytes()).decode('utf-8'))


def group_for(player, period=None):
    from . import CFG
    if not player.participant.vars.get('linked_peer_groups'):
        return None
    period = period or (player.round_number - 1) // 15 + 1
    snapshots = dict(player.participant.vars.get('peer_groups', {}))
    key = str(period)
    if key in snapshots:
        return snapshots[key]
    task = player.participant.vars['period_tasks'][period - 1]
    rows = reference(CFG['iq_distribution_source']).get(task, [])
    if len(rows) < 5:
        raise ValueError(f'No complete linked reference pool for {task}')
    # Stable random tie-breaks keep equal-score respondents from systematically
    # sorting by participant ID. Quintile boundaries are fixed for each domain.
    rows = sorted(rows, key=lambda r: (r['score'], hashlib.sha256((task+r['id']).encode()).hexdigest()))
    rng = random.Random(f'{player.participant.code}-peer-group-{period}-{task}')
    quintile = rng.randrange(5)
    eligible = rows[len(rows)*quintile//5:len(rows)*(quintile+1)//5]
    # TEMPORARY: replacement accommodates small pilot quintiles. Switch to
    # sample(..., 20) when every domain/quintile contains enough respondents.
    draws = rng.choices(eligible, k=20)
    snapshot = dict(task=task, quintile=quintile+1, replacement=True,
                    reference_source=CFG['iq_distribution_source'],
                    draw_ids=[r['id'] for r in draws], scores=[r['score'] for r in draws])
    snapshots[key] = snapshot
    player.participant.vars['peer_groups'] = snapshots
    return snapshot


def records_for(player, period):
    group = group_for(player, period)
    if not group:
        return []
    index = {r['id']: r for r in reference(group['reference_source'])[group['task']]}
    return [index[key] for key in group['draw_ids']]


def message_for(player, kind):
    """Sample messages only from drawn members; no repeated sender/content pair.

    Duplicate draws increase norming weights, not the number of times a message
    can appear. Exhaustion produces no incoming message, never a fabricated peer.
    """
    plans = dict(player.participant.vars.get('linked_message_plan', {}))
    key = str(player.round_number)
    if key in plans:
        return plans[key]
    # Only reserve messages actually encountered, not messages for control or
    # unplayed periods. Preserve the earlier no-repeat-sender rule as well.
    period = (player.round_number - 1)//15 + 1
    used = {m['fingerprint'] for m in plans.values() if m}
    used_names = {m['name'].strip().casefold() for m in plans.values() if m}
    records = records_for(player, period)
    candidates = {m['id']: m for r in records for m in r['messages'] if m['kind'] == kind}
    candidates = list(candidates.values())
    random.Random(f'{player.participant.code}-messages-{period}-{kind}').shuffle(candidates)
    chosen = None
    for message in candidates:
        fingerprint = json.dumps([message['name'].casefold(), message.get('number'),
                                  message.get('sentence', '').strip()], ensure_ascii=False)
        if fingerprint not in used and message['name'].strip().casefold() not in used_names:
            chosen = dict(message, fingerprint=fingerprint)
            break
    plans[key] = chosen
    player.participant.vars['linked_message_plan'] = plans
    return chosen


def averages(player, period):
    """Block-weighted reports on a /15 scale, transparently labelled as such.

    Control and qualitative records have no numerical reports. Missing/unsent
    reports are never coded as zero. Repeated reference draws retain their weight.
    """
    records = records_for(player, period)
    if player.participant.vars['social_type'] == 'qualitative_social':
        # Initial pilot used happy/neutral/unhappy emojis; this definition is
        # specific to that source and is preserved in the exported snapshot.
        composed = [b for r in records for b in r['blocks'] if b.get('emoji')]
        sent = [b for b in composed if b['sent']]
        happy = {'😃'}
        rate = lambda bs: 100*sum(b['emoji'] in happy for b in bs)/len(bs) if bs else None
        return dict(period=period, actual=rate(composed), reported=rate(sent),
                    kind='happy', n_draws=len(records), composed=len(composed), sent_blocks=len(sent),
                    happy_definition=sorted(happy))
    all_numeric = [b for r in records for b in r['blocks'] if b['report'] is not None]
    sent = [b for b in all_numeric if b['sent']]
    actual = sum(r['score'] for r in records) / len(records)
    result = dict(period=period, actual=actual, reported=None, kind='score', sent_blocks=len(sent),
                  numeric_blocks=len(all_numeric), n_draws=len(records))
    if sent:
        reported = 3*sum(b['report'] for b in sent)/len(sent)
        actual_sent = 3*sum(b['score'] for b in sent)/len(sent)
        actual_numeric = 3*sum(b['score'] for b in all_numeric)/len(all_numeric)
        result.update(reported=reported, selection=actual_sent-actual_numeric,
                      misreporting=reported-actual_sent,
                      reporting_subset=actual_numeric-actual)
    return result
