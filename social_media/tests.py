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
    round_spec, get_condition,
    is_feedback_round, is_third_period, third_period_played,
    is_end_of_period, is_end_of_period_with_p3,
    BotCheck, Consent, Intro, TaskIntro, QuestionPage, IQReadout,
    PerceivedPercentile, PerceivedPercentileConfidence, ColorTaskIntro,
    ColorTask1, ColorTask2, ColorTask3, ColorTask4, ColorTask5, ColorTask6,
    EndOfPeriodSurvey, WTACompare, Results,
    BigFiveSurvey, SelfEsteemSurvey, NarcissismSurvey, Demographics,
    SocialMediaUsage, RealismQuestion, SurveyReliabilityOverall,
    FinalResults, ProlificCompletion,
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
            yield Submission(Intro, dict(), check_html=False)

        plays_question = (not is_third_period(p)) or third_period_played(p)

        if p.round_number in (1, C.PERIOD_LENGTH + 1, C.THIRD_PERIOD_START) and plays_question:
            yield Submission(TaskIntro, dict(), check_html=False)
        if plays_question:
            fields = dict(q_answer=_correct_answer(p), q_response_time=2.0)
            if is_feedback_round(p):
                cond = get_condition(p)
                if cond == 'quantitative_social':
                    fields.update(report_display_name='Bot', report_number=5, report_shared=True)
                elif cond == 'qualitative_social':
                    fields.update(report_display_name='Bot', report_emoji=QUAL_EMOJIS[0],
                                  report_message='Felt good about that one.', report_shared=True)
            yield Submission(QuestionPage, fields, check_html=False)

        if CFG['show_iq'] and is_end_of_period_with_p3(p):
            yield Submission(IQReadout, dict(), check_html=False)

        if is_end_of_period_with_p3(p):
            yield Submission(PerceivedPercentile, dict(perceived_relative_performance=50), check_html=False)
            yield Submission(PerceivedPercentileConfidence, dict(perceived_percentile_confidence=50), check_html=False)

        if is_end_of_period(p):
            yield Submission(ColorTaskIntro, dict(), check_html=False)
            yield Submission(ColorTask1, dict(stroop_1='Blue', stroop_1_response_time=1.0), check_html=False)
            yield Submission(ColorTask2, dict(stroop_2='Red', stroop_2_response_time=1.0), check_html=False)
            yield Submission(ColorTask3, dict(stroop_3='Green', stroop_3_response_time=1.0), check_html=False)
            yield Submission(ColorTask4, dict(stroop_4='Yellow', stroop_4_response_time=1.0), check_html=False)
            yield Submission(ColorTask5, dict(stroop_5='Green', stroop_5_response_time=1.0), check_html=False)
            yield Submission(ColorTask6, dict(stroop_6='Blue', stroop_6_response_time=1.0), check_html=False)

        if is_end_of_period_with_p3(p):
            yield Submission(EndOfPeriodSurvey, dict(mood=3, task_enjoyment=3, payment_satisfaction=3), check_html=False)

        if CFG['use_wta'] and self.round_number == 2 * C.PERIOD_LENGTH:
            wta = {}
            for i in range(1, len(WTA_AMOUNTS) + 1):
                wta[f'wta_t_{i}'] = 'Yes'
                wta[f'wta_c_{i}'] = 'Yes'
            yield Submission(WTACompare, wta, check_html=False)
            yield Submission(Results, dict(), check_html=False)

        if self.round_number == C.NUM_ROUNDS:
            bfi = {f'big5_{i}': 3 for i in range(1, 11)}
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
            yield Submission(FinalResults, dict(), check_html=False)
            yield Submission(ProlificCompletion, dict(), check_html=False)
