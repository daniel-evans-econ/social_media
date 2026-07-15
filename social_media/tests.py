"""Bot that plays through the whole experiment, used to smoke-test all pages.

Run for each pilot by setting EXPERIMENT_PILOT before invoking, e.g.:

    EXPERIMENT_PILOT=initial otree test social_media
    EXPERIMENT_PILOT=iq      otree test social_media
    EXPERIMENT_PILOT=main    otree test social_media

The bot answers every cognitive question correctly (so grading, scoring and the
IQ readout are exercised) and fills in all surveys.
"""
from otree.api import Bot, Submission

from . import (
    C, CFG, QD, WTA_AMOUNTS, QUAL_EMOJIS,
    round_spec, get_condition, stroop_question,
    is_feedback_round, is_third_period, third_period_played,
    is_end_of_period, is_end_of_period_with_p3,
    BotCheck, Consent, IQReferencePoint, Intro, TaskIntro, QuestionPage, BlockFeedback, IQFeedback,
    PerceivedPercentile, PerceivedPercentileConfidence, ColorTaskIntro,
    ColorTask1, ColorTask2, ColorTask3, ColorTask4, ColorTask5, ColorTask6,
    EndOfPeriodSurvey, WTACompare, Results,
    BigFiveSurvey, SelfEsteemSurvey, NarcissismSurvey, Demographics,
    SocialMediaUsage, RealismQuestion, SurveyReliabilityOverall,
    Comments, FinalResults,
)


def _correct_answer(player):
    spec = round_spec(player)
    item = QD.QUESTIONS[spec['task']][spec['item_id']]
    if QD.TASK_RESPONSE[spec['task']] == 'count':
        return str(item['dot_count'])
    return str(item['correct'])


class PlayerBot(Bot):
    def play_round(self):
        p = self.player

        if self.round_number == 1:
            yield Submission(BotCheck, dict(
                turnstile_token='', turnstile_bypass_key='',
                turnstile_client_host='localhost', honeypot_intro_response='',
            ), check_html=False)
            yield Submission(Consent, dict(consent=True, llm_rule_confirm=True), check_html=False)
            if p.participant.vars.get('iq_reference_asked', False):
                yield Submission(IQReferencePoint, dict(iq_reference_score=100), check_html=False)
            else:
                yield Submission(IQReferencePoint, dict(), check_html=False)
            yield Submission(Intro, dict(display_name='Bot'), check_html=False)

        plays_question = (not is_third_period(p)) or third_period_played(p)

        if p.round_number in (1, C.PERIOD_LENGTH + 1, C.THIRD_PERIOD_START) and plays_question:
            p.participant.vars['task_intro_checked'] = True
            yield Submission(TaskIntro, dict(), check_html=False)
        if plays_question:
            # Exercise the timed-out feedback-round path on the first feedback
            # round: leave the 5th question unanswered and let the 60s timer
            # expire. BlockFeedback must still show afterwards (it is gated only
            # on is_feedback_round, not on the answer being present).
            if is_feedback_round(p) and p.round_number == 5:
                yield Submission(QuestionPage, dict(), check_html=False, timeout_happened=True)
            else:
                yield Submission(
                    QuestionPage,
                    dict(q_answer=_correct_answer(p), q_response_time=2.0),
                    check_html=False,
                )
            if is_feedback_round(p):
                # BlockFeedback (number-correct sidebar) shows at all feedback
                # rounds in the initial pilot, but only at MID-PERIOD feedback
                # rounds in show_iq pilots (15/30/45 are handled by IQFeedback).
                block_fb_shown = (
                    not CFG['show_iq']
                    or (p.round_number not in C.END_OF_PERIOD_ROUNDS
                        and p.round_number != C.NUM_ROUNDS)
                )
                if block_fb_shown:
                    cond = get_condition(p)
                    fb = {}
                    if cond == 'quantitative_social':
                        fb.update(report_number=5, report_shared=True)
                    elif cond == 'qualitative_social':
                        fb.update(report_emoji=QUAL_EMOJIS[0],
                                  report_message='Felt good about that one.', report_shared=True)
                    yield Submission(BlockFeedback, fb, check_html=False)

        if CFG['show_iq'] and is_end_of_period_with_p3(p):
            cond = get_condition(p)
            iqfb = {}
            if cond == 'quantitative_social':
                iqfb.update(report_iq=100, report_shared=True)
            elif cond == 'qualitative_social':
                iqfb.update(report_emoji=QUAL_EMOJIS[0],
                            report_message='Felt good about that one.', report_shared=True)
            yield Submission(IQFeedback, iqfb, check_html=False)

        if is_end_of_period_with_p3(p):
            yield Submission(PerceivedPercentile, dict(perceived_relative_performance=50), check_html=False)
            yield Submission(PerceivedPercentileConfidence, dict(perceived_percentile_confidence=50), check_html=False)

        if is_end_of_period_with_p3(p):
            yield Submission(EndOfPeriodSurvey, dict(mood=3, task_enjoyment=3, payment_satisfaction=3), check_html=False)

        if is_end_of_period_with_p3(p):
            yield Submission(ColorTaskIntro, dict(), check_html=False)
            color_pages = [ColorTask1, ColorTask2, ColorTask3, ColorTask4, ColorTask5, ColorTask6]
            for n, page in enumerate(color_pages, start=1):
                ink = stroop_question(p, n)['color']
                yield Submission(
                    page,
                    {f'stroop_{n}': ink, f'stroop_{n}_response_time': 1.0},
                    check_html=False,
                )

        if CFG['use_wta'] and self.round_number == 2 * C.PERIOD_LENGTH:
            wta = {}
            for i in range(1, len(WTA_AMOUNTS) + 1):
                wta[f'wta_t_{i}'] = 'Yes'
                wta[f'wta_c_{i}'] = 'Yes'
            yield Submission(WTACompare, wta, check_html=False)
            yield Submission(Results, dict(), check_html=False)

        if self.round_number == C.NUM_ROUNDS:
            bfi = {f'big5_{i}': 3 for i in range(1, 11)}
            bfi['self_knowledge'] = 3
            bfi['big5_accuracy'] = 3
            bfi['competitiveness'] = 3
            yield Submission(BigFiveSurvey, bfi, check_html=False)
            yield Submission(SelfEsteemSurvey, {f'rses_{i}': 2 for i in range(1, 11)}, check_html=False)
            yield Submission(NarcissismSurvey, {f'npi_{i}': 1 for i in range(1, 9)}, check_html=False)
            yield Submission(Demographics, dict(age=30, gender='woman', education='bachelor'), check_html=False)
            yield Submission(SocialMediaUsage, dict(sm_instagram=True, social_media_hours=2.0), check_html=False)
            yield Submission(RealismQuestion, dict(
                realism_feedback='The social feedback felt fairly realistic to me overall, thanks.'
            ), check_html=False)
            yield Submission(SurveyReliabilityOverall, dict(survey_reliability=7), check_html=False)
            yield Submission(Comments, dict(comments='Great study, no issues.'), check_html=False)
            yield Submission(FinalResults, dict(), check_html=False)
