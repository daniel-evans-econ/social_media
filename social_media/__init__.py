from otree.api import *
import json
import os
import random
from pathlib import Path

from . import questions_data as QD


doc = """
Social media and well-being experiment.
Subjects complete three blocks (periods) of 15 cognitive questions each. Each
subject experiences the control condition in one block and one of two social
feedback treatments (quantitative / qualitative) in the others (mixed-subject
design, order randomized). The experiment runs in one of three pilot modes
(Initial / IQ / Main), selected with the EXPERIMENT_PILOT environment variable.
"""

# Prolific study completion redirect (participant return URL)
PROLIFIC_COMPLETION_URL = (
    "https://app.prolific.com/submissions/complete?cc=REPLACE_WITH_YOUR_COMPLETION_CODE"
)

STROOP_COLORS = ["Blue", "Red", "Green", "Yellow"]

# Three FIXED blocks of Stroop (color-word) questions. Each block is six
# (word, ink-color) pairs; the correct answer is always the ink color, not the
# word. Which block a participant sees in which period, and the order of the six
# questions within a block, are randomized per participant (see _stroop_plan);
# the grouping of questions into blocks is fixed and the same for everyone.
STROOP_BLOCKS = [
    [
        dict(word="RED", color="Blue"),
        dict(word="GREEN", color="Red"),
        dict(word="BLUE", color="Yellow"),
        dict(word="YELLOW", color="Green"),
        dict(word="GREEN", color="Green"),
        dict(word="RED", color="Red"),
    ],
    [
        dict(word="YELLOW", color="Red"),
        dict(word="BLUE", color="Green"),
        dict(word="RED", color="Yellow"),
        dict(word="GREEN", color="Blue"),
        dict(word="BLUE", color="Blue"),
        dict(word="YELLOW", color="Yellow"),
    ],
    [
        dict(word="GREEN", color="Yellow"),
        dict(word="RED", color="Green"),
        dict(word="YELLOW", color="Blue"),
        dict(word="BLUE", color="Red"),
        dict(word="RED", color="Blue"),
        dict(word="GREEN", color="Green"),
    ],
]

QUESTION_TIMEOUT_SECONDS = 60  # 60 seconds per question
# Working-memory stimulus is flashed for exactly this long after the participant
# presses "Show image" (chosen to equalize image load time across participants).
WM_STIMULUS_SECONDS = 1.7

# Flat (participation) payment shown on the instructions page. Placeholder until
# the amount is finalized.
FLAT_PAYMENT_DISPLAY = "$X.XX"


# ---------------------------------------------------------------------------
# Pilot mode (the three switchable modes)
# ---------------------------------------------------------------------------
# Switch the active pilot with the EXPERIMENT_PILOT env var: "initial" | "iq" | "main".
PILOT = (os.environ.get("EXPERIMENT_PILOT", "initial") or "initial").strip().lower()
if PILOT not in ("initial", "iq", "main"):
    PILOT = "initial"

PILOT_CONFIG = {
    # Initial pilot: sequences (always) + 2 random of the three non-sequence
    # tasks; number-correct feedback only (no IQ); send messages but receive
    # none; all three blocks mandatory (no WTA).
    "initial": dict(
        fixed_tasks=["sequences"],
        random_pool=["shape_rotation", "working_memory", "ravens"],
        random_count=2,
        show_iq=False,
        received_message_source=None,
        iq_distribution_source=None,
        use_wta=False,
        period3_mandatory=True,
    ),
    # IQ pilot: all three non-sequence tasks; number-correct per 5 + IQ after
    # 15 (normed against the Initial pilot); receive Initial-pilot messages;
    # 3rd block optional via WTA.
    "iq": dict(
        fixed_tasks=["shape_rotation", "working_memory", "ravens"],
        random_pool=[],
        random_count=0,
        show_iq=True,
        received_message_source="initial",
        iq_distribution_source="initial",
        use_wta=True,
        period3_mandatory=False,
    ),
    # Main pilot: like IQ, but normed against / receiving messages from the IQ pilot.
    "main": dict(
        fixed_tasks=["shape_rotation", "working_memory", "ravens"],
        random_pool=[],
        random_count=0,
        show_iq=True,
        received_message_source="iq",
        iq_distribution_source="iq",
        use_wta=True,
        period3_mandatory=False,
    ),
}
CFG = PILOT_CONFIG[PILOT]

# Each task maps to an IQ "component" used in the IQ readout (IQ/Main pilots).
TASK_IQ_COMPONENT = {
    "shape_rotation": "spatial",
    "ravens": "fluid",
    "working_memory": "working_memory",
    "sequences": "numerical",
}

IQ_COMPONENT_LABELS = {
    "spatial": "spatial",
    "fluid": "fluid",
    "working_memory": "working memory",
    "numerical": "numerical",
}

# Human-readable task names, named after the IQ construct each one targets (used
# in the diagnostic bar, the task-intro page titles, and the end-of-period survey).
TASK_LABELS = {
    "sequences": "Numerical reasoning",
    "shape_rotation": "Spatial reasoning",
    "working_memory": "Working memory",
    "ravens": "Abstract reasoning",
}

# Lower-case construct phrase used inline in sentences (e.g. "the abstract
# reasoning task").
TASK_CONSTRUCT = {
    "sequences": "numerical reasoning",
    "shape_rotation": "spatial reasoning",
    "working_memory": "working memory",
    "ravens": "abstract reasoning",
}

# The IQ component each task is framed as testing (used in the instructions and
# task-explanation pages).
TASK_IQ_LABEL = {
    "shape_rotation": "spatial reasoning IQ",
    "sequences": "numerical reasoning IQ",
    "working_memory": "working memory IQ",
    "ravens": "abstract reasoning IQ",
}

# Targeted prompt shown directly above the answer choices / box on each question.
TASK_PROMPT = {
    "sequences": "Which number completes the sequence?",
    "ravens": "Which image completes the pattern?",
    "shape_rotation": "Which option shows the correctly rotated shape?",
    "working_memory": "How many squares had red dots?",
}

