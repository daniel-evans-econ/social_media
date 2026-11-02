"""Initial-IQ awards; percentile awards await data on the current question set."""


def accuracy_bonuses(player):
    from . import (C, CFG, TASK_IQ_COMPONENT, estimate_iq,
                   IQ_COMPARISON_GROUP,
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
        # Accuracy of the initial guess is assessed against the calibrated
        # full-sample estimate, never the randomized comparison-group feedback.
        iq = estimate_iq(component, score, C.PERIOD_LENGTH)
        iq_results.append(iq)
        guess = last.field_maybe_none('perceived_relative_performance')
        if guess is None:
            count = last.field_maybe_none('perceived_outperformed_count')
            if count is not None:
                guess = 100 * count / IQ_COMPARISON_GROUP
        label = f'Period {period} percentile estimate'
        # Historical pilot respondents answered different question sets. Their
        # scores must not determine this same-questions accuracy bonus. Keep
        # the response and eligibility for settlement after current data arrive.
        pending.append(dict(label=label, maximum=float(C.PAY_PER_PERCENTILE),
                            period=period, guess=guess, score=score, tolerance=10,
                            reason='awaiting_current_question_set_data'))

    if player.participant.vars.get('iq_reference_asked'):
        first = by_round.get(1)
        guess = first.field_maybe_none('iq_reference_score') if first else None
        # The initial instructions specify two components when period 3 is
        # optional; its acceptance must not change the initial prediction target.
        count = 2 if CFG['use_wta'] else 3
        actual = int(sum(iq_results[:count]) / count + .5) if len(iq_results) >= count else None
        if guess is None or actual is None:
            pending.insert(0, dict(label='Initial IQ estimate', maximum=float(C.PAY_IQ_REFERENCE_GUESS)))
        else:
            amount = float(C.PAY_IQ_REFERENCE_GUESS) if abs(guess - actual) <= 10 else 0
            rows.insert(0, dict(label='Initial IQ estimate', amount=f'{amount:.2f}'))
            audit['initial_iq'] = dict(guess=guess, actual=actual, components=count,
                                      source='full_sample', tolerance=10, amount=amount)
    player.participant.vars['accuracy_bonus_results'] = dict(version=3, awards=audit, pending=pending)
    return rows, pending
