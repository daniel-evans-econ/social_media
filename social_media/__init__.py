from otree.api import *
import json
import random


doc = """
Social media and well-being experiment.
Subjects complete Raven's Progressive Matrices across two periods of 10 questions each.
Each subject experiences the control condition in one period and one of two social feedback
treatments in the other (mixed-subject design, order randomized).
"""

# Prolific study completion redirect (participant return URL)
PROLIFIC_COMPLETION_URL = (
    "https://app.prolific.com/submissions/complete?cc=REPLACE_WITH_YOUR_COMPLETION_CODE"
)

RAVEN_CORRECT = "B"

# AB_PAY_PER_50 = cu(0.05)  # disabled: a-b button-press effort task removed
STROOP_ANSWERS = ["Blue", "Red", "Green", "Yellow", "Green", "Blue"]
RAVENS_TIMEOUT_SECONDS = 90  # 1.5 minutes per Raven's question

QUAL_EMOJIS = ["\U0001f603", "\U0001f610", "\U0001f61e"]  # smile / neutral / frown

# Display names used as the sender of the simulated peer report shown on the
# in-question sidebar. One is randomly drawn per feedback round.
PILOT_NAMES = ["Jane", "John"]

# Short example notes for qualitative pilot peer messages (always non-empty).
PILOT_QUAL_SENTENCES = [
    "Going OK so far.",
    "Mixed feelings.",
    "Phew, that was a block.",
]
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

MOOD_CHOICES = [
    [1, "Very bad"],
    [2, "Somewhat bad"],
    [3, "Neutral"],
    [4, "Somewhat good"],
    [5, "Very good"],
]

# Overall self-reported survey reliability (Dohmen & Jagelka): 11-point scale 0–10.
OVERALL_RELIABILITY_CHOICES = [[n, str(n)] for n in range(11)]

GENDER_CHOICES = [
    ["man", "Man"],
    ["woman", "Woman"],
    ["nonbinary_other_prefer_not_say", "Non-binary/other/prefer not to say"],
]

EDUCATION_CHOICES = [
    ["less_hs", "Less than high school"],
    ["hs", "High school"],
    ["some_college", "Some college"],
    ["bachelor", "Bachelor's degree"],
    ["master", "Master's degree"],
    ["doctorate", "Doctorate / PhD"],
    ["other", "Other"],
]

WTA_AMOUNTS = [0.01, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]