# Minimal "what is this task" explanation + worked example shown before each new
# task begins. ``example_image`` points at a filler image under static/examples/
# (kept outside static/questions/ so the question-bank rebuild does not wipe it);
# until a real example is dropped in, the page shows a placeholder box instead of
# a broken image.
TASK_INTRO = {
    "working_memory": dict(
        title="Working memory",
        body_html=(
            "Your task in this period is to <strong style=\"color:darkred;\">memorize</strong> "
            "the number of squares that have red dots. You will have "
            "<strong style=\"color:darkred;\">1.7 seconds</strong> to look at each pattern. "
            "This tests your <strong style=\"color:darkred;\">working memory IQ</strong>."
        ),
        example_image="examples/working_memory.png",
        example_answer=(
            "In this example, there are <strong style=\"color:darkred;\">3</strong> "
            "squares with red dots."
        ),
    ),
    "sequences": dict(
        title="Numerical reasoning",
        body_html=(
            "Your task in this period is to <strong style=\"color:darkred;\">predict the "
            "next number</strong> that follows in a given sequence. This tests your "
            "<strong style=\"color:darkred;\">numerical reasoning IQ</strong>."
        ),
        example_image="examples/sequences.png",
        example_answer=(
            "<strong style=\"color:darkred;\">B) 6</strong> completes the sequence."
        ),
    ),
    "shape_rotation": dict(
        title="Spatial reasoning",
        body_html=(
            "The top row shows a shape before and after rotation. Your task is to "
            "apply the <strong style=\"color:darkred;\">same rotation</strong> to "
            "another shape. This tests your "
            "<strong style=\"color:darkred;\">spatial reasoning IQ</strong>."
        ),
        example_image="examples/shape_rotation.png",
        example_answer="Option <strong style=\"color:darkred;\">D</strong> is the correctly rotated shape.",
    ),
    "ravens": dict(
        title="Abstract reasoning",
        body_html=(
            "Your task in this period is to choose the image that "
            "<strong style=\"color:darkred;\">completes the pattern</strong>. This tests "
            "your <strong style=\"color:darkred;\">abstract reasoning IQ</strong>."
        ),
        # C8 (excluded from the live bank); correct answer 7 per the answer key.
        example_image="examples/ravens.jpg",
        example_answer="Image <strong style=\"color:darkred;\">7</strong> completes the pattern.",
    ),
}


# ---------------------------------------------------------------------------
# Data files (cross-pilot messages + IQ distribution). Supplied between pilots.
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def static_exists(rel_path: str) -> bool:
    """Whether a static file exists (oTree's {% static %} errors on missing files)."""
    if not rel_path:
        return False
    return (STATIC_DIR / rel_path).exists()


def _load_json(name: str):
    p = DATA_DIR / name
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


_MESSAGE_CACHE = {}
_IQ_DIST_CACHE = {}


def received_message_pool():
    """Messages from the previous pilot, keyed [task][set_id][quant|qual]."""
    src = CFG["received_message_source"]
    if not src:
        return None
    if src not in _MESSAGE_CACHE:
        _MESSAGE_CACHE[src] = _load_json(f"messages_{src}.json") or {}
    return _MESSAGE_CACHE[src]


def iq_distribution():
    """Score->IQ tables from the previous pilot, keyed by component."""
    src = CFG["iq_distribution_source"]
    if not src:
        return None
    if src not in _IQ_DIST_CACHE:
        _IQ_DIST_CACHE[src] = _load_json(f"iq_distribution_{src}.json") or {}
    return _IQ_DIST_CACHE[src]


def estimate_iq(component: str, score: int, max_score: int) -> int:
    """Map a period score to an IQ estimate using the supplied distribution.

    The distribution file maps each raw period score (0..max_score) to an IQ
    for a given component, fitted from the previous pilot's data. When the file
    is absent or incomplete (e.g. demo / Initial pilot), fall back to an
    illustrative linear map spanning 70-130.
    """
    try:
        s = int(score)
    except (TypeError, ValueError):
        s = 0
    dist = iq_distribution()
    if dist and component in dist:
        table = dist[component] or {}
        v = table.get(str(s))
        if v is not None:
            return int(round(v))
    if max_score <= 0:
        return 100
    return int(round(70 + (s / max_score) * 60))


# ---------------------------------------------------------------------------
# Simulated peer messages (fallback when no real pool is available)
# ---------------------------------------------------------------------------
QUAL_EMOJI_SMILE = "\U0001f603"   # 😃
QUAL_EMOJI_NEUTRAL = "\U0001f610"  # 😐
QUAL_EMOJI_FROWN = "\U0001f61e"   # 😞
QUAL_EMOJIS = [QUAL_EMOJI_SMILE, QUAL_EMOJI_NEUTRAL, QUAL_EMOJI_FROWN]

PILOT_NAMES = ["Jane", "John"]

PILOT_QUAL_TEXT_BY_EMOJI = {
    QUAL_EMOJI_SMILE: [
        "Felt good about that one.",
        "On a roll!",
        "Going pretty well so far.",
        "These are clicking for me.",
        "Pleased with how that block went.",
    ],
    QUAL_EMOJI_NEUTRAL: [
        "Going OK so far.",
        "Mixed feelings.",
        "Could be better, could be worse.",
        "Hard to tell how I'm doing.",
        "Some easier, some harder.",
    ],
    QUAL_EMOJI_FROWN: [
        "Phew, that was a tough block.",
        "Tougher than I expected.",
        "Definitely struggling on these.",
        "Not my best block.",
        "Found that one really hard.",
    ],
}

# Score-mentioning qualitative templates now leak a raw number-correct (0-5),
# matching the number-correct framing of the feedback. {n} is filled with a
# count concordant with the emoji's valence.
PILOT_QUAL_SCORE_BY_EMOJI = {
    QUAL_EMOJI_SMILE: [
        "Pretty happy with {n} out of 5.",
        "Got {n} of 5 that round.",
        "Nailed {n} out of 5 \u2014 feeling good.",
    ],
    QUAL_EMOJI_NEUTRAL: [
        "Got {n} out of 5 this round.",
        "Ended up with {n} of 5.",
        "Around {n} out of 5.",
    ],
    QUAL_EMOJI_FROWN: [
        "Only {n} out of 5 for me.",
        "Just {n} of 5 \u2014 could be better.",
        "Managed {n} out of 5.",
    ],
}

