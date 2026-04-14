from otree.api import *
import json
import random


doc = """
Social media and well-being experiment.
Subjects complete Raven's Progressive Matrices across two periods of 10 questions each.
Each subject experiences the control condition in one period and one of two social feedback
treatments in the other (mixed-subject design, order randomized).
"""

RAVEN_CORRECT = "A"

AB_PAY_PER_50 = cu(0.05)
STROOP_ANSWERS = ["Blue", "Red", "Green", "Yellow", "Green", "Blue"]
# Tasks 2 and 5 are congruent (word matches display color)

BFI_CHOICES = [
    [0, ""],
    [1, ""],
    [2, ""],
    [3, ""],
    [4, ""],
]

RSES_CHOICES = [
    [0, ""],
    [1, ""],
    [2, ""],
    [3, ""],
]

LIKERT_CHOICES = [
    [1, "Not at all"],
    [2, "A little"],
    [3, "Moderately"],
    [4, "Quite a lot"],
    [5, "Very much"],
]

WTA_AMOUNTS = [0.01, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]


class C(BaseConstants):
    NAME_IN_URL = 'social_media'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 30

    PERIOD_LENGTH = 10
    FEEDBACK_ROUNDS = [5, 10, 15, 20, 25, 30]
    END_OF_PERIOD_ROUNDS = [10, 20]
    THIRD_PERIOD_START = 21

    PAY_PER_CORRECT = cu(0.25)
    PAY_PER_STROOP = cu(0.10)


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # ---- Consent ----
    consent = models.BooleanField(label="")
    llm_rule_confirm = models.BooleanField(label="")

    condition = models.StringField(blank=True)

    raven_answer = models.StringField(
        choices=["A", "B", "C", "D", "E", "F"],
        blank=True,
        label="Select the figure that completes the pattern:",
        widget=widgets.RadioSelectHorizontal,
    )
    feedback_snapshot = models.LongStringField(blank=True)

    # ---- Personality survey (BFI-10) ----
    # Labels are blank because the table template provides statement text and column headers.
    big5_1 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    big5_2 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    big5_3 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    big5_4 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    big5_5 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    big5_6 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    big5_7 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    big5_8 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    big5_9 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    big5_10 = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")

    # ---- NPI-8: Narcissistic Personality Inventory (Schmalbach et al., 2020) ----
    # Forced-choice pairs; 1 = narcissistic option, 0 = non-narcissistic option.
    # Leadership/Authority subscale
    npi_1 = models.IntegerField(choices=[
        [1, "I really like to be the center of attention."],
        [0, "It makes me uncomfortable to be the center of attention."],
    ], widget=widgets.RadioSelect, blank=True, label="")
    npi_2 = models.IntegerField(choices=[
        [0, "I am not sure if I would make a good leader."],
        [1, "I see myself as a good leader."],
    ], widget=widgets.RadioSelect, blank=True, label="")
    npi_3 = models.IntegerField(choices=[
        [1, "I like to have authority over other people."],
        [0, "I don't mind following orders."],
    ], widget=widgets.RadioSelect, blank=True, label="")
    npi_4 = models.IntegerField(choices=[
        [1, "I have a natural talent for influencing people."],
        [0, "I am not good at influencing people."],
    ], widget=widgets.RadioSelect, blank=True, label="")
    # Grandiose Exhibitionism subscale
    npi_5 = models.IntegerField(choices=[
        [1, "I like to show off my body."],
        [0, "I don't particularly like to show off my body."],
    ], widget=widgets.RadioSelect, blank=True, label="")
    npi_6 = models.IntegerField(choices=[
        [0, "I try not to be a show off."],
        [1, "I will usually show off if I get the chance."],
    ], widget=widgets.RadioSelect, blank=True, label="")
    npi_7 = models.IntegerField(choices=[
        [1, "I like to look at myself in the mirror."],
        [0, "I am not particularly interested in looking at myself in the mirror."],
    ], widget=widgets.RadioSelect, blank=True, label="")
    npi_8 = models.IntegerField(choices=[
        [1, "I am a born leader."],
        [0, "Leadership is a quality that takes a long time to develop."],
    ], widget=widgets.RadioSelect, blank=True, label="")
    competitiveness = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")

    # ---- Rosenberg Self-Esteem Scale (RSES, 10 items, 4-point) ----
    rses_1 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    rses_2 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    rses_3 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    rses_4 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    rses_5 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    rses_6 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    rses_7 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    rses_8 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    rses_9 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    rses_10 = models.IntegerField(choices=RSES_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")

    # ---- End-of-period measures ----
    perceived_relative_performance = models.IntegerField(
        label="",
        min=0, max=100, blank=True,
    )

    ab_count = models.IntegerField(label="", min=0, initial=0, blank=True)

    stroop_1 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
    )
    stroop_2 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
    )
    stroop_3 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
    )
    stroop_4 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
    )
    stroop_5 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
    )
    stroop_6 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
    )

    task_enjoyment = models.IntegerField(
        choices=LIKERT_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True,
        label="",
    )
    payment_satisfaction = models.IntegerField(
        choices=LIKERT_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True,
        label="",
    )

    # ---- WTA multiple price list ----
    wta_1 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_2 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_3 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_4 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_5 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_6 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_7 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_8 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_9 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_10 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_11 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")

    # ---- End-of-experiment only ----
    social_media_hours = models.FloatField(
        label="On average, how many hours per day do you spend on social media?",
        min=0, max=24, blank=True,
    )
    sm_instagram = models.BooleanField(blank=True, initial=False)
    sm_tiktok = models.BooleanField(blank=True, initial=False)
    sm_twitter = models.BooleanField(blank=True, initial=False)
    sm_facebook = models.BooleanField(blank=True, initial=False)
    sm_snapchat = models.BooleanField(blank=True, initial=False)
    sm_youtube = models.BooleanField(blank=True, initial=False)
    sm_reddit = models.BooleanField(blank=True, initial=False)
    sm_linkedin = models.BooleanField(blank=True, initial=False)
    sm_other = models.BooleanField(blank=True, initial=False)
    sm_none = models.BooleanField(blank=True, initial=False)
    sm_other_text = models.StringField(
        label="",
        blank=True,
    )
    realism_feedback = models.LongStringField(
        label="",
        blank=True,
    )