# ---- Cloudflare Turnstile (bot check) ----
ENABLE_TURNSTILE = True
TURNSTILE_SITE_KEY = "0x4AAAAAACnfkwrD0j2j_URF"  # placeholder; set via env in production
TURNSTILE_SECRET_KEY = "0x4AAAAAACnfk_ZxfVMEct1r7CRNuh19G1M"  # placeholder
TURNSTILE_BYPASS_KEY = "stonkgoup"
TURNSTILE_USE_TEST_KEYS_ON_LOCALHOST = True
TURNSTILE_ALLOW_AUTO_BYPASS_ON_LOCALHOST = True
TURNSTILE_TEST_SITE_KEY = "1x00000000000000000000AA"
TURNSTILE_TEST_SECRET_KEY = "1x0000000000000000000000000000000AA"


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
    raven_timeout = models.BooleanField(initial=False)
    feedback_snapshot = models.LongStringField(blank=True)

    # ---- Per-block report a participant might send to a future participant ----
    # Stored only on rounds that end a 5-question block (5, 10, 15, 20, 25, 30).
    report_number = models.IntegerField(min=0, max=5, blank=True)
    report_emoji = models.StringField(blank=True)
    report_message = models.StringField(blank=True, max_length=140)
    report_shared = models.BooleanField(initial=False, blank=True)
    report_display_name = models.StringField(blank=True, max_length=60)
    # Snapshot of received signal so we can audit later
    received_signal_name = models.StringField(blank=True)
    received_signal_value = models.StringField(blank=True)

    # ---- Bot check (Cloudflare Turnstile + honeypot) ----
    turnstile_token = models.StringField(blank=True)
    turnstile_bypass_key = models.StringField(blank=True)
    turnstile_client_host = models.StringField(blank=True)
    honeypot_intro_response = models.LongStringField(blank=True)
    honeypot_intro_triggered = models.BooleanField(initial=False)

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
    big5_accuracy = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")

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
    mood = models.IntegerField(
        choices=MOOD_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True,
        label="",
    )

    # ---- Confidence in percentile estimate (0-100 slider) ----
    perceived_percentile_confidence = models.IntegerField(min=0, max=100, blank=True, label="")

    # ---- Overall self-reported reliability (Dohmen & Jagelka): end-of-survey 0–10 ----
    survey_reliability = models.IntegerField(
        choices=OVERALL_RELIABILITY_CHOICES,
        widget=widgets.RadioSelectHorizontal,
        blank=True,
        label="",
    )

    # ---- Demographics ----
    age = models.IntegerField(min=18, max=99, blank=True, label="What is your age?")
    gender = models.StringField(choices=GENDER_CHOICES, widget=widgets.RadioSelect, blank=True,
                                label="What is your gender?")
    education = models.StringField(choices=EDUCATION_CHOICES, widget=widgets.RadioSelect, blank=True,
                                   label="What is your highest level of education?")

    # ---- Two simultaneous WTAs (treatment vs control) ----
    # Each row is one payment level; Yes/No per condition.
    wta_t_1 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_2 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_3 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_4 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_5 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_6 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_7 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_8 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_9 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_10 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_t_11 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")

    wta_c_1 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_2 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_3 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_4 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_5 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_6 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_7 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_8 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_9 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_10 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")
    wta_c_11 = models.StringField(choices=["Yes", "No"], widget=widgets.RadioSelectHorizontal, blank=True, label="")

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
    sm_bluesky = models.BooleanField(blank=True, initial=False)
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
            # The actual third-period condition is set in Results.vars_for_template
            # (after the WTA selection); if not yet set, default to control.
            p.condition = p.participant.vars.get('third_period_condition', 'control')


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
    """Number of correct answers in the current 5-question block (includes this round once saved)."""
    r = player.round_number
    block_start = ((r - 1) // 5) * 5 + 1
    total = 0
    for p in player.in_rounds(block_start, r):
        if (p.field_maybe_none('raven_answer') or '') == RAVEN_CORRECT:
            total += 1
    return total


def block_correct_prior_in_block(player: Player):
    """Correct count in this block for rounds strictly before the current one (DB-saved only).

    Used for feedback sidebar display: the current round's answer is not saved until the
    page is submitted, so `block_correct` would undercount by one on GET.
    """
    r = player.round_number
    block_start = ((r - 1) // 5) * 5 + 1
    if r <= block_start:
        return 0
    total = 0
    for p in player.in_rounds(block_start, r - 1):
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
    Simulate one report from a past (pilot) participant for the current block.
    Quantitative: score 0-5; peer message is fixed-format copy (see template).
    Qualitative: 1 randomly drawn emoji plus a non-empty sentence (always shown).
    """
    cond = get_condition(player)
    r = player.round_number
    seed = f"{player.session.code}-{player.participant.code}-{r}"
    rng = random.Random(seed)

    name = rng.choice(PILOT_NAMES)

    if cond == 'quantitative_social':
        score = rng.randint(0, 5)
        return dict(type='quantitative', name=name, score=score)

    if cond == 'qualitative_social':
        emoji = rng.choice(QUAL_EMOJIS)
        sentence = rng.choice(PILOT_QUAL_SENTENCES)  # always non-empty
        return dict(type='qualitative', name=name, emoji=emoji, sentence=sentence)

    return dict(type='control', name=None, sentence='')


# def effort_ab_count(player: Player):
#     return player.field_maybe_none('ab_count') or 0


def experienced_conditions(player: Player):
    """Return (treatment_condition, control_condition_label) for the WTA elicitation.

    The participant always experiences control in one period and one of the social
    conditions in the other. We return the social condition for the 'treatment' label.
    """
    p1 = player.participant.period_1_condition
    p2 = player.participant.period_2_condition
    treatment = p1 if p1 != 'control' else p2
    return treatment, 'control'


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
        'big5_accuracy',
        'competitiveness',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def error_message(player: Player, values):
        fields = [
            'big5_1', 'big5_2', 'big5_3', 'big5_4', 'big5_5',
            'big5_6', 'big5_7', 'big5_8', 'big5_9', 'big5_10',
            'big5_accuracy',
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
        return player.round_number == C.NUM_ROUNDS

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
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def error_message(player: Player, values):
        fields = [f'npi_{i}' for i in range(1, 9)]
        if any(values.get(f) is None for f in fields):
            return "Please answer all questions before continuing."


class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'education']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def error_message(player: Player, values):
        if values.get('age') is None:
            return "Please enter your age."
        if not values.get('gender'):
            return "Please indicate your gender."
        if not values.get('education'):
            return "Please indicate your highest level of education."


class BotCheck(Page):
    """Cloudflare Turnstile + invisible honeypot bot check (round 1 only)."""
    form_model = 'player'
    form_fields = ['turnstile_token', 'turnstile_bypass_key',
                   'turnstile_client_host', 'honeypot_intro_response']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            turnstile_site_key=TURNSTILE_SITE_KEY,
            turnstile_test_site_key=TURNSTILE_TEST_SITE_KEY,
            turnstile_use_test_keys_on_localhost_js='true' if TURNSTILE_USE_TEST_KEYS_ON_LOCALHOST else 'false',
            enable_turnstile=ENABLE_TURNSTILE,
        )

    @staticmethod
    def error_message(player: Player, values):
        # 1. Honeypot check: a hidden, off-screen text field. Bots will fill it; humans won't.
        honeypot_raw = values.get('honeypot_intro_response') or ''
        honeypot_triggered = bool(str(honeypot_raw).strip())
        player.honeypot_intro_triggered = honeypot_triggered
        # We don't reject bots immediately on honeypot trigger; we record it for later exclusion.

        if not ENABLE_TURNSTILE:
            return

        host = (values.get('turnstile_client_host') or '').strip().lower()
        is_localhost = host in ('localhost', '127.0.0.1', '::1')
        if is_localhost and TURNSTILE_ALLOW_AUTO_BYPASS_ON_LOCALHOST:
            return

        provided_bypass = (values.get('turnstile_bypass_key') or '').strip()
        if TURNSTILE_BYPASS_KEY and provided_bypass == TURNSTILE_BYPASS_KEY:
            player.participant.vars['captcha_bypassed'] = True
            return

        token = (values.get('turnstile_token') or '').strip()
        if not token:
            return {'turnstile_token': 'Please complete the bot check to continue.'}

        # Server-side siteverify
        try:
            from urllib import parse, request
            import json as _json
            secret_key = (TURNSTILE_TEST_SECRET_KEY if (is_localhost and TURNSTILE_USE_TEST_KEYS_ON_LOCALHOST)
                          else TURNSTILE_SECRET_KEY)
            data = parse.urlencode({'secret': secret_key, 'response': token}).encode()
            req = request.Request(
                'https://challenges.cloudflare.com/turnstile/v0/siteverify', data=data,
            )
            resp = request.urlopen(req, timeout=6)
            result = _json.load(resp)
            if not result.get('success'):
                return {'turnstile_token': 'Bot check verification failed; please try again.'}
        except Exception:
            return {'turnstile_token': 'Bot check could not be verified; please try again.'}

        player.participant.vars['captcha_verified'] = True


class Intro(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class RavensQuestion(Page):
    """Raven's Progressive Matrices question.

    On block-end rounds (5, 10, 15, 20, 25, 30) the page also includes an
    inline, slide-in feedback sidebar that appears after the participant
    answers the question and clicks "Next". The same form submission
    therefore captures both the answer and (optionally) the report the
    participant chooses to share with future participants.
    """
    form_model = 'player'
    form_fields = [
        'raven_answer',
        'report_number',
        'report_emoji',
        'report_message',
        'report_shared',
        'report_display_name',
    ]
    timeout_seconds = RAVENS_TIMEOUT_SECONDS

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

        ctx = dict(
            question_number=r,
            total_questions=C.NUM_ROUNDS,
            period=period,
            question_in_period=q_in_period,
            is_feedback_round=False,
        )

        if is_feedback_round(player):
            cond = get_condition(player)
            score = block_correct(player)
            signal = pilot_feedback_signals(player)
            signal_name = (signal.get('name') or '') if isinstance(signal, dict) else ''
            signal_initial = signal_name[:1].upper() if signal_name else '?'
            ctx.update(
                is_feedback_round=True,
                condition=cond,
                block_score=score,
                block_score_prior=block_correct_prior_in_block(player),
                raven_correct_letter=RAVEN_CORRECT,
                signal=signal,
                signal_initial=signal_initial,
                qual_emojis=QUAL_EMOJIS,
                number_options=[0, 1, 2, 3, 4, 5],
                in_treatment=cond in ('quantitative_social', 'qualitative_social'),
                is_quantitative=cond == 'quantitative_social',
                is_qualitative=cond == 'qualitative_social',
            )
        return ctx

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.raven_timeout = True

        if not is_feedback_round(player):
            return

        cond = get_condition(player)
        score = block_correct(player)
        signal = pilot_feedback_signals(player)
        if cond == 'quantitative_social':
            n = player.field_maybe_none('report_number')
            if n is not None:
                player.report_message = (
                    f"Message: I got {n} out of the last 5 questions correct."
                )
        if cond in ('quantitative_social', 'qualitative_social'):
            player.report_display_name = (
                (player.field_maybe_none('report_display_name') or '').strip()
            )
        player.feedback_snapshot = json.dumps(dict(
            round=player.round_number,
            condition=cond,
            block_score=score,
            signal=signal,
            sent_number=player.field_maybe_none('report_number'),
            sent_emoji=player.field_maybe_none('report_emoji'),
            sent_message=player.field_maybe_none('report_message'),
            shared=player.field_maybe_none('report_shared'),
            sent_display_name=player.field_maybe_none('report_display_name'),
        ))
        if signal.get('type') == 'quantitative':
            player.received_signal_name = signal.get('name') or ''
            player.received_signal_value = str(signal.get('score'))
        elif signal.get('type') == 'qualitative':
            player.received_signal_name = signal.get('name') or ''
            player.received_signal_value = signal.get('emoji') or ''

    @staticmethod
    def error_message(player: Player, values):
        # Timed-out submits include timeout_happened; skip further checks so oTree can advance.
        if values.get('timeout_happened'):
            return
        if not values.get('raven_answer'):
            return "Please select an answer before continuing."
        if not is_feedback_round(player):
            return
        cond = get_condition(player)
        if cond not in ('quantitative_social', 'qualitative_social'):
            return
        if cond == 'quantitative_social':
            rn = values.get('report_number')
            if rn is None or rn == '':
                return "Please select how many questions you got right."
            if not (values.get('report_display_name') or '').strip():
                return "Please enter the name you want to use."
            return
        if not (values.get('report_display_name') or '').strip():
            return "Please enter the name you want to use."
        msg = (values.get('report_message') or '').strip()
        if not msg:
            return "Please add a short note before continuing."
        if not values.get('report_emoji'):
            return "Please indicate how the last 5 questions went."


class PerceivedPercentile(Page):
    form_model = 'player'
    form_fields = ['perceived_relative_performance']

    @staticmethod
    def is_displayed(player: Player):
        # Period 3 (rounds 21–30): main pattern task only — no percentile at round 30.
        return is_end_of_period(player)

    @staticmethod
    def vars_for_template(player: Player):
        r = player.round_number
        if r <= C.PERIOD_LENGTH:
            period = 1
        elif r <= 2 * C.PERIOD_LENGTH:
            period = 2
        else:
            period = 3
        return dict(period=period)

    @staticmethod
    def error_message(player: Player, values):
        if values.get('perceived_relative_performance') is None:
            return "Please provide your percentile estimate before continuing."


class PerceivedPercentileConfidence(Page):
    """0-100 slider for confidence in the prior percentile guess."""
    form_model = 'player'
    form_fields = ['perceived_percentile_confidence']

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def vars_for_template(player: Player):
        r = player.round_number
        if r <= C.PERIOD_LENGTH:
            period = 1
        elif r <= 2 * C.PERIOD_LENGTH:
            period = 2
        else:
            period = 3
        prior_guess = player.field_maybe_none('perceived_relative_performance')
        return dict(
            period=period,
            prior_guess=prior_guess,
            has_prior_guess=prior_guess is not None,
        )

    @staticmethod
    def error_message(player: Player, values):
        if values.get('perceived_percentile_confidence') is None or values.get('perceived_percentile_confidence') == '':
            return "Please indicate your level of certainty before continuing."


# ---------------------------------------------------------------------------
# A-B button-press effort task: DISABLED (commented out for now)
# ---------------------------------------------------------------------------
# class EffortTask(Page):
#     form_model = 'player'
#     form_fields = ['ab_count']
#
#     @staticmethod
#     def is_displayed(player: Player):
#         return is_end_of_period(player)
#
#     @staticmethod
#     def vars_for_template(player: Player):
#         existing = player.field_maybe_none('ab_count')
#         done = existing is not None and existing > 0
#         return dict(already_done="true" if done else "false", existing_count=existing or 0)
#
#     @staticmethod
#     def live_method(player: Player, data):
#         if data.get('type') == 'save_count':
#             player.ab_count = int(data['count'])
#             return {player.id_in_group: dict(type='saved')}


class ColorTaskIntro(Page):
    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)


def _stroop_color_task_error(values: dict, field_name: str):
    """Require a color choice on manual submit; allow timeout auto-submit."""
    if values.get('timeout_happened'):
        return
    v = values.get(field_name)
    if not v:
        return "Please select a color before continuing."


class ColorTask1(Page):
    form_model = 'player'
    form_fields = ['stroop_1']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_1')

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
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_2')

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
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_3')

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
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_4')

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
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_5')

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
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_6')

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened and not player.stroop_6:
            player.stroop_6 = random.choice(["Blue", "Red", "Green", "Yellow"])


class EndOfPeriodSurvey(Page):
    """Single page combining mood, task enjoyment, and payment satisfaction.

    Shown at the end of periods 1 and 2 only (rounds 10 and 20). Period 3 is
    pattern-completion questions only—no follow-up survey block after round 30.
    """
    form_model = 'player'
    form_fields = ['mood', 'task_enjoyment', 'payment_satisfaction']

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period(player)

    @staticmethod
    def vars_for_template(player: Player):
        r = player.round_number
        if r <= C.PERIOD_LENGTH:
            period = 1
        elif r <= 2 * C.PERIOD_LENGTH:
            period = 2
        else:
            period = 3
        if r >= C.THIRD_PERIOD_START:
            pay_rate = player.participant.vars.get('third_period_pay_rate', 0) or 0
        else:
            pay_rate = float(C.PAY_PER_CORRECT)
        correct = period_correct(player)
        earnings = correct * pay_rate
        return dict(period=period, period_earnings=f"{earnings:.2f}")

    @staticmethod
    def error_message(player: Player, values):
        if (values.get('mood') is None or values.get('task_enjoyment') is None
                or values.get('payment_satisfaction') is None):
            return "Please answer all questions before continuing."


class WTACompare(Page):
    """Two simultaneous WTA price lists (treatment vs control), shown after both periods.

    Only displayed at the end of period 2 (round 20). Each row corresponds to a
    payment level; the participant says Yes/No separately for each condition.
    """
    form_model = 'player'
    form_fields = (
        [f'wta_t_{i}' for i in range(1, len(WTA_AMOUNTS) + 1)]
        + [f'wta_c_{i}' for i in range(1, len(WTA_AMOUNTS) + 1)]
    )

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 2 * C.PERIOD_LENGTH

    @staticmethod
    def vars_for_template(player: Player):
        treatment, _ = experienced_conditions(player)
        rows = []
        for i, amount in enumerate(WTA_AMOUNTS, 1):
            rows.append(dict(
                index=i,
                amount=f"\u20ac{amount:.2f}",
                t_field=f"wta_t_{i}",
                c_field=f"wta_c_{i}",
            ))
        return dict(
            treatment_condition=treatment,
            rows=rows,
        )

    @staticmethod
    def error_message(player: Player, values):
        for i in range(1, len(WTA_AMOUNTS) + 1):
            if not values.get(f'wta_t_{i}') or not values.get(f'wta_c_{i}'):
                return "Please make a choice for every payment level in BOTH columns."


class SocialMediaUsage(Page):
    form_model = 'player'
    # Order: platforms first (required), then hours (skippable if "I do not use social media").
    form_fields = [
        'sm_instagram', 'sm_tiktok', 'sm_twitter', 'sm_facebook',
        'sm_snapchat', 'sm_youtube', 'sm_reddit', 'sm_linkedin', 'sm_bluesky',
        'sm_other', 'sm_other_text', 'sm_none',
        'social_media_hours',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def error_message(player: Player, values):
        platforms = [
            'sm_instagram', 'sm_tiktok', 'sm_twitter', 'sm_facebook',
            'sm_snapchat', 'sm_youtube', 'sm_reddit', 'sm_linkedin', 'sm_bluesky',
            'sm_other',
        ]
        has_platform = any(values.get(p) for p in platforms)
        has_none = values.get('sm_none')
        if not has_platform and not has_none:
            return "Please select at least one platform, or 'I do not use social media'."
        if has_none and has_platform:
            return "If you selected 'I do not use social media', please uncheck the other platforms."
        if values.get('sm_other') and not (values.get('sm_other_text') or '').strip():
            return "Please specify which other platform(s) you use."
        # Hours is required only if the participant uses any social media.
        if not has_none and values.get('social_media_hours') is None:
            return "Please indicate your daily social media usage."


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


class SurveyReliabilityOverall(Page):
    """Dohmen & Jagelka-style overall reliability, last substantive screen before thank-you."""

    form_model = 'player'
    form_fields = ['survey_reliability']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def error_message(player: Player, values):
        if values.get('survey_reliability') is None:
            return "Please select a value on the scale before continuing."


class Results(Page):
    """Intermediate results page (after WTA, end of period 2).

    Shows the participant's earnings so far and which WTA decision was randomly
    selected for implementation, including whether period 3 will be played and
    under which feedback condition.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 2 * C.PERIOD_LENGTH

    @staticmethod
    def vars_for_template(player: Player):
        raven_total = total_correct(player)

        stroop_total = 0
        for r in C.END_OF_PERIOD_ROUNDS:
            p = player.in_round(r)
            stroop_total += stroop_correct_count(p)

        payoff = cu(0)
        payoff += raven_total * C.PAY_PER_CORRECT
        payoff += stroop_total * C.PAY_PER_STROOP

        # Randomly select one WTA decision (one row, one column) for implementation
        treatment, _ = experienced_conditions(player)
        n = len(WTA_AMOUNTS)
        rng = random.Random(f"{player.session.code}-{player.participant.code}-wta")
        selected_row = rng.randint(0, n - 1)
        selected_col = rng.choice(['t', 'c'])
        selected_amount = WTA_AMOUNTS[selected_row]
        field = f'wta_{selected_col}_{selected_row + 1}'
        selected_choice = player.field_maybe_none(field) or "No"
        selected_for_retake = selected_choice == "Yes"
        # The third period inherits the feedback condition from the column selected
        if selected_col == 't':
            p3_condition = treatment
        else:
            p3_condition = 'control'

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
            stroop_total=stroop_total,
            selected_wta_amount=selected_amount,
            selected_wta_column=selected_col,
            selected_for_retake=selected_for_retake,
            payoff=float(payoff),
        )

        selected_accept_decline = 'Accept' if selected_choice == 'Yes' else 'Decline'
        selected_feedback_label = (
            'Number correct + message from participant'
            if selected_col == 't'
            else 'Only number correct'
        )

        return dict(
            raven_total=raven_total,
            stroop_total=stroop_total,
            selected_for_retake=selected_for_retake,
            selected_amount=f"\u20ac{selected_amount:.2f}",
            selected_column='treatment' if selected_col == 't' else 'control',
            p3_feedback_desc=p3_feedback_desc,
            payoff=payoff,
            selected_accept_decline=selected_accept_decline,
            selected_feedback_label=selected_feedback_label,
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

        # Stroop only after periods 1 & 2 (rounds 10 and 20); not repeated after period 3.
        stroop_total = 0
        for r in C.END_OF_PERIOD_ROUNDS:
            p = player.in_round(r)
            stroop_total += stroop_correct_count(p)
        stroop_payoff = stroop_total * C.PAY_PER_STROOP

        base_payoff = raven_payoff + stroop_payoff

        # Period 3 payoff
        p3_correct = 0
        p3_pay_rate = player.participant.vars.get('third_period_pay_rate', 0) or 0
        accepted = third_period_accepted(player)
        if accepted:
            for p in player.in_rounds(C.THIRD_PERIOD_START, C.NUM_ROUNDS):
                if (p.field_maybe_none('raven_answer') or '') == RAVEN_CORRECT:
                    p3_correct += 1
        p3_payoff = cu(p3_correct * p3_pay_rate) if accepted else cu(0)

        total_payoff = base_payoff + p3_payoff
        player.payoff = total_payoff

        return dict(total_payoff=total_payoff)


class ProlificCompletion(Page):
    """Final screen: redirect participants back to Prolific for completion credit."""

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        return dict(prolific_url=PROLIFIC_COMPLETION_URL)


page_sequence = [
    # Round 1 only (bot check first; Turnstile + honeypot match cd_tournament_main pattern)
    BotCheck,
    Consent,
    Intro,
    # Every round (rounds 1-30, period 3 conditional on WTA acceptance).
    # On feedback rounds (5, 10, 15, 20, 25, 30) this page also shows an
    # inline slide-in sidebar with block summary + (in treatments) a peer
    # report and a compose-your-own panel.
    RavensQuestion,
    # End of periods 1 & 2 only (rounds 10 and 20); period 3 skips these pages.
    PerceivedPercentile,
    PerceivedPercentileConfidence,
    ColorTaskIntro,
    ColorTask1,
    ColorTask2,
    ColorTask3,
    ColorTask4,
    ColorTask5,
    ColorTask6,
    EndOfPeriodSurvey,
    # Round 20 only: simultaneous treatment vs control WTA
    WTACompare,
    Results,
    # Round 30 only: surveys + final results
    BigFiveSurvey,
    SelfEsteemSurvey,
    NarcissismSurvey,
    Demographics,
    SocialMediaUsage,
    RealismQuestion,
    SurveyReliabilityOverall,
    FinalResults,
    ProlificCompletion,
]
