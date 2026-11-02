"""Accuracy awards from the completed tasks and the assigned reference groups."""
import random


def accuracy_bonuses(player):
    from . import (C, CFG, TASK_IQ_COMPONENT, estimate_iq_for_player,
                   group_for, iq_reference_scores, IQ_COMPARISON_GROUP,
                   third_period_played)

    rounds = list(player.in_rounds(1, C.NUM_ROUNDS))
    by_round = {p.round_number: p for p in rounds}
    tasks = player.participant.vars.get('period_tasks', [])
    periods = 3 if third_period_played(player) else 2
    rows, pending, iq_results = [], [], []
    audit = {}

    for period in range(1, periods + 1):
        end = period * C.PERIOD_LENGTH
        last = by_round.get(end)
        task = tasks[period - 1] if period <= len(tasks) else None
        component = TASK_IQ_COMPONENT.get(task)
        if last is None or component is None:
            continue
        score = sum(bool(p.field_maybe_none('q_correct')) for p in rounds
                    if end - C.PERIOD_LENGTH < p.round_number <= end)
        iq = last.field_maybe_none('iq_estimate')
        if iq is None:
            iq = estimate_iq_for_player(last, component, score, C.PERIOD_LENGTH)
        iq_results.append(iq)
        guess = last.field_maybe_none('perceived_relative_performance')
        if guess is None:
            count = last.field_maybe_none('perceived_outperformed_count')
            if count is not None:
                guess = 100 * count / IQ_COMPARISON_GROUP
        label = f'Period {period} percentile estimate'
        group = group_for(last)
        sample = group['scores'] if group else []
        if not sample:
            # Reproduce the legacy IQ-feedback draw; never draw another group.
            full = (iq_reference_scores() or {}).get(component, [])
            if len(full) >= IQ_COMPARISON_GROUP:
                sample = random.Random(f'{player.participant.code}-iqnoise-{component}').sample(full, IQ_COMPARISON_GROUP)
        if guess is None or not sample:
            pending.append(dict(label=label, maximum=float(C.PAY_PER_PERCENTILE)))
            continue
        # Match the IQ calculation's mid-rank convention, without clipping the
        # endpoints (clipping is only needed for the inverse-normal transform).
        actual = 100 * (sum(v < score for v in sample) + .5 * sum(v == score for v in sample)) / len(sample)
        amount = float(C.PAY_PER_PERCENTILE) if abs(guess - actual) <= 10 + 1e-9 else 0
        rows.append(dict(label=label, amount=f'{amount:.2f}'))
        audit[f'percentile_{period}'] = dict(guess=guess, actual=actual, score=score,
                                            tolerance=10, amount=amount, ties='half_weight')

    if player.participant.vars.get('iq_reference_asked'):
        first = by_round.get(1)
        guess = first.field_maybe_none('iq_reference_score') if first else None
        # The initial instructions specify two components when period 3 is
        # optional; its acceptance must not change the initial prediction target.
        count = 2 if CFG['use_wta'] else 3
        combined = by_round.get(2 * C.PERIOD_LENGTH)
        actual = combined.field_maybe_none('global_iq_estimate') if combined and CFG['use_wta'] else None
        if actual is None and len(iq_results) >= count:
            actual = int(sum(iq_results[:count]) / count + .5)
        if guess is None or actual is None:
            pending.insert(0, dict(label='Initial IQ estimate', maximum=float(C.PAY_IQ_REFERENCE_GUESS)))
        else:
            amount = float(C.PAY_IQ_REFERENCE_GUESS) if abs(guess - actual) <= 10 else 0
            rows.insert(0, dict(label='Initial IQ estimate', amount=f'{amount:.2f}'))
            audit['initial_iq'] = dict(guess=guess, actual=actual, components=count, tolerance=10, amount=amount)
    player.participant.vars['accuracy_bonus_results'] = dict(version=1, awards=audit, pending=pending)
    return rows, pending