BFI_CHOICES = [
    [1, ""],
    [2, ""],
    [3, ""],
    [4, ""],
    [5, ""],
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
    ["other_prefer_not_say", "Other / prefer not to answer"],
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
# Off by default. Set ENABLE_TURNSTILE=1 and TURNSTILE_SITE_KEY / TURNSTILE_SECRET_KEY to re-enable.
def _env_bool(name: str, default: bool = True) -> bool:
    v = os.environ.get(name)
    if v is None or str(v).strip() == "":
        return default
    s = str(v).strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return default


ENABLE_TURNSTILE = _env_bool("ENABLE_TURNSTILE", False)
TURNSTILE_SITE_KEY = os.environ.get(
    "TURNSTILE_SITE_KEY",
    "0x4AAAAAACnfkwrD0j2j_URF",
)
TURNSTILE_SECRET_KEY = os.environ.get(
    "TURNSTILE_SECRET_KEY",
    "0x4AAAAAACnfk_ZxfVMEct1r7CRNuh19G1M",
)
TURNSTILE_BYPASS_KEY = os.environ.get("TURNSTILE_BYPASS_KEY", "stonkgoup")
TURNSTILE_USE_TEST_KEYS_ON_LOCALHOST = True
TURNSTILE_ALLOW_AUTO_BYPASS_ON_LOCALHOST = True
TURNSTILE_TEST_SITE_KEY = "1x00000000000000000000AA"
TURNSTILE_TEST_SECRET_KEY = "1x0000000000000000000000000000000AA"


class C(BaseConstants):
    NAME_IN_URL = 'social_media'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 45

    # Active pilot mode, exposed for templates (e.g. the diagnostic bar).
    PILOT = PILOT

    PERIOD_LENGTH = 15
    # Feedback is shown after every 5-question block (3 blocks per 15-question period).
    FEEDBACK_ROUNDS = [5, 10, 15, 20, 25, 30, 35, 40, 45]
    END_OF_PERIOD_ROUNDS = [15, 30]
    THIRD_PERIOD_START = 31

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

    # ---- Baseline IQ reference point (randomized treatment, before any task) ----
    # iq_reference_asked: whether this participant was (randomly) shown the
    # reference-point page. iq_reference_score: their self-perceived IQ score on
    # the usual 50-150 scale, used as a reference point against which later
    # performance / reporting is compared.
    iq_reference_asked = models.BooleanField(initial=False)
    iq_reference_score = models.IntegerField(min=50, max=150, blank=True, label="")

    # ---- Per-round question (generic across task types) ----
    q_task = models.StringField(blank=True)
    q_item_id = models.StringField(blank=True)
    q_set_id = models.StringField(blank=True)
    q_difficulty = models.StringField(blank=True)
    # The participant's answer: a multiple-choice label (e.g. "B" or "3") or, for
    # working memory, the reported number of red-dot squares (e.g. "7").
    q_answer = models.StringField(blank=True)
    q_correct = models.BooleanField(initial=False)
    q_timeout = models.BooleanField(initial=False)
    # Working memory: whether the stimulus has already been flashed once on this
    # round (so a re-render after an empty submit can't grant another look).
    q_stimulus_shown = models.BooleanField(initial=False)
    # Tab/window-switch counter for THIS question (one row per round).
    q_tab_switches = models.IntegerField(initial=0)
    # Seconds from page load to first answer interaction.
    q_response_time = models.FloatField(blank=True)
    feedback_snapshot = models.LongStringField(blank=True)

    # ---- Per-period IQ readout (IQ / Main pilots only) ----
    iq_estimate = models.IntegerField(blank=True)

    # ---- Per-block report a participant might send to another participant ----
    # report_number stores the number-correct (0-5) the participant chooses to report.
    report_number = models.IntegerField(min=0, max=5, blank=True)
    report_emoji = models.StringField(blank=True)
    report_message = models.StringField(blank=True, max_length=140)
    report_shared = models.BooleanField(initial=False, blank=True)
    report_display_name = models.StringField(blank=True, max_length=60)
    received_signal_name = models.StringField(blank=True)
    received_signal_value = models.StringField(blank=True)

    # ---- Bot check (Cloudflare Turnstile + honeypot) ----
    turnstile_token = models.StringField(blank=True)
    turnstile_bypass_key = models.StringField(blank=True)
    turnstile_client_host = models.StringField(blank=True)
    honeypot_intro_response = models.LongStringField(blank=True)
    honeypot_intro_triggered = models.BooleanField(initial=False)

    # ---- Personality survey (BFI-10) ----
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
        widget=widgets.RadioSelect,
    )
    stroop_2 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
        widget=widgets.RadioSelect,
    )
    stroop_3 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
        widget=widgets.RadioSelect,
    )
    stroop_4 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
        widget=widgets.RadioSelect,
    )
    stroop_5 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
        widget=widgets.RadioSelect,
    )
    stroop_6 = models.StringField(
        label='What color is this word displayed in?',
        choices=["Blue", "Red", "Green", "Yellow"], blank=True,
        widget=widgets.RadioSelect,
    )
    stroop_1_response_time = models.FloatField(blank=True)
    stroop_2_response_time = models.FloatField(blank=True)
    stroop_3_response_time = models.FloatField(blank=True)
    stroop_4_response_time = models.FloatField(blank=True)
    stroop_5_response_time = models.FloatField(blank=True)
    stroop_6_response_time = models.FloatField(blank=True)

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
# Per-subject question/condition plan
# ---------------------------------------------------------------------------

def _build_plan(participant):
    """Construct a stable 45-round plan for one participant.

    Returns (period_tasks, period_sets, round_plan). The plan is deterministic
    given the participant code (so refresh/back-navigation is stable).
    """
    rng = random.Random(f"{participant.code}-plan")

    # Choose this subject's 3 task types per the pilot config.
    tasks = list(CFG["fixed_tasks"])
    pool = list(CFG["random_pool"])
    rng.shuffle(pool)
    tasks += pool[: CFG["random_count"]]
    rng.shuffle(tasks)  # randomized assignment of tasks to periods 1/2/3
    period_tasks = tasks[:3]

    round_plan = {}
    period_sets = []
    for pi, task in enumerate(period_tasks):
        task_sets = QD.SETS[task]
        # One randomly-chosen set per difficulty, ALWAYS in ascending difficulty
        # order (easy block first, then medium, then hard) for every task type.
        chosen_set_ids = []
        for diff in ("easy", "medium", "hard"):
            candidates = [s for s in task_sets if s.startswith(diff + "_")]
            chosen_set_ids.append(rng.choice(candidates))
        period_sets.append(chosen_set_ids)
        for bi, set_id in enumerate(chosen_set_ids):
            item_ids = list(task_sets[set_id])
            rng.shuffle(item_ids)
            base = pi * C.PERIOD_LENGTH + bi * 5
            for k, item_id in enumerate(item_ids):
                rnd = base + k + 1
                diff = QD.QUESTIONS[task][item_id]["difficulty"]
                round_plan[str(rnd)] = dict(
                    task=task, item_id=item_id, set_id=set_id, difficulty=diff,
                )
    return period_tasks, period_sets, round_plan