# ---------------------------------------------------------------------------
# Session setup
# ---------------------------------------------------------------------------

def creating_session(subsession: Subsession):
    if subsession.round_number == 1:
        players = subsession.get_players()
        # Mixed-subject design: each subject gets control in one period and
        # one of {quantitative_social, qualitative_social} in the other.
        # Four balanced cells ensure equal treatment-order combinations.
        cells = [
            ('control', 'quantitative_social'),
            ('quantitative_social', 'control'),
            ('control', 'qualitative_social'),
            ('qualitative_social', 'control'),
        ]
        assignments = [cells[i % len(cells)] for i in range(len(players))]
        random.shuffle(assignments)

        for p, (p1_cond, p2_cond) in zip(players, assignments):
            p.participant.period_1_condition = p1_cond
            p.participant.period_2_condition = p2_cond

    for p in subsession.get_players():
        if p.round_number <= C.PERIOD_LENGTH:
            p.condition = p.participant.period_1_condition
        elif p.round_number <= 2 * C.PERIOD_LENGTH:
            p.condition = p.participant.period_2_condition
        else:
            p.condition = 'control'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_condition(player: Player):
    if player.round_number <= C.PERIOD_LENGTH:
        return player.participant.period_1_condition
    elif player.round_number <= 2 * C.PERIOD_LENGTH:
        return player.participant.period_2_condition
    return player.participant.vars.get('third_period_condition', 'control')


def is_feedback_round(player: Player):
    return player.round_number in C.FEEDBACK_ROUNDS


def is_end_of_period(player: Player):
    return player.round_number in C.END_OF_PERIOD_ROUNDS


def is_third_period(player: Player):
    return player.round_number >= C.THIRD_PERIOD_START


def third_period_accepted(player: Player):
    return player.participant.vars.get('third_period_accepted', False)


