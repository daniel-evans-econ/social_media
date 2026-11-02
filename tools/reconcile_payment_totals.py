"""Repair the old round-30/45 duplicate credit, without changing awards.

Run without arguments to produce a backup/audit JSON. Only --apply writes.
This does not send payments or recalculate any historical accuracy bonuses.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from otree.database import init_orm, db
init_orm()
import social_media as survey


def reconcile(apply=False):
    records, skipped = [], []
    for final in survey.Player.objects_filter(round_number=survey.C.NUM_ROUNDS):
        participant = final.participant
        if participant.vars.get('payment_accounting_version', 1) >= 2:
            continue
        interim = final.in_round(2 * survey.C.PERIOD_LENGTH)
        if not final.payoff or not interim.payoff:
            continue
        if final.payoff < interim.payoff:
            skipped.append(participant.code)
            continue
        record = dict(participant=participant.code, session=final.session.code,
                      interim=float(interim.payoff), final_before=float(final.payoff),
                      aggregate_before=float(participant.payoff),
                      final_after=float(final.payoff-interim.payoff),
                      aggregate_after=float(participant.payoff-interim.payoff))
        records.append(record)
        if apply:
            participant.vars['legacy_payment_reconciliation'] = record
            final.payoff = final.payoff - interim.payoff
            participant.vars['payment_accounting_version'] = 2
    if apply:
        db.commit()
    return dict(applied=apply, count=len(records), records=records, skipped=skipped)


if __name__ == '__main__':
    print(json.dumps(reconcile('--apply' in sys.argv)))