def creating_session(subsession: Subsession):
    if subsession.round_number == 1:
        players = subsession.get_players()
        for i, p in enumerate(players):
            part = p.participant
            period_tasks, period_sets, round_plan = _build_plan(part)
            part.vars['period_tasks'] = period_tasks
            part.vars['period_sets'] = period_sets
            part.vars['round_plan'] = round_plan
            part.vars['period_task_labels'] = " \u2192 ".join(
                TASK_LABELS.get(t, t) for t in period_tasks
            )
            part.vars['stroop_plan'] = _stroop_plan(part)

            # Randomized (50/50) reference-point treatment: only this subgroup is
            # asked their self-perceived IQ score before starting. Seeded per
            # participant so it is stable and uncorrelated with the cell above.
            asked = random.Random(f"{part.code}-iqref").random() < 0.5
            part.vars['iq_reference_asked'] = asked
            p.iq_reference_asked = asked

            # Four balanced cells decorrelate the social type (quantitative vs
            # qualitative) from the block order (control-first vs social-first).
            cell = i % 4
            social_type = 'quantitative_social' if cell in (0, 1) else 'qualitative_social'
            part.vars['social_type'] = social_type

            cond_rng = random.Random(f"{part.code}-cond")
            if not CFG['use_wta']:
                # Initial pilot: 3 mandatory blocks, 1 control + 2 social, order randomized.
                conds = ['control', social_type, social_type]
                cond_rng.shuffle(conds)
                part.period_1_condition = conds[0]
                part.period_2_condition = conds[1]
                part.vars['period_3_condition'] = conds[2]
            else:
                # IQ / Main: one control + one social in periods 1-2 (control-first vs
                # social-first balanced); period 3 condition is set later from the WTA.
                control_first = cell in (0, 2)
                if control_first:
                    part.period_1_condition = 'control'
                    part.period_2_condition = social_type
                else:
                    part.period_1_condition = social_type
                    part.period_2_condition = 'control'
                # Placeholder until the WTA elicitation decides period 3 (so the
                # diagnostic bar reads "TBD" rather than a misleading "control").
                part.vars.setdefault('period_3_condition', 'TBD')

    for p in subsession.get_players():
        p.condition = get_condition(p)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def period_of_round(round_number: int) -> int:
    if round_number <= C.PERIOD_LENGTH:
        return 1
    if round_number <= 2 * C.PERIOD_LENGTH:
        return 2
    return 3


def get_condition(player: Player):
    part = player.participant
    period = period_of_round(player.round_number)
    if period == 1:
        return part.period_1_condition
    if period == 2:
        return part.period_2_condition
    return part.vars.get('period_3_condition', 'control')


def round_spec(player: Player):
    """The {task,item_id,set_id,difficulty} planned for this round."""
    return player.participant.vars['round_plan'][str(player.round_number)]


def component_for_player(player: Player) -> str:
    return TASK_IQ_COMPONENT.get(round_spec(player)['task'], 'fluid')


def iq_component_label(component: str) -> str:
    return IQ_COMPONENT_LABELS.get(component, component)


def grade_answer(task: str, item_id: str, answer) -> bool:
    item = QD.QUESTIONS[task][item_id]
    if QD.TASK_RESPONSE[task] == 'count':
        # Working memory: exact match on the reported number of red-dot squares.
        try:
            return int(str(answer).strip()) == int(item['dot_count'])
        except (TypeError, ValueError):
            return False
    return str(answer or '').strip() == str(item['correct']).strip()


def q_answer_earns_bonus(p: Player) -> bool:
    """Correct AND no tab switch on that question."""
    correct = bool(p.field_maybe_none('q_correct'))
    switched = (p.field_maybe_none('q_tab_switches') or 0) > 0
    return correct and not switched


def q_disqualified_by_switch(p: Player) -> bool:
    """Correct but a tab switch on that question stripped the bonus."""
    correct = bool(p.field_maybe_none('q_correct'))
    switched = (p.field_maybe_none('q_tab_switches') or 0) > 0
    return correct and switched


def switched_disqualified_count(player: Player, start: int, end: int) -> int:
    """# of unique questions in [start, end] that lost the bonus to a tab switch."""
    return sum(1 for p in player.in_rounds(start, end) if q_disqualified_by_switch(p))


def is_feedback_round(player: Player):
    return player.round_number in C.FEEDBACK_ROUNDS


def is_end_of_period(player: Player):
    return player.round_number in C.END_OF_PERIOD_ROUNDS


def is_third_period(player: Player):
    return player.round_number >= C.THIRD_PERIOD_START


def third_period_played(player: Player):
    """Period 3 is mandatory in the Initial pilot; WTA-gated otherwise."""
    if CFG['period3_mandatory']:
        return True
    return player.participant.vars.get('third_period_accepted', False)


def is_end_of_period_with_p3(player: Player):
    if player.round_number in C.END_OF_PERIOD_ROUNDS:
        return True
    if player.round_number == C.NUM_ROUNDS and third_period_played(player):
        return True
    return False