def block_correct(player: Player):
    """Number of correct answers in the current 5-question block."""
    r = player.round_number
    block_start = ((r - 1) // 5) * 5 + 1
    total = 0
    for p in player.in_rounds(block_start, r):
        if (p.field_maybe_none('raven_answer') or '') == RAVEN_CORRECT:
            total += 1
    return total


def total_correct(player: Player):
    """Total correct answers from round 1 through current round."""
    total = 0
    for p in player.in_rounds(1, player.round_number):
        if (p.field_maybe_none('raven_answer') or '') == RAVEN_CORRECT:
            total += 1
    return total


def period_correct(player: Player):
    """Total correct in the current period."""
    r = player.round_number
    if r <= C.PERIOD_LENGTH:
        start = 1
    elif r <= 2 * C.PERIOD_LENGTH:
        start = C.PERIOD_LENGTH + 1
    else:
        start = C.THIRD_PERIOD_START
    total = 0
    for p in player.in_rounds(start, r):
        if (p.field_maybe_none('raven_answer') or '') == RAVEN_CORRECT:
            total += 1
    return total


def pilot_feedback_signals(player: Player):
    """
    Simulate feedback from pilot experiment participants.
    Quantitative: 3 randomly drawn scores (0-5).
    Qualitative: 3 randomly drawn emojis.
    """
    cond = get_condition(player)
    r = player.round_number
    seed = f"{player.session.code}-{player.participant.code}-{r}"
    rng = random.Random(seed)

    if cond == 'quantitative_social':
        scores = [rng.randint(0, 5) for _ in range(3)]
        return dict(type='quantitative', scores=scores)

    if cond == 'qualitative_social':
        emojis = [rng.choice(["\U0001f603", "\U0001f610", "\U0001f61e"]) for _ in range(3)]
        return dict(type='qualitative', emojis=emojis)

    return dict(type='control')


def effort_ab_count(player: Player):
    return player.field_maybe_none('ab_count') or 0


def stroop_correct_count(player: Player):
    answers = [player.stroop_1, player.stroop_2, player.stroop_3,
               player.stroop_4, player.stroop_5, player.stroop_6]
    return sum(1 for i, a in enumerate(answers) if a == STROOP_ANSWERS[i])


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

class Consent(Page):
    form_model = 'player'
    form_fields = ['consent', 'llm_rule_confirm']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def error_message(player: Player, values):
        if not values.get('consent') or not values.get('llm_rule_confirm'):
            return "You must agree to all conditions and consent to continue."


class BigFiveSurvey(Page):
    form_model = 'player'
    form_fields = [
        'big5_1', 'big5_2', 'big5_3', 'big5_4', 'big5_5',
        'big5_6', 'big5_7', 'big5_8', 'big5_9', 'big5_10',
        'competitiveness',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def error_message(player: Player, values):
        fields = [
            'big5_1', 'big5_2', 'big5_3', 'big5_4', 'big5_5',
            'big5_6', 'big5_7', 'big5_8', 'big5_9', 'big5_10',
            'competitiveness',
        ]
        if any(values.get(f) is None for f in fields):
            return "Please answer all questions before continuing."


class SelfEsteemSurvey(Page):
    form_model = 'player'
    form_fields = [
        'rses_1', 'rses_2', 'rses_3', 'rses_4', 'rses_5',
        'rses_6', 'rses_7', 'rses_8', 'rses_9', 'rses_10',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def error_message(player: Player, values):
        fields = [f'rses_{i}' for i in range(1, 11)]
        if any(values.get(f) is None for f in fields):
            return "Please answer all questions before continuing."


class NarcissismSurvey(Page):
    form_model = 'player'
    form_fields = [
        'npi_1', 'npi_2', 'npi_3', 'npi_4',
        'npi_5', 'npi_6', 'npi_7', 'npi_8',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def error_message(player: Player, values):
        fields = [f'npi_{i}' for i in range(1, 9)]
        if any(values.get(f) is None for f in fields):
            return "Please answer all questions before continuing."


class Intro(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class RavensQuestion(Page):
    form_model = 'player'
    form_fields = ['raven_answer']

    @staticmethod
    def is_displayed(player: Player):
        if is_third_period(player):
            return third_period_accepted(player)
        return True

    @staticmethod
    def vars_for_template(player: Player):
        r = player.round_number
        if r <= C.PERIOD_LENGTH:
            period = 1
            q_in_period = r
        elif r <= 2 * C.PERIOD_LENGTH:
            period = 2
            q_in_period = r - C.PERIOD_LENGTH
        else:
            period = 3
            q_in_period = r - 2 * C.PERIOD_LENGTH
        return dict(
            question_number=r,
            total_questions=C.NUM_ROUNDS,
            period=period,
            question_in_period=q_in_period,
        )

    @staticmethod
    def error_message(player: Player, values):
        if not values.get('raven_answer'):
            return "Please select an answer before continuing."


class Feedback(Page):
    @staticmethod
    def is_displayed(player: Player):
        if not is_feedback_round(player):
            return False
        if is_third_period(player):
            return third_period_accepted(player)
        return True

    @staticmethod
    def vars_for_template(player: Player):
        cond = get_condition(player)
        score = block_correct(player)
        signals = pilot_feedback_signals(player)
        return dict(
            condition=cond,
            block_score=score,
            signals=signals,
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        cond = get_condition(player)
        score = block_correct(player)
        signals = pilot_feedback_signals(player)
        player.feedback_snapshot = json.dumps(dict(
            round=player.round_number,
            condition=cond,
            block_score=score,
            signals=signals,
        ))


class PerceivedPercentile(Page):
    form_model = 'player'
    form_fields = ['perceived_relative_performance']

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def vars_for_template(player: Player):
        return dict(period=1 if player.round_number <= C.PERIOD_LENGTH else 2)

    @staticmethod
    def error_message(player: Player, values):
        if values.get('perceived_relative_performance') is None:
            return "Please provide your percentile estimate before continuing."


class EffortTask(Page):
    form_model = 'player'
    form_fields = ['ab_count']

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def vars_for_template(player: Player):
        existing = player.field_maybe_none('ab_count')
        done = existing is not None and existing > 0
        return dict(already_done="true" if done else "false", existing_count=existing or 0)

    @staticmethod
    def live_method(player: Player, data):
        if data.get('type') == 'save_count':
            player.ab_count = int(data['count'])
            return {player.id_in_group: dict(type='saved')}


class ColorTaskIntro(Page):
    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)


class ColorTask1(Page):
    form_model = 'player'
    form_fields = ['stroop_1']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened and not player.stroop_1:
            player.stroop_1 = random.choice(["Blue", "Red", "Green", "Yellow"])


class ColorTask2(Page):
    form_model = 'player'
    form_fields = ['stroop_2']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened and not player.stroop_2:
            player.stroop_2 = random.choice(["Blue", "Red", "Green", "Yellow"])


class ColorTask3(Page):
    form_model = 'player'
    form_fields = ['stroop_3']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened and not player.stroop_3:
            player.stroop_3 = random.choice(["Blue", "Red", "Green", "Yellow"])


class ColorTask4(Page):
    form_model = 'player'
    form_fields = ['stroop_4']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened and not player.stroop_4:
            player.stroop_4 = random.choice(["Blue", "Red", "Green", "Yellow"])


class ColorTask5(Page):
    form_model = 'player'
    form_fields = ['stroop_5']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened and not player.stroop_5:
            player.stroop_5 = random.choice(["Blue", "Red", "Green", "Yellow"])


class ColorTask6(Page):
    form_model = 'player'
    form_fields = ['stroop_6']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened and not player.stroop_6:
            player.stroop_6 = random.choice(["Blue", "Red", "Green", "Yellow"])


class ExperienceAndWTA(Page):
    form_model = 'player'
    form_fields = ['task_enjoyment', 'payment_satisfaction']

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def vars_for_template(player: Player):
        period = 1 if player.round_number <= C.PERIOD_LENGTH else 2
        correct = period_correct(player)
        earnings = float(correct * C.PAY_PER_CORRECT)
        return dict(period=period, period_earnings=f"{earnings:.2f}")

    @staticmethod
    def error_message(player: Player, values):
        if values.get('task_enjoyment') is None or values.get('payment_satisfaction') is None:
            return "Please answer all questions before continuing."


class Valuation(Page):
    form_model = 'player'
    form_fields = []

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def vars_for_template(player: Player):
        if 'wta_state' not in player.participant.vars:
            player.participant.vars['wta_state'] = dict(step=0)
        s = player.participant.vars['wta_state']
        amount = WTA_AMOUNTS[s['step']]
        period = 1 if player.round_number <= C.PERIOD_LENGTH else 2
        cond = get_condition(player)
        if cond in ('quantitative_social', 'qualitative_social'):
            feedback_desc = "number correct + reported performance of others"
        else:
            feedback_desc = "number correct"
        return dict(
            current_amount=f"\u20ac{amount:.2f}",
            step=s['step'] + 1,
            total_steps=len(WTA_AMOUNTS),
            is_second_period=period == 2,
            feedback_desc=feedback_desc,
        )

    @staticmethod
    def live_method(player: Player, data):
        s = player.participant.vars.get('wta_state')
        if not s:
            return {player.id_in_group: dict(error="State missing; please reload.")}

        choice = data.get('choice')
        if choice not in ('Yes', 'No'):
            return {player.id_in_group: dict(error="Invalid choice.")}

        field = f'wta_{s["step"] + 1}'
        setattr(player, field, choice)
        s['step'] += 1

        if s['step'] >= len(WTA_AMOUNTS):
            del player.participant.vars['wta_state']
            return {player.id_in_group: dict(finished=True)}

        amount = WTA_AMOUNTS[s['step']]
        return {player.id_in_group: dict(
            finished=False,
            next_amount=f"\u20ac{amount:.2f}",
            step=s['step'] + 1,
        )}


class SocialMediaUsage(Page):
    form_model = 'player'
    form_fields = [
        'social_media_hours',
        'sm_instagram', 'sm_tiktok', 'sm_twitter', 'sm_facebook',
        'sm_snapchat', 'sm_youtube', 'sm_reddit', 'sm_linkedin',
        'sm_other', 'sm_other_text', 'sm_none',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def error_message(player: Player, values):
        if values.get('social_media_hours') is None:
            return "Please indicate your daily social media usage."
        platforms = [
            'sm_instagram', 'sm_tiktok', 'sm_twitter', 'sm_facebook',
            'sm_snapchat', 'sm_youtube', 'sm_reddit', 'sm_linkedin', 'sm_other',
        ]
        has_platform = any(values.get(p) for p in platforms)
        has_none = values.get('sm_none')
        if not has_platform and not has_none:
            return "Please select at least one option."
        if values.get('sm_other') and not (values.get('sm_other_text') or '').strip():
            return "Please specify which other platform(s) you use."


class RealismQuestion(Page):
    form_model = 'player'
    form_fields = ['realism_feedback']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def error_message(player: Player, values):
        if not (values.get('realism_feedback') or '').strip():
            return "Please share your thoughts before continuing."


class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 2 * C.PERIOD_LENGTH

    @staticmethod
    def vars_for_template(player: Player):
        raven_total = total_correct(player)

        ab_total = 0
        stroop_total = 0
        for r in C.END_OF_PERIOD_ROUNDS:
            p = player.in_round(r)
            ab_total += effort_ab_count(p)
            stroop_total += stroop_correct_count(p)

        payoff = cu(0)
        payoff += raven_total * C.PAY_PER_CORRECT
        payoff += cu(ab_total // 50) * AB_PAY_PER_50
        payoff += stroop_total * C.PAY_PER_STROOP

        # Randomly select one WTA decision for implementation
        # Pool all WTA decisions from both periods (round 10 and round 20)
        all_wta = []
        for eop_round in C.END_OF_PERIOD_ROUNDS:
            p_eop = player.in_round(eop_round)
            for i in range(1, len(WTA_AMOUNTS) + 1):
                val = p_eop.field_maybe_none(f'wta_{i}')
                all_wta.append((eop_round, i, val))

        rng = random.Random(f"{player.session.code}-{player.participant.code}-wta")
        selected_idx = rng.randint(0, len(all_wta) - 1)
        sel_round, wta_i, selected_choice = all_wta[selected_idx]
        selected_amount = WTA_AMOUNTS[wta_i - 1]
        selected_for_retake = selected_choice == "Yes"

        # The third period inherits the feedback condition from the period
        # in which the selected WTA decision was made
        if sel_round <= C.PERIOD_LENGTH:
            p3_condition = player.participant.period_1_condition
        else:
            p3_condition = player.participant.period_2_condition

        player.participant.third_period_accepted = selected_for_retake
        player.participant.third_period_pay_rate = selected_amount if selected_for_retake else 0
        player.participant.vars['third_period_condition'] = p3_condition

        if p3_condition in ('quantitative_social', 'qualitative_social'):
            p3_feedback_desc = "number correct + reported performance of others"
        else:
            p3_feedback_desc = "number correct"

        player.payoff = payoff

        player.participant.social_media_summary = dict(
            period_1_condition=player.participant.period_1_condition,
            period_2_condition=player.participant.period_2_condition,
            third_period_condition=p3_condition,
            raven_total=raven_total,
            ab_total=ab_total,
            stroop_total=stroop_total,
            selected_wta_amount=selected_amount,
            selected_for_retake=selected_for_retake,
            payoff=float(payoff),
        )

        return dict(
            raven_total=raven_total,
            ab_total=ab_total,
            stroop_total=stroop_total,
            selected_for_retake=selected_for_retake,
            selected_amount=f"\u20ac{selected_amount:.2f}",
            p3_feedback_desc=p3_feedback_desc,
            payoff=payoff,
        )


class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        # Raven's correct in periods 1 & 2
        raven_p12 = 0
        for p in player.in_rounds(1, 2 * C.PERIOD_LENGTH):
            if (p.field_maybe_none('raven_answer') or '') == RAVEN_CORRECT:
                raven_p12 += 1
        raven_payoff = raven_p12 * C.PAY_PER_CORRECT

        # Effort and Stroop from end-of-period rounds
        ab_total = 0
        stroop_total = 0
        for r in C.END_OF_PERIOD_ROUNDS:
            p = player.in_round(r)
            ab_total += effort_ab_count(p)
            stroop_total += stroop_correct_count(p)
        effort_payoff = cu(ab_total // 50) * AB_PAY_PER_50
        stroop_payoff = stroop_total * C.PAY_PER_STROOP

        base_payoff = raven_payoff + effort_payoff + stroop_payoff

        # Period 3 payoff
        p3_correct = 0
        p3_pay_rate = player.participant.vars.get('third_period_pay_rate', 0)
        accepted = third_period_accepted(player)
        if accepted:
            for p in player.in_rounds(C.THIRD_PERIOD_START, C.NUM_ROUNDS):
                if (p.field_maybe_none('raven_answer') or '') == RAVEN_CORRECT:
                    p3_correct += 1
        p3_payoff = cu(p3_correct * p3_pay_rate) if accepted else cu(0)

        total_payoff = base_payoff + p3_payoff
        player.payoff = total_payoff

        p3_condition = player.participant.vars.get('third_period_condition', 'control')
        if p3_condition in ('quantitative_social', 'qualitative_social'):
            p3_feedback_desc = "number correct + reported performance of others"
        else:
            p3_feedback_desc = "number correct"

        return dict(
            raven_p12=raven_p12,
            raven_payoff=raven_payoff,
            ab_total=ab_total,
            effort_payoff=effort_payoff,
            stroop_total=stroop_total,
            stroop_payoff=stroop_payoff,
            base_payoff=base_payoff,
            accepted=accepted,
            p3_correct=p3_correct,
            p3_pay_rate=f"\u20ac{p3_pay_rate:.2f}" if accepted else "",
            p3_payoff=p3_payoff,
            p3_feedback_desc=p3_feedback_desc,
            total_payoff=total_payoff,
        )


page_sequence = [
    Consent,
    BigFiveSurvey,
    SelfEsteemSurvey,
    NarcissismSurvey,
    Intro,
    RavensQuestion,
    Feedback,
    PerceivedPercentile,
    EffortTask,
    ColorTaskIntro,
    ColorTask1,
    ColorTask2,
    ColorTask3,
    ColorTask4,
    ColorTask5,
    ColorTask6,
    ExperienceAndWTA,
    Valuation,
    Results,
    SocialMediaUsage,
    RealismQuestion,
    FinalResults,
]
