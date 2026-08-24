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
    C, CFG, QD, WTA_AMOUNTS, QUAL_EMOJIS, BFI_CORE_FIELDS,
    round_spec, get_condition, experienced_conditions,
    is_feedback_round, is_third_period, third_period_played,
    is_end_of_period_with_p3,
    BotCheck, Consent, ProlificID, IQReferencePoint, Intro, TaskIntro, QuestionPage, BlockFeedback, IQFeedback,
    EndOfPeriodSurvey, TaskEffort, WTACompare, Results, GlobalIQFeedback,
    PerceivedPercentile, PerceivedPercentileConfidence,
    BigFiveSurvey, SelfEsteemSurvey, NarcissismSurvey, Demographics,
    PlatformUsage, RealismQuestion,
    ExperienceChecklist1, ExperienceChecklist2, ExperienceChecklist3,
    experience_page_order, ToolsUsed,
    SurveyReliabilityOverall, Comments, FinalResults,
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
            yield Submission(ProlificID, dict(prolific_id='abcdefghijklmnopqrstuvwx'), check_html=False)
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
            yield Submission(EndOfPeriodSurvey, dict(
                mood=3, performance_satisfaction=3, task_enjoyment=3, payment_satisfaction=3,
            ), check_html=False)

        if CFG['use_wta'] and self.round_number == 2 * C.PERIOD_LENGTH:
            if CFG['show_iq']:
                treatment, _ = experienced_conditions(p)
                gifb = {}
                if treatment == 'quantitative_social':
                    gifb.update(global_report_iq=100, global_report_shared=True)
                elif treatment == 'qualitative_social':
                    gifb.update(
                        global_report_emoji=QUAL_EMOJIS[0],
                        global_report_message='Felt good overall.',
                        global_report_shared=True,
                    )
                yield Submission(GlobalIQFeedback, gifb, check_html=False)
            wta = {}
            for i in range(1, len(WTA_AMOUNTS) + 1):
                wta[f'wta_t_{i}'] = 'Yes'
                wta[f'wta_c_{i}'] = 'Yes'
            yield Submission(WTACompare, wta, check_html=False)
            yield Submission(Results, dict(), check_html=False)

        if self.round_number == C.NUM_ROUNDS:
            bfi = {f: 3 for f in BFI_CORE_FIELDS}
            bfi['big5_accuracy'] = 3
            yield Submission(BigFiveSurvey, bfi, check_html=False)
            yield Submission(SelfEsteemSurvey, {f'rses_{i}': 2 for i in range(1, 11)}, check_html=False)
            yield Submission(NarcissismSurvey, {f'npi_{i}': 1 for i in range(1, 9)}, check_html=False)
            yield Submission(Demographics, dict(
                age=30, gender='woman', education='bachelor', taken_iq_test_before='Yes',
            ), check_html=False)
            yield Submission(TaskEffort, dict(task_effort=75), check_html=False)
            yield Submission(PlatformUsage, dict(sm_instagram=True, social_media_hours=2.0), check_html=False)
            yield Submission(RealismQuestion, dict(
                realism_feedback='The social feedback felt fairly realistic to me overall, thanks.'
            ), check_html=False)
            _exp_write = dict(
                write_well_show=True,
                write_well_downplay=False,
                write_poor_honest=True,
                write_poor_exaggerate=False,
                write_peer_well_up=True,
                write_peer_well_down=False,
                write_peer_poor_up=False,
                write_peer_poor_down=True,
                write_match_tone=False,
            )
            _exp_share = dict(
                share_well_positive=True,
                share_well_withhold=False,
                share_poor_positive=False,
                share_poor_withhold=True,
                share_peer_well_up=True,
                share_peer_well_down=False,
                share_peer_poor_up=False,
                share_peer_poor_down=True,
                share_helpful=True,
            )
            _exp_impact = dict(
                impact_recv_mood=True,
                impact_recv_sat=False,
                impact_recv_effort=True,
                impact_send_mood=False,
                impact_send_sat=True,
                impact_send_effort=False,
            )
            _exp_by_key = dict(writing=_exp_write, sharing=_exp_share, impacts=_exp_impact)
            for slot, page_cls in enumerate((
                ExperienceChecklist1, ExperienceChecklist2, ExperienceChecklist3,
            )):
                page_key = experience_page_order(p.participant)[slot]
                yield Submission(page_cls, _exp_by_key[page_key], check_html=False)
            yield Submission(ToolsUsed, dict(
                tool_pen_paper=True,
                tool_calculator=False,
                tool_ai=False,
                tool_cellphone_camera=False,
                tool_search_engine=False,
                tool_ask_someone_else=False,
                tool_none=False,
            ), check_html=False)
            yield Submission(SurveyReliabilityOverall, dict(survey_reliability=7), check_html=False)
            yield Submission(Comments, dict(comments='Great study, no issues.'), check_html=False)
            yield Submission(FinalResults, dict(), check_html=False)