def block_correct(player: Player):
    """Correct answers in the current 5-question block (DB-saved rows)."""
    r = player.round_number
    block_start = ((r - 1) // 5) * 5 + 1
    total = 0
    for p in player.in_rounds(block_start, r):
        if p.field_maybe_none('q_correct'):
            total += 1
    return total


def block_correct_prior_in_block(player: Player):
    """Correct count in this block for rounds strictly before the current one."""
    r = player.round_number
    block_start = ((r - 1) // 5) * 5 + 1
    if r <= block_start:
        return 0
    total = 0
    for p in player.in_rounds(block_start, r - 1):
        if p.field_maybe_none('q_correct'):
            total += 1
    return total


def total_correct(player: Player):
    total = 0
    for p in player.in_rounds(1, player.round_number):
        if q_answer_earns_bonus(p):
            total += 1
    return total


def period_correct(player: Player):
    r = player.round_number
    if r <= C.PERIOD_LENGTH:
        start = 1
    elif r <= 2 * C.PERIOD_LENGTH:
        start = C.PERIOD_LENGTH + 1
    else:
        start = C.THIRD_PERIOD_START
    total = 0
    for p in player.in_rounds(start, r):
        if q_answer_earns_bonus(p):
            total += 1
    return total


def pilot_feedback_signals(player: Player):
    """One peer report shown on the feedback sidebar for the current block.

    Initial pilot: no received message (send-only). IQ/Main: draw a real message
    from the previous pilot for this (task, set_id); fall back to a simulated one.
    Messages are number-correct based (0-5) in all pilots.
    """
    cond = get_condition(player)
    if cond not in ('quantitative_social', 'qualitative_social'):
        return dict(type='control', name=None)

    if CFG['received_message_source'] is None:
        return dict(type='none', name=None)

    spec = round_spec(player)
    pool = received_message_pool() or {}
    set_pool = pool.get(spec['task'], {}).get(spec['set_id'], {})
    rng = random.Random(f"{player.session.code}-{player.participant.code}-{player.round_number}-recv")
    name = rng.choice(PILOT_NAMES)

    if cond == 'quantitative_social':
        entries = set_pool.get('quantitative') or []
        if entries:
            e = rng.choice(entries)
            return dict(type='quantitative', name=e.get('name') or name,
                        number=int(e.get('number', 0)))
        return dict(type='quantitative', name=name, number=rng.randint(0, 5))

    entries = set_pool.get('qualitative') or []
    if entries:
        e = rng.choice(entries)
        return dict(type='qualitative', name=e.get('name') or name,
                    emoji=e.get('emoji') or QUAL_EMOJI_NEUTRAL,
                    sentence=e.get('sentence') or '')
    # Simulated fallback.
    emoji = rng.choice(QUAL_EMOJIS)
    if emoji == QUAL_EMOJI_SMILE:
        n = rng.choice([4, 5])
    elif emoji == QUAL_EMOJI_NEUTRAL:
        n = rng.choice([2, 3])
    else:
        n = rng.choice([0, 1])
    if rng.random() < 0.5:
        sentence = rng.choice(PILOT_QUAL_SCORE_BY_EMOJI[emoji]).format(n=n)
    else:
        sentence = rng.choice(PILOT_QUAL_TEXT_BY_EMOJI[emoji])
    return dict(type='qualitative', name=name, emoji=emoji, sentence=sentence)


def experienced_conditions(player: Player):
    p1 = player.participant.period_1_condition
    p2 = player.participant.period_2_condition
    treatment = p1 if p1 != 'control' else p2
    return treatment, 'control'


def _stroop_plan(participant):
    """Per-participant Stroop plan: {period -> ordered list of 6 question dicts}.

    Randomizes (i) which fixed block appears in which period and (ii) the order
    of the six questions within each block. Keyed by str(period) so it survives
    JSON round-tripping in participant.vars.
    """
    rng = random.Random(f"{participant.code}-stroop")
    block_order = [0, 1, 2]
    rng.shuffle(block_order)
    plan = {}
    for period_idx in range(3):
        block = [dict(q) for q in STROOP_BLOCKS[block_order[period_idx]]]
        rng.shuffle(block)
        plan[str(period_idx + 1)] = block
    return plan


def stroop_block_for_round(player: Player):
    plan = player.participant.vars.get('stroop_plan')
    if not plan:
        plan = _stroop_plan(player.participant)
        player.participant.vars['stroop_plan'] = plan
    return plan[str(period_of_round(player.round_number))]


def stroop_question(player: Player, index: int):
    """The index-th (1-based) Stroop question for the player's current period."""
    return stroop_block_for_round(player)[index - 1]


def stroop_correct_count(player: Player):
    block = stroop_block_for_round(player)
    answers = [player.stroop_1, player.stroop_2, player.stroop_3,
               player.stroop_4, player.stroop_5, player.stroop_6]
    return sum(1 for i, a in enumerate(answers) if a == block[i]['color'])


def _period_index_and_qnum(round_number: int):
    if round_number <= C.PERIOD_LENGTH:
        return 1, round_number
    if round_number <= 2 * C.PERIOD_LENGTH:
        return 2, round_number - C.PERIOD_LENGTH
    return 3, round_number - 2 * C.PERIOD_LENGTH


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


BFI_PROMPTS = {
    'big5_1': "\u2026is reserved.",
    'big5_2': "\u2026is generally trusting.",
    'big5_3': "\u2026tends to be lazy.",
    'big5_4': "\u2026is relaxed, handles stress well.",
    'big5_5': "\u2026has few artistic interests.",
    'big5_6': "\u2026is outgoing, sociable.",
    'big5_7': "\u2026tends to find fault with others.",
    'big5_8': "\u2026does a thorough job.",
    'big5_9': "\u2026gets nervous easily.",
    'big5_10': "\u2026has an active imagination.",
    'competitiveness': "\u2026enjoys competing with others.",
    'big5_accuracy': "\u2026is sure that my answers to these questions describe me accurately.",
}

RSES_PROMPTS = {
    'rses_1': "On the whole, I am satisfied with myself.",
    'rses_2': "At times I think I am no good at all.",
    'rses_3': "I feel that I have a number of good qualities.",
    'rses_4': "I am able to do things as well as most other people.",
    'rses_5': "I feel I do not have much to be proud of.",
    'rses_6': "I certainly feel useless at times.",
    'rses_7': "I feel that I'm a person of worth, at least on an equal plane with others.",
    'rses_8': "I wish I could have more respect for myself.",
    'rses_9': "All in all, I am inclined to feel that I am a failure.",
    'rses_10': "I take a positive attitude toward myself.",
}


def _stable_shuffled(player: Player, suffix: str, items: list) -> list:
    rng = random.Random(f"{player.participant.code}-{suffix}")
    out = list(items)
    rng.shuffle(out)
    return out


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
    def vars_for_template(player: Player):
        shuffled_fields = _stable_shuffled(
            player, 'bfi',
            [k for k in BFI_PROMPTS.keys() if k != 'big5_accuracy'],
        )
        rows = [
            dict(field=name, prompt=BFI_PROMPTS[name])
            for name in shuffled_fields
        ]
        rows.append(dict(field='big5_accuracy', prompt=BFI_PROMPTS['big5_accuracy']))
        return dict(rows=rows)

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
    def vars_for_template(player: Player):
        shuffled_fields = _stable_shuffled(
            player, 'rses', list(RSES_PROMPTS.keys()),
        )
        rows = [
            dict(field=name, prompt=RSES_PROMPTS[name])
            for name in shuffled_fields
        ]
        return dict(rows=rows)

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
    def vars_for_template(player: Player):
        npi_fields = [f'npi_{i}' for i in range(1, 9)]
        ordered = _stable_shuffled(player, 'npi', npi_fields)
        return dict(npi_order=ordered)

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
        honeypot_raw = values.get('honeypot_intro_response') or ''
        honeypot_triggered = bool(str(honeypot_raw).strip())
        player.honeypot_intro_triggered = honeypot_triggered

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


class IQReferencePoint(Page):
    """Baseline reference point (randomized treatment): the participant's
    self-perceived IQ score, elicited before they see any task."""
    form_model = 'player'
    form_fields = ['iq_reference_score']

    @staticmethod
    def is_displayed(player: Player):
        return (
            player.round_number == 1
            and player.participant.vars.get('iq_reference_asked', False)
        )

    @staticmethod
    def error_message(player: Player, values):
        v = values.get('iq_reference_score')
        if v is None or v == '':
            return "Please move the slider to provide your estimate before continuing."


class Intro(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        period_tasks = player.participant.vars.get('period_tasks', [])
        period_components = [TASK_CONSTRUCT.get(t, t) for t in period_tasks]
        return dict(
            show_iq=CFG['show_iq'],
            has_optional_third=CFG['use_wta'],
            receives_messages=CFG['received_message_source'] is not None,
            total_questions=2 * C.PERIOD_LENGTH if CFG['use_wta'] else 3 * C.PERIOD_LENGTH,
            period_components=period_components,
            flat_payment=FLAT_PAYMENT_DISPLAY,
        )


class TaskIntro(Page):
    """Minimal task explanation + worked example, shown before each new task.

    Appears once at the start of every period (rounds 1 / 16 / 31), right after
    the Task-instructions page in period 1.
    """

    @staticmethod
    def is_displayed(player: Player):
        if player.round_number not in (1, C.PERIOD_LENGTH + 1, C.THIRD_PERIOD_START):
            return False
        if is_third_period(player):
            return third_period_played(player)
        return True

    @staticmethod
    def vars_for_template(player: Player):
        spec = round_spec(player)
        task = spec['task']
        period, _ = _period_index_and_qnum(player.round_number)
        intro = TASK_INTRO.get(task, {})
        example_image = intro.get('example_image')
        if not static_exists(example_image):
            # Real example not dropped in yet: the template shows a placeholder.
            example_image = None
        return dict(
            period=period,
            task=task,
            title=intro.get('title', TASK_LABELS.get(task, task)),
            body_html=intro.get('body_html', ''),
            example_image=example_image,
            example_answer=intro.get('example_answer', ''),
        )


class QuestionPage(Page):
    """One cognitive question (task type depends on the round's plan).

    On feedback rounds (every 5th) the page also shows an inline slide-in
    sidebar with the block summary and (in social conditions) a peer report and
    a compose-your-own panel, captured in the same form submission.
    """
    form_model = 'player'
    form_fields = [
        'q_answer',
        'q_response_time',
        'report_number',
        'report_emoji',
        'report_message',
        'report_shared',
        'report_display_name',
    ]
    timeout_seconds = QUESTION_TIMEOUT_SECONDS

    @staticmethod
    def is_displayed(player: Player):
        if is_third_period(player):
            return third_period_played(player)
        return True

    @staticmethod
    def vars_for_template(player: Player):
        spec = round_spec(player)
        task = spec['task']
        item = QD.QUESTIONS[task][spec['item_id']]
        period, q_in_period = _period_index_and_qnum(player.round_number)
        response_type = QD.TASK_RESPONSE[task]

        # Working-memory stimulus is one-and-done: mark it shown on the first
        # render so a re-render (e.g. pressing Next with no answer) won't show
        # the image again. Done server-side (not via liveSend) so it is robust
        # even when the image is cached and flashes before liveSend is ready.
        already_shown = bool(player.field_maybe_none('q_stimulus_shown'))
        if response_type == 'count' and not already_shown:
            player.q_stimulus_shown = True

        ctx = dict(
            question_number=player.round_number,
            total_questions=C.NUM_ROUNDS,
            period=period,
            question_in_period=q_in_period,
            is_feedback_round=False,
            task=task,
            response_type=response_type,
            question_prompt=TASK_PROMPT.get(task, ''),
            # Raven's / sequence stimuli pack fine detail (small option numbers,
            # long digit strings) and need more width to stay readable.
            big_image=task in ('ravens', 'sequences'),
            item=item,
            image=item.get('image'),
            is_placeholder=item.get('is_placeholder', False),
            options=item.get('options', []),
            wm_stimulus_ms=int(WM_STIMULUS_SECONDS * 1000),
            already_shown=already_shown,
            prior_answer=player.field_maybe_none('q_answer') or '',
            already_tab_switched=(player.field_maybe_none('q_tab_switches') or 0) > 0,
        )

        if is_feedback_round(player):
            cond = get_condition(player)
            signal = pilot_feedback_signals(player)
            signal_name = (signal.get('name') or '') if isinstance(signal, dict) else ''
            signal_initial = signal_name[:1].upper() if signal_name else '?'
            ctx.update(
                is_feedback_round=True,
                condition=cond,
                block_score_prior=block_correct_prior_in_block(player),
                report_options=list(range(6)),
                signal=signal,
                signal_initial=signal_initial,
                qual_emojis=QUAL_EMOJIS,
                in_treatment=cond in ('quantitative_social', 'qualitative_social'),
                is_quantitative=cond == 'quantitative_social',
                is_qualitative=cond == 'qualitative_social',
                has_received_message=isinstance(signal, dict) and signal.get('type') in ('quantitative', 'qualitative'),
            )
        return ctx

    @staticmethod
    def live_method(player: Player, data):
        if not isinstance(data, dict):
            return
        action = data.get('action')
        if action == 'track_focus_switch':
            try:
                current = int(player.field_maybe_none('q_tab_switches') or 0)
            except Exception:
                current = 0
            player.q_tab_switches = current + 1
            return {
                player.id_in_group: dict(
                    action='focus_switch_recorded',
                    count=player.q_tab_switches,
                    bonus_disqualified=True,
                )
            }
        if action == 'wm_shown':
            # The working-memory stimulus has been flashed once: lock it so a
            # re-render (e.g. after an empty submit) can't grant another look.
            player.q_stimulus_shown = True
            return
        if action == 'submit_answer':
            # Record the answer + grade it server-side so we can show the block
            # count without ever leaking the correct answer to the client.
            spec = round_spec(player)
            ans = data.get('answer') or ''
            player.q_answer = str(ans)
            player.q_correct = grade_answer(spec['task'], spec['item_id'], ans)
            count = block_correct_prior_in_block(player) + (1 if player.q_correct else 0)
            return {player.id_in_group: dict(action='block_count', count=count, block_size=5)}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        spec = round_spec(player)
        player.q_task = spec['task']
        player.q_item_id = spec['item_id']
        player.q_set_id = spec['set_id']
        player.q_difficulty = spec['difficulty']
        # Record the live condition (period-3's is only known after the WTA).
        player.condition = get_condition(player)

        if timeout_happened:
            player.q_timeout = True

        answer = player.field_maybe_none('q_answer') or ''
        if not answer:
            player.q_response_time = None
            player.q_correct = False
        else:
            player.q_correct = grade_answer(spec['task'], spec['item_id'], answer)

        # Canary: if no display name was composed, the participant never filled
        # in a report, so blank out report fields rather than store 0/defaults.
        composed_name = (player.field_maybe_none('report_display_name') or '').strip()
        if not composed_name:
            player.report_number = None
            player.report_emoji = None
            player.report_message = None
            player.report_display_name = None

        if not is_feedback_round(player):
            return

        cond = get_condition(player)
        signal = pilot_feedback_signals(player)
        if cond == 'quantitative_social':
            n = player.field_maybe_none('report_number')
            if n is not None:
                player.report_message = f"Message: I got {n} out of 5 correct."
        if cond in ('quantitative_social', 'qualitative_social'):
            player.report_display_name = (
                (player.field_maybe_none('report_display_name') or '').strip()
            )
        player.feedback_snapshot = json.dumps(dict(
            round=player.round_number,
            condition=cond,
            task=spec['task'],
            set_id=spec['set_id'],
            block_score=block_correct(player),
            signal=signal,
            sent_number=player.field_maybe_none('report_number'),
            sent_emoji=player.field_maybe_none('report_emoji'),
            sent_message=player.field_maybe_none('report_message'),
            shared=player.field_maybe_none('report_shared'),
            sent_display_name=player.field_maybe_none('report_display_name'),
        ))
        if signal.get('type') == 'quantitative':
            player.received_signal_name = signal.get('name') or ''
            player.received_signal_value = str(signal.get('number'))
        elif signal.get('type') == 'qualitative':
            player.received_signal_name = signal.get('name') or ''
            player.received_signal_value = signal.get('emoji') or ''

    @staticmethod
    def error_message(player: Player, values):
        if values.get('timeout_happened'):
            return
        if not (values.get('q_answer') or '').strip():
            return "Please answer the question before continuing."
        if not is_feedback_round(player):
            return
        cond = get_condition(player)
        if cond not in ('quantitative_social', 'qualitative_social'):
            return
        if not (values.get('report_display_name') or '').strip():
            return "Please enter the name you want to use."
        if cond == 'quantitative_social':
            rn = values.get('report_number')
            if rn is None or rn == '':
                return "Please select the number you want to report."
            return
        msg = (values.get('report_message') or '').strip()
        if not msg:
            return "Please add a short note before continuing."
        if len(msg) < 5:
            return "Please write at least 5 characters in your note."
        if not values.get('report_emoji'):
            return "Please indicate how the last 5 questions went."


class IQReadout(Page):
    """Per-period IQ estimate, shown after each block of 15 in the IQ/Main pilots."""

    @staticmethod
    def is_displayed(player: Player):
        return CFG['show_iq'] and is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        period, _ = _period_index_and_qnum(player.round_number)
        component = component_for_player(player)
        score = period_correct(player)
        iq = estimate_iq(component, score, C.PERIOD_LENGTH)
        player.iq_estimate = iq
        return dict(
            period=period,
            component=component,
            component_label=iq_component_label(component),
            iq=iq,
        )


class PerceivedPercentile(Page):
    form_model = 'player'
    form_fields = ['perceived_relative_performance']

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        period, _ = _period_index_and_qnum(player.round_number)
        return dict(period=period)

    @staticmethod
    def error_message(player: Player, values):
        v = values.get('perceived_relative_performance')
        if v is None or v == '':
            return "Please move the slider to provide your percentile estimate before continuing."


class PerceivedPercentileConfidence(Page):
    """0-100 slider for confidence in the prior percentile guess."""
    form_model = 'player'
    form_fields = ['perceived_percentile_confidence']

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        period, _ = _period_index_and_qnum(player.round_number)
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


class ColorTaskIntro(Page):
    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)


def _stroop_color_task_error(values: dict, field_name: str):
    if values.get('timeout_happened'):
        return
    v = values.get(field_name)
    if not v:
        return "Please select a color before continuing."


def _color_task_vars(player: Player, index: int):
    q = stroop_question(player, index)
    return dict(
        stroop_index=index,
        stroop_total=6,
        stroop_word=q['word'],
        stroop_color=q['color'].lower(),
    )


class ColorTask1(Page):
    form_model = 'player'
    form_fields = ['stroop_1', 'stroop_1_response_time']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        return _color_task_vars(player, 1)

    @staticmethod
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_1')

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.stroop_1_response_time = None


class ColorTask2(Page):
    form_model = 'player'
    form_fields = ['stroop_2', 'stroop_2_response_time']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        return _color_task_vars(player, 2)

    @staticmethod
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_2')

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.stroop_2_response_time = None


class ColorTask3(Page):
    form_model = 'player'
    form_fields = ['stroop_3', 'stroop_3_response_time']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        return _color_task_vars(player, 3)

    @staticmethod
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_3')

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.stroop_3_response_time = None


class ColorTask4(Page):
    form_model = 'player'
    form_fields = ['stroop_4', 'stroop_4_response_time']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        return _color_task_vars(player, 4)

    @staticmethod
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_4')

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.stroop_4_response_time = None


class ColorTask5(Page):
    form_model = 'player'
    form_fields = ['stroop_5', 'stroop_5_response_time']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        return _color_task_vars(player, 5)

    @staticmethod
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_5')

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.stroop_5_response_time = None


class ColorTask6(Page):
    form_model = 'player'
    form_fields = ['stroop_6', 'stroop_6_response_time']
    timeout_seconds = 5

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        return _color_task_vars(player, 6)

    @staticmethod
    def error_message(player: Player, values):
        return _stroop_color_task_error(values, 'stroop_6')

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.stroop_6_response_time = None


class EndOfPeriodSurvey(Page):
    form_model = 'player'
    form_fields = ['mood', 'task_enjoyment', 'payment_satisfaction']

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        period, _ = _period_index_and_qnum(player.round_number)
        if player.round_number >= C.THIRD_PERIOD_START and CFG['use_wta']:
            pay_rate = player.participant.vars.get('third_period_pay_rate', 0) or 0
        else:
            pay_rate = float(C.PAY_PER_CORRECT)
        correct = period_correct(player)
        earnings = correct * pay_rate

        r = player.round_number
        if r <= C.PERIOD_LENGTH:
            start = 1
        elif r <= 2 * C.PERIOD_LENGTH:
            start = C.PERIOD_LENGTH + 1
        else:
            start = C.THIRD_PERIOD_START
        switched = switched_disqualified_count(player, start, r)
        subtracted = switched * pay_rate

        task = round_spec(player)['task']

        rng = random.Random(f"{player.participant.code}-eop-survey")
        question_keys = ['mood', 'task_enjoyment', 'payment_satisfaction']
        rng.shuffle(question_keys)

        return dict(
            period=period,
            period_earnings=f"{earnings:.2f}",
            switched_count=switched,
            switched_subtracted=f"{subtracted:.2f}",
            task_construct=TASK_CONSTRUCT.get(task, "task"),
            question_order=question_keys,
        )

    @staticmethod
    def error_message(player: Player, values):
        if (values.get('mood') is None or values.get('task_enjoyment') is None
                or values.get('payment_satisfaction') is None):
            return "Please answer all questions before continuing."


class WTACompare(Page):
    """Two simultaneous WTA price lists (treatment vs control), end of period 2.

    Only shown in pilots that use the WTA (IQ / Main).
    """
    form_model = 'player'
    form_fields = (
        [f'wta_t_{i}' for i in range(1, len(WTA_AMOUNTS) + 1)]
        + [f'wta_c_{i}' for i in range(1, len(WTA_AMOUNTS) + 1)]
    )

    @staticmethod
    def is_displayed(player: Player):
        return CFG['use_wta'] and player.round_number == 2 * C.PERIOD_LENGTH

    @staticmethod
    def vars_for_template(player: Player):
        treatment, _ = experienced_conditions(player)

        def make_rows(prefix: str):
            rs = []
            for i, amount in enumerate(WTA_AMOUNTS, 1):
                fname = f"wta_{prefix}_{i}"
                val = player.field_maybe_none(fname) or ""
                rs.append(dict(
                    index=i,
                    amount=f"${amount:.2f}",
                    field=fname,
                    is_yes=val == "Yes",
                    is_no=val == "No",
                ))
            return rs

        with_msg_block = dict(
            kind="with_messages",
            heading="With messages",
            description=(
                "In this scenario, you are able to interact with other "
                "participants. You learn both about your performance and "
                "about theirs'."
            ),
            rows=make_rows("t"),
        )
        without_msg_block = dict(
            kind="without_messages",
            heading="Without messages",
            description=(
                "In this scenario, you are not able to interact with other "
                "participants. You learn only about your own performance."
            ),
            rows=make_rows("c"),
        )

        p1 = player.participant.period_1_condition
        if p1 == 'control':
            blocks = [without_msg_block, with_msg_block]
        else:
            blocks = [with_msg_block, without_msg_block]

        return dict(
            treatment_condition=treatment,
            blocks=blocks,
        )

    @staticmethod
    def error_message(player: Player, values):
        for i in range(1, len(WTA_AMOUNTS) + 1):
            if not values.get(f'wta_t_{i}') or not values.get(f'wta_c_{i}'):
                return "Please make a choice for every payment level in both blocks."


class SocialMediaUsage(Page):
    form_model = 'player'
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
        text = (values.get('realism_feedback') or '').strip()
        if not text:
            return "Please share your thoughts before continuing."
        if len(text) < 50:
            return (
                "Please write at least 50 characters about how the social "
                "feedback felt during the study (currently "
                f"{len(text)} characters)."
            )


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
    """Intermediate results page (after WTA, end of period 2). IQ/Main pilots only."""

    @staticmethod
    def is_displayed(player: Player):
        return CFG['use_wta'] and player.round_number == 2 * C.PERIOD_LENGTH

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

        treatment, _ = experienced_conditions(player)
        n = len(WTA_AMOUNTS)
        rng = random.Random(f"{player.session.code}-{player.participant.code}-wta")
        selected_row = rng.randint(0, n - 1)
        selected_col = rng.choice(['t', 'c'])
        selected_amount = WTA_AMOUNTS[selected_row]
        field = f'wta_{selected_col}_{selected_row + 1}'
        selected_choice = player.field_maybe_none(field) or "No"
        selected_for_retake = selected_choice == "Yes"
        if selected_col == 't':
            p3_condition = treatment
        else:
            p3_condition = 'control'

        player.participant.third_period_accepted = selected_for_retake
        player.participant.third_period_pay_rate = selected_amount if selected_for_retake else 0
        player.participant.vars['period_3_condition'] = p3_condition

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
            selected_amount=f"${selected_amount:.2f}",
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
        accepted = third_period_played(player)
        period_tasks = player.participant.vars.get('period_tasks', [])
        rate_per_correct = float(C.PAY_PER_CORRECT)
        if CFG['use_wta']:
            p3_pay_rate = player.participant.vars.get('third_period_pay_rate', 0) or 0
        else:
            p3_pay_rate = rate_per_correct

        period_ranges = [
            (1, C.PERIOD_LENGTH),
            (C.PERIOD_LENGTH + 1, 2 * C.PERIOD_LENGTH),
            (C.THIRD_PERIOD_START, C.NUM_ROUNDS),
        ]

        def bonus_correct(start, end):
            return sum(1 for p in player.in_rounds(start, end) if q_answer_earns_bonus(p))

        # One row per played task period (period 3 only if it was taken).
        task_rows = []
        question_payoff = 0.0
        for idx, (start, end) in enumerate(period_ranges):
            period_no = idx + 1
            if period_no == 3 and not accepted:
                continue
            task = period_tasks[idx] if idx < len(period_tasks) else None
            rate = p3_pay_rate if (period_no == 3 and CFG['use_wta']) else rate_per_correct
            correct = bonus_correct(start, end)
            amount = correct * rate
            question_payoff += amount
            task_rows.append(dict(
                period=period_no,
                label=TASK_LABELS.get(task, task or f"Period {period_no}"),
                correct=correct,
                rate=f"{rate:.2f}",
                amount=f"{amount:.2f}",
            ))

        # Stroop ("color task") bonus, summed over the periods it was shown.
        stroop_rounds = list(C.END_OF_PERIOD_ROUNDS)
        if accepted:
            stroop_rounds.append(C.NUM_ROUNDS)
        stroop_total = sum(stroop_correct_count(player.in_round(r)) for r in stroop_rounds)
        stroop_amount = stroop_total * float(C.PAY_PER_STROOP)

        total = question_payoff + stroop_amount
        total_payoff = cu(total)
        player.payoff = total_payoff

        # Bonus stripped by tab switching (correct answers that switched tabs).
        switched_p12 = switched_disqualified_count(player, 1, 2 * C.PERIOD_LENGTH)
        subtracted = switched_p12 * rate_per_correct
        if accepted:
            switched_p3 = switched_disqualified_count(player, C.THIRD_PERIOD_START, C.NUM_ROUNDS)
            subtracted += switched_p3 * p3_pay_rate

        return dict(
            total_payoff=total_payoff,
            task_rows=task_rows,
            question_subtotal=f"{question_payoff:.2f}",
            stroop_total=stroop_total,
            stroop_rate=f"{float(C.PAY_PER_STROOP):.2f}",
            stroop_amount=f"{stroop_amount:.2f}",
            switched_subtracted=f"{subtracted:.2f}",
            had_switch_deduction=subtracted > 0,
        )


class ProlificCompletion(Page):
    """Final screen: redirect participants back to Prolific for completion credit."""

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        return dict(prolific_url=PROLIFIC_COMPLETION_URL)


page_sequence = [
    BotCheck,
    Consent,
    IQReferencePoint,
    Intro,
    TaskIntro,
    QuestionPage,
    IQReadout,
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
    WTACompare,
    Results,
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
