from otree.api import *
import json
import os
import random
from pathlib import Path
from statistics import NormalDist

from . import questions_data as QD
from .message_vocab import is_task_specific


doc = """
Social media and well-being experiment.
Subjects complete three blocks (periods) of 15 cognitive questions each. Each
subject experiences the control condition in one block and one of two social
feedback treatments (quantitative / qualitative) in the others (mixed-subject
design, order randomized). The experiment runs in one of three pilot modes
(Initial / IQ / Main), selected with the EXPERIMENT_PILOT environment variable.
"""

# Prolific study completion redirect (participant return URL)
PROLIFIC_COMPLETION_URL = os.environ.get(
    "PROLIFIC_COMPLETION_URL",
    "https://app.prolific.com/submissions/complete?cc=C16FOI42",
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

# Flat (participation) payment shown on the instructions page.
FLAT_PAYMENT_DISPLAY = "$5.5"

# IQ reference-point page "sense of the scale" bullets. The numbers are the
# x-axis band edges shown on static/images/iq_distribution.png (the ±1 / ±2 SD
# marks of N(100, 15)), so the text lines up with the labeled ticks on the plot.
IQ_SCALE_CUTOFFS = dict(
    bottom_2=70,
    bottom_16=85,
    median=100,
    top_16=115,
    top_2=130,
)


# ---------------------------------------------------------------------------
# Pilot mode (the three switchable modes)
# ---------------------------------------------------------------------------
# Switch the active pilot with the EXPERIMENT_PILOT env var: "initial" | "iq" | "main".
PILOT = (os.environ.get("EXPERIMENT_PILOT", "initial") or "initial").strip().lower()
if PILOT not in ("initial", "iq", "main"):
    PILOT = "initial"

PILOT_CONFIG = {
    # Initial pilot: sequences (always) + working memory + Raven's; number-correct
    # feedback only (no IQ); send messages but receive none; all three blocks
    # mandatory (no WTA). Spatial (shape_rotation) is retired.
    "initial": dict(
        fixed_tasks=["sequences"],
        random_pool=["working_memory", "ravens"],
        random_count=2,
        show_iq=False,
        received_message_source=None,
        iq_distribution_source=None,
        use_wta=False,
        period3_mandatory=True,
    ),
    # IQ pilot: numerical + working memory + Raven's; number-correct per 5 + IQ
    # after 15 (normed against the Initial pilot); receive Initial-pilot messages
    # on mid-period blocks only; 3rd period optional via WTA.
    "iq": dict(
        fixed_tasks=["sequences", "working_memory", "ravens"],
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
        fixed_tasks=["sequences", "working_memory", "ravens"],
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
    "spatial": "spatial reasoning",
    "fluid": "abstract reasoning",
    "working_memory": "working memory",
    "numerical": "numerical reasoning",
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


def task_iq_title(task: str) -> str:
    """Title-cased IQ component for page titles, e.g. 'Abstract Reasoning IQ'."""
    base = TASK_LABELS.get(task, "IQ")
    titled = " ".join(w.capitalize() for w in base.split())
    return f"{titled} IQ"

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
            "the number of squares that have red dots. "
            "This tests the <strong style=\"color:darkred;\">working memory</strong> "
            "component of your IQ."
        ),
        example_note=(
            "During the real task, you will have "
            "<strong style=\"color:darkred;\">1.7 seconds</strong> to look at each pattern."
        ),
        example_image="examples/working_memory.png",
        example_prompt="How many squares have red dots?",
        example_response_type="count",
        example_correct="3",
        example_answer=(
            "In this example, there are <strong style=\"color:darkred;\">3</strong> "
            "squares with red dots."
        ),
    ),
    "sequences": dict(
        title="Numerical reasoning",
        body_html=(
            "Your task in this period is to <strong style=\"color:darkred;\">predict the "
            "next number</strong> that follows in a given sequence. This tests the "
            "<strong style=\"color:darkred;\">numerical reasoning</strong> component of your IQ."
        ),
        example_image="examples/sequences.png",
        example_prompt="Which number completes the sequence?",
        example_response_type="mc",
        example_options=["A", "B", "C", "D"],
        example_correct="B",
        example_answer=(
            "<strong style=\"color:darkred;\">B) 6</strong> completes the sequence."
        ),
    ),
    "shape_rotation": dict(
        title="Spatial reasoning",
        body_html=(
            "The top row shows a shape before and after rotation. Your task is to "
            "apply the <strong style=\"color:darkred;\">same rotation</strong> to "
            "another shape. This tests the "
            "<strong style=\"color:darkred;\">spatial reasoning</strong> component of your IQ."
        ),
        example_image="examples/shape_rotation.png",
        example_prompt="Which option shows the correctly rotated shape?",
        example_response_type="mc",
        example_options=["A", "B", "C", "D", "E"],
        example_correct="D",
        example_answer="Option <strong style=\"color:darkred;\">D</strong> is the correctly rotated shape.",
    ),
    "ravens": dict(
        title="Abstract reasoning",
        body_html=(
            "Your task in this period is to choose the image that "
            "<strong style=\"color:darkred;\">completes the pattern</strong>. This tests the "
            "<strong style=\"color:darkred;\">abstract reasoning</strong> component of your IQ."
        ),
        # C8 (excluded from the live bank); answer-key option 7 = the 7th
        # lettered choice (G), matching the A-H labels printed on the image.
        example_image="examples/ravens.jpg",
        example_prompt="Which image completes the pattern?",
        example_response_type="mc",
        example_options=["A", "B", "C", "D", "E", "F", "G", "H"],
        example_correct="G",
        example_answer="Image <strong style=\"color:darkred;\">G</strong> completes the pattern.",
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


def _flatten_message_pool(pool: dict) -> dict:
    """Flatten [task][set_id][kind] into {kind: [entries]} for a portable draw.

    Messages are served at random from the whole pool rather than matched to the
    participant's own (task, set_id), so qualitative entries naming task content
    are dropped: they cannot truthfully travel to someone on a different task.
    Each surviving entry keeps its origin so we can record what was shown.
    Non-dict values (e.g. the ``_README`` key in the data files) are skipped.
    """
    flat = {'quantitative': [], 'qualitative': []}
    for task, sets in (pool or {}).items():
        if not isinstance(sets, dict):
            continue
        for set_id, pools in sets.items():
            if not isinstance(pools, dict):
                continue
            for e in pools.get('quantitative') or []:
                flat['quantitative'].append(
                    dict(e, source_task=task, source_set_id=set_id)
                )
            for e in pools.get('qualitative') or []:
                if is_task_specific(e.get('sentence') or ''):
                    continue
                flat['qualitative'].append(
                    dict(e, source_task=task, source_set_id=set_id)
                )
    return flat


def received_message_pool():
    """Portable messages from the previous pilot, keyed [quant|qual]."""
    src = CFG["received_message_source"]
    if not src:
        return None
    if src not in _MESSAGE_CACHE:
        raw = _load_json(f"messages_{src}.json") or {}
        _MESSAGE_CACHE[src] = _flatten_message_pool(raw)
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
    NAME_IN_URL = 'cognitive_tasks'
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
    PAY_PER_STROOP = cu(0.05)
    # Bonus for guessing your performance percentile within 10 points (per period).
    PAY_PER_PERCENTILE = cu(0.25)
    # Bonus for baseline IQ reference-point guess within 10 points (treatment subgroup).
    PAY_IQ_REFERENCE_GUESS = cu(0.50)
    # Study has up to 3 end-of-period percentile elicitations (all pilots).
    NUM_PERCENTILE_GUESS_PERIODS = 3
    # Max deferred bonus from IQ + percentile guesses; fixed for all participants/pilots.
    GUESS_BONUS_MAX = PAY_IQ_REFERENCE_GUESS + NUM_PERCENTILE_GUESS_PERIODS * PAY_PER_PERCENTILE


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # ---- Consent ----
    consent = models.BooleanField(label="")
    llm_rule_confirm = models.BooleanField(label="")

    # ---- Prolific ID (elicited after consent, same as cd_intake_survey) ----
    prolific_id = models.StringField(
        label="Please enter your unique Prolific ID below."
    )

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
    # Seconds from page load to clicking Next (form submit).
    q_response_time = models.FloatField(blank=True)
    feedback_snapshot = models.LongStringField(blank=True)

    # ---- Per-period IQ readout (IQ / Main pilots only) ----
    iq_estimate = models.IntegerField(blank=True)

    # ---- Per-block report a participant might send to another participant ----
    # report_number stores the number-correct (0-5) the participant chooses to report.
    report_number = models.IntegerField(min=0, max=5, blank=True)
    # report_iq stores the reported IQ score (quantitative_social IQ feedback).
    # Bounds match the reference-point slider (60-140).
    report_iq = models.IntegerField(min=60, max=140, blank=True, label="")
    # Overall (cross-component) IQ readout + optional message after all periods.
    global_iq_estimate = models.IntegerField(blank=True)
    global_report_iq = models.IntegerField(min=60, max=140, blank=True, label="")
    global_report_emoji = models.StringField(blank=True)
    global_report_message = models.StringField(blank=True, max_length=140)
    global_report_shared = models.BooleanField(blank=True)
    global_report_edit_back_count = models.IntegerField(initial=0, blank=True)
    global_report_compose_history = models.LongStringField(blank=True)
    report_emoji = models.StringField(blank=True)
    report_message = models.StringField(blank=True, max_length=140)
    report_shared = models.BooleanField(blank=True)
    report_display_name = models.StringField(blank=True, max_length=60)
    # Compose-step audit trail (social feedback sidebars): prior drafts, edit-back clicks.
    report_edit_back_count = models.IntegerField(initial=0, blank=True)
    report_compose_history = models.LongStringField(blank=True)
    # Username chosen once on the Further-instructions page (round 1) and reused
    # for every message the participant composes in the feedback sidebars.
    display_name = models.StringField(blank=True, max_length=60, label="")
    received_signal_name = models.StringField(blank=True)
    received_signal_value = models.StringField(blank=True)
    # Exact text shown to the participant, plus where the message came from
    # (messages are drawn at random from the whole portable pool, so the origin
    # task/set is not the participant's own). 'simulated' when the pool was empty.
    received_signal_text = models.StringField(blank=True, max_length=200)
    received_signal_source = models.StringField(blank=True, max_length=60)

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
    self_knowledge = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
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
    # Extra preference / social-comparison items on the BFI page.
    pref_risk = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    pref_patience = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    pref_trust = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    pref_altruism = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    pref_reciprocity = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    pref_punish = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    pref_share_success = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    pref_share_fail = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    pref_compare = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")
    pref_dislike_brag = models.IntegerField(choices=BFI_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True, label="")

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
    performance_satisfaction = models.IntegerField(
        choices=LIKERT_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True,
        label="",
    )
    mood = models.IntegerField(
        choices=MOOD_CHOICES, widget=widgets.RadioSelectHorizontal, blank=True,
        label="",
    )

    # ---- Confidence in percentile estimate (0-100 slider) ----
    perceived_percentile_confidence = models.IntegerField(min=0, max=100, blank=True, label="")

    # ---- Overall task effort (0-100 slider), after optional/mandatory period 3 ----
    task_effort = models.IntegerField(min=0, max=100, blank=True, label="")

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
    taken_iq_test_before = models.StringField(
        choices=[["Yes", "Yes"], ["No", "No"]],
        widget=widgets.RadioSelect,
        blank=True,
        label="Have you taken an IQ test before?",
    )

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
    # Writing motives (click-all-that-apply), after the open-ended experience page.
    write_well_show = models.BooleanField(blank=True, initial=False)
    write_well_downplay = models.BooleanField(blank=True, initial=False)
    write_poor_honest = models.BooleanField(blank=True, initial=False)
    write_poor_exaggerate = models.BooleanField(blank=True, initial=False)
    write_peer_well_up = models.BooleanField(blank=True, initial=False)
    write_peer_well_down = models.BooleanField(blank=True, initial=False)
    write_peer_poor_up = models.BooleanField(blank=True, initial=False)
    write_peer_poor_down = models.BooleanField(blank=True, initial=False)
    write_match_tone = models.BooleanField(blank=True, initial=False)
    write_none = models.BooleanField(blank=True, initial=False)
    # Sharing motives (click-all-that-apply), after the writing-motives page.
    share_well_positive = models.BooleanField(blank=True, initial=False)
    share_well_withhold = models.BooleanField(blank=True, initial=False)
    share_poor_positive = models.BooleanField(blank=True, initial=False)
    share_poor_withhold = models.BooleanField(blank=True, initial=False)
    share_peer_well_up = models.BooleanField(blank=True, initial=False)
    share_peer_well_down = models.BooleanField(blank=True, initial=False)
    share_peer_poor_up = models.BooleanField(blank=True, initial=False)
    share_peer_poor_down = models.BooleanField(blank=True, initial=False)
    share_helpful = models.BooleanField(blank=True, initial=False)
    share_none = models.BooleanField(blank=True, initial=False)
    # Message impacts (click-all-that-apply), after the sharing-motives page.
    impact_recv_mood = models.BooleanField(blank=True, initial=False)
    impact_recv_sat = models.BooleanField(blank=True, initial=False)
    impact_recv_effort = models.BooleanField(blank=True, initial=False)
    impact_send_mood = models.BooleanField(blank=True, initial=False)
    impact_send_sat = models.BooleanField(blank=True, initial=False)
    impact_send_effort = models.BooleanField(blank=True, initial=False)
    impact_none = models.BooleanField(blank=True, initial=False)

    # Tools used on the cognitive questions (unpaid; does not affect approval).
    tool_pen_paper = models.BooleanField(blank=True, initial=False)
    tool_calculator = models.BooleanField(blank=True, initial=False)
    tool_ai = models.BooleanField(blank=True, initial=False)
    tool_cellphone_camera = models.BooleanField(blank=True, initial=False)
    tool_search_engine = models.BooleanField(blank=True, initial=False)
    tool_ask_someone_else = models.BooleanField(blank=True, initial=False)
    tool_none = models.BooleanField(blank=True, initial=False)

    realism_feedback = models.LongStringField(
        label="",
        blank=True,
    )

    # ---- Final free-text comments (optional) ----
    comments = models.LongStringField(
        label="Do you have any additional thoughts or comments about this study that you would like to share with us?",
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
        # One randomly-chosen set per difficulty, presented in a fixed difficulty
        # order. Every task (including working memory) ramps easy -> medium -> hard.
        diff_order = ("easy", "medium", "hard")
        chosen_set_ids = []
        for diff in diff_order:
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


def _peer_message_time(rng: random.Random) -> str:
    """Plausible posted-at time for a peer message (stable per seeded draw)."""
    hour = rng.randint(9, 20)
    minute = rng.randint(0, 59)
    h12 = hour % 12 or 12
    suffix = 'AM' if hour < 12 else 'PM'
    return f"{h12}:{minute:02d} {suffix}"


def pilot_feedback_signals(player: Player):
    """One peer report shown on the feedback sidebar for the current block.

    Initial pilot: no received message (send-only). IQ/Main: draw a message
    uniformly at random from the previous pilot's portable pool, independent of
    the participant's own task and set; fall back to a simulated one only when
    the pool is empty. Messages are number-correct based (0-5) in all pilots.
    """
    cond = get_condition(player)
    if cond not in ('quantitative_social', 'qualitative_social'):
        return dict(type='control', name=None)

    if CFG['received_message_source'] is None:
        return dict(type='none', name=None)

    pool = received_message_pool() or {}
    rng = random.Random(f"{player.session.code}-{player.participant.code}-{player.round_number}-recv")
    name = rng.choice(PILOT_NAMES)

    if cond == 'quantitative_social':
        entries = pool.get('quantitative') or []
        if entries:
            e = rng.choice(entries)
            return dict(type='quantitative', name=e.get('name') or name,
                        number=int(e.get('number', 0)),
                        source_task=e.get('source_task'),
                        source_set_id=e.get('source_set_id'),
                        time=e.get('time') or _peer_message_time(rng))
        return dict(type='quantitative', name=name, number=rng.randint(0, 5),
                    simulated=True,
                    time=_peer_message_time(rng))

    entries = pool.get('qualitative') or []
    if entries:
        e = rng.choice(entries)
        return dict(type='qualitative', name=e.get('name') or name,
                    emoji=e.get('emoji') or QUAL_EMOJI_NEUTRAL,
                    sentence=e.get('sentence') or '',
                    source_task=e.get('source_task'),
                    source_set_id=e.get('source_set_id'),
                    time=e.get('time') or _peer_message_time(rng))
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
    return dict(type='qualitative', name=name, emoji=emoji, sentence=sentence,
                simulated=True, time=_peer_message_time(rng))


def pilot_iq_feedback_signal(player: Player):
    """Peer IQ message for end-of-period IQ feedback.

    We do not show a received peer IQ message here: there is no real period-level
    peer IQ pool, and simulated messages looked fake. Compose/send still proceeds.
    """
    cond = get_condition(player)
    if cond not in ('quantitative_social', 'qualitative_social'):
        return dict(type='control', name=None)
    if CFG['received_message_source'] is None:
        return dict(type='none', name=None)
    return dict(type='none', name=None)


def global_iq_for_player(player: Player) -> int:
    """Average of period IQ estimates across completed task periods.

    Before the WTA (period 3 not yet decided), only periods 1 and 2 contribute.
    """
    iqs = []
    for r in C.END_OF_PERIOD_ROUNDS:
        if r > player.round_number:
            break
        p = player.in_round(r)
        iq = p.field_maybe_none('iq_estimate')
        if iq is not None:
            iqs.append(int(iq))
    if third_period_played(player) and player.round_number >= C.NUM_ROUNDS:
        p = player.in_round(C.NUM_ROUNDS)
        iq = p.field_maybe_none('iq_estimate')
        if iq is not None:
            iqs.append(int(iq))
    if not iqs:
        # Fallback: map total correct on completed questions via overall table.
        n = 0
        max_q = 0
        for start, end, needed in (
            (1, C.PERIOD_LENGTH, True),
            (C.PERIOD_LENGTH + 1, 2 * C.PERIOD_LENGTH, True),
            (C.THIRD_PERIOD_START, C.NUM_ROUNDS, third_period_played(player)),
        ):
            if not needed:
                continue
            max_q += C.PERIOD_LENGTH
            n += sum(1 for p in player.in_rounds(start, end) if p.field_maybe_none('q_correct'))
        return estimate_iq('overall', n, max_q or C.PERIOD_LENGTH)
    return int(round(sum(iqs) / len(iqs)))


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
    'self_knowledge': "\u2026knows himself/herself well.",
    'competitiveness': "\u2026enjoys competing with others.",
    'pref_risk': "\u2026is generally willing to take risks.",
    'pref_patience': (
        "\u2026is generally willing to give up something today in order to "
        "benefit from that in the future."
    ),
    'pref_trust': (
        "\u2026assumes that people have only the best intentions, as long as "
        "I am not convinced otherwise."
    ),
    'pref_altruism': (
        "\u2026is generally willing to share with others without expecting "
        "anything in return when it comes to charity."
    ),
    'pref_reciprocity': (
        "\u2026is generally willing to return a favor that someone does for me."
    ),
    'pref_punish': (
        "\u2026is generally willing to punish unfair behavior even if this is costly."
    ),
    'pref_share_success': "\u2026likes to share my successes with others.",
    'pref_share_fail': "\u2026likes to share my failures with others.",
    'pref_compare': "\u2026often compares myself with others.",
    'pref_dislike_brag': "\u2026dislikes when others talk about their successes.",
    'big5_accuracy': "\u2026is sure that my answers to these questions describe me accurately.",
}

BFI_CORE_FIELDS = [
    'big5_1', 'big5_2', 'big5_3', 'big5_4', 'big5_5',
    'big5_6', 'big5_7', 'big5_8', 'big5_9', 'big5_10',
    'self_knowledge', 'competitiveness',
    'pref_risk', 'pref_patience', 'pref_trust', 'pref_altruism',
    'pref_reciprocity', 'pref_punish', 'pref_share_success',
    'pref_share_fail', 'pref_compare', 'pref_dislike_brag',
]

# Parallel click-all-that-apply lists (9 substantive + none) for the experience pages.
# Slots 1-4: own performance (well/poor × positive/withhold); 5-6: peer performance;
# 7: social consideration; 8: low effort; 9: not affected; 10: none.
WRITING_MOTIVES = [
    dict(
        field='write_well_show',
        text=(
            "When I did well, I tended to write positively about my performance because I "
            "wanted other participants to see that I had done well."
        ),
        is_none=False,
    ),
    dict(
        field='write_well_downplay',
        text=(
            "When I did well, I tended to downplay my performance because I did not want to "
            "seem like I was bragging."
        ),
        is_none=False,
    ),
    dict(
        field='write_poor_honest',
        text="When I did poorly, I tended to be honest about struggling.",
        is_none=False,
    ),
    dict(
        field='write_poor_exaggerate',
        text="When I did poorly, I tended to exaggerate how well I did.",
        is_none=False,
    ),
    dict(
        field='write_peer_well_up',
        text=(
            "When another participant said they did well, I was more likely to write "
            "positively about my own performance."
        ),
        is_none=False,
    ),
    dict(
        field='write_peer_well_down',
        text=(
            "When another participant said they did well, I was less likely to write "
            "positively about my own performance."
        ),
        is_none=False,
    ),
    dict(
        field='write_peer_poor_up',
        text=(
            "When another participant said they did poorly, I was more likely to write "
            "positively about my own performance."
        ),
        is_none=False,
    ),
    dict(
        field='write_peer_poor_down',
        text=(
            "When another participant said they did poorly, I was less likely to write "
            "positively about my own performance."
        ),
        is_none=False,
    ),
    dict(
        field='write_match_tone',
        text=(
            "I tried to match the tone or style of messages I had received from other "
            "participants."
        ),
        is_none=False,
    ),
    dict(
        field='write_none',
        text="None of these apply to me.",
        is_none=True,
    ),
]

SHARING_MOTIVES = [
    dict(
        field='share_well_positive',
        text=(
            "When I did well, I tended to share because I wanted other participants to see "
            "that I had done well."
        ),
        is_none=False,
    ),
    dict(
        field='share_well_withhold',
        text=(
            "When I did well, I tended to hold back because I did not want to seem like I "
            "was bragging."
        ),
        is_none=False,
    ),
    dict(
        field='share_poor_positive',
        text=(
            "When I did poorly, I tended to share because I wanted to reassure other "
            "participants."
        ),
        is_none=False,
    ),
    dict(
        field='share_poor_withhold',
        text=(
            "When I did poorly, I tended to hold back because I did not want other "
            "participants to see that I had done poorly."
        ),
        is_none=False,
    ),
    dict(
        field='share_peer_well_up',
        text=(
            "When another participant said they did well, I was more likely to share my own "
            "performance."
        ),
        is_none=False,
    ),
    dict(
        field='share_peer_well_down',
        text=(
            "When another participant said they did well, I was less likely to share my own "
            "performance."
        ),
        is_none=False,
    ),
    dict(
        field='share_peer_poor_up',
        text=(
            "When another participant said they did poorly, I was more likely to share my "
            "own performance."
        ),
        is_none=False,
    ),
    dict(
        field='share_peer_poor_down',
        text=(
            "When another participant said they did poorly, I was less likely to share my "
            "own performance."
        ),
        is_none=False,
    ),
    dict(
        field='share_helpful',
        text=(
            "I tended to share when I thought my message would be helpful or relatable to "
            "other participants."
        ),
        is_none=False,
    ),
    dict(
        field='share_none',
        text="None of these apply to me.",
        is_none=True,
    ),
]

# Receiving / sending × mood / satisfaction / effort (6 + none).
# The two activity blocks are shuffled per participant on the impacts page.
_MESSAGE_IMPACT_OUTCOMES = (
    ('mood', 'my mood'),
    ('sat', 'how satisfied I was with my performance'),
    ('effort', 'how hard I tried on subsequent blocks'),
)


def _message_impact_block(key: str, heading: str, prefix: str) -> dict:
    return dict(
        key=key,
        heading=heading,
        items=[
            dict(field=f'{prefix}_{suffix}', text=text, is_none=False)
            for suffix, text in _MESSAGE_IMPACT_OUTCOMES
        ],
    )


MESSAGE_IMPACT_RECV_BLOCK = _message_impact_block(
    'recv',
    'Receiving messages from other participants affected',
    'impact_recv',
)
MESSAGE_IMPACT_SEND_BLOCK = _message_impact_block(
    'send',
    'Sending messages affected',
    'impact_send',
)
MESSAGE_IMPACT_BLOCKS = (
    MESSAGE_IMPACT_RECV_BLOCK,
    MESSAGE_IMPACT_SEND_BLOCK,
)
MESSAGE_IMPACT_NONE = dict(
    field='impact_none',
    text="None of these apply to me.",
    is_none=True,
)
MESSAGE_IMPACTS = (
    MESSAGE_IMPACT_RECV_BLOCK['items']
    + MESSAGE_IMPACT_SEND_BLOCK['items']
    + [MESSAGE_IMPACT_NONE]
)

EXPERIENCE_PAGE_KEYS = ('writing', 'sharing', 'impacts')
EXPERIENCE_PAGE_META = {
    'writing': dict(motives=WRITING_MOTIVES),
    'sharing': dict(motives=SHARING_MOTIVES),
    'impacts': dict(motives=MESSAGE_IMPACTS),
}

IQ_REPORT_MIN = 60
IQ_REPORT_MAX = 140


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
    form_fields = BFI_CORE_FIELDS + ['big5_accuracy']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        shuffled_fields = _stable_shuffled(player, 'bfi', list(BFI_CORE_FIELDS))
        rows = [
            dict(field=name, prompt=BFI_PROMPTS[name])
            for name in shuffled_fields
        ]
        rows.append(dict(field='big5_accuracy', prompt=BFI_PROMPTS['big5_accuracy']))
        return dict(rows=rows)

    @staticmethod
    def error_message(player: Player, values):
        fields = BFI_CORE_FIELDS + ['big5_accuracy']
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
    form_fields = ['age', 'gender', 'education', 'taken_iq_test_before']

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
        if not values.get('taken_iq_test_before'):
            return "Please indicate whether you have taken an IQ test before."


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


class ProlificID(Page):
    """Elicit and record the participant's Prolific ID (round 1 only)."""
    form_model = 'player'
    form_fields = ['prolific_id']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def error_message(player: Player, values):
        prolific_id = (values.get('prolific_id') or '').strip()
        if len(prolific_id) != 24:
            return "Please enter your Prolific ID exactly as shown on Prolific (24 characters)."

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        pid = (player.field_maybe_none('prolific_id') or '').strip()
        if pid:
            # Keep participant.label in sync for matching Prolific submissions.
            player.participant.label = pid


class IQReferencePoint(Page):
    """Before-you-begin overview (all participants) plus baseline IQ reference-point
    elicitation for the randomized treatment subgroup."""
    form_model = 'player'
    form_fields = ['iq_reference_score']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        period_tasks = player.participant.vars.get('period_tasks', [])
        period_components = [TASK_CONSTRUCT.get(t, t) for t in period_tasks]
        asked = player.participant.vars.get('iq_reference_asked', False)
        return dict(
            show_iq=CFG['show_iq'],
            iq_reference_asked=asked,
            has_optional_third=CFG['use_wta'],
            total_questions=2 * C.PERIOD_LENGTH if CFG['use_wta'] else 3 * C.PERIOD_LENGTH,
            period_components=period_components,
            flat_payment=FLAT_PAYMENT_DISPLAY,
            iq_scale=IQ_SCALE_CUTOFFS,
        )

    @staticmethod
    def error_message(player: Player, values):
        if not player.participant.vars.get('iq_reference_asked', False):
            return
        v = values.get('iq_reference_score')
        if v is None or v == '':
            return "Please move the slider to provide your estimate before continuing."


class Intro(Page):
    form_model = 'player'
    form_fields = ['display_name']

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

    @staticmethod
    def error_message(player: Player, values):
        if not (values.get('display_name') or '').strip():
            return "Please enter the username you want to use."

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        name = (player.field_maybe_none('display_name') or '').strip()
        player.display_name = name
        player.participant.vars['display_name'] = name


class TaskIntro(Page):
    """Minimal task explanation + worked example, shown before each new task.

    Appears once at the start of every period (rounds 1 / 16 / 31), right after
    the Task-instructions page in period 1. Participants must answer the
    interactive example and click Check before Next is accepted (tracked in
    participant.vars via liveSend).
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
        # Working memory stimuli are only shown for ~1.7 s, so any first-load
        # delay is very visible. Preload every image in the task's pool while
        # the participant reads the example page.
        preload_images = []
        if task == 'working_memory':
            preload_images = [
                item['image']
                for item in QD.QUESTIONS.get('working_memory', {}).values()
                if item.get('image') and not item.get('is_placeholder')
            ]
        # Fresh gate each time this page is shown.
        player.participant.vars['task_intro_checked'] = False
        return dict(
            period=period,
            task=task,
            title=intro.get('title', TASK_LABELS.get(task, task)),
            body_html=intro.get('body_html', ''),
            example_note=intro.get('example_note', ''),
            example_image=example_image,
            example_answer=intro.get('example_answer', ''),
            example_prompt=intro.get('example_prompt', ''),
            example_response_type=intro.get('example_response_type', ''),
            example_options=intro.get('example_options', []),
            example_correct=str(intro.get('example_correct', '')),
            big_image=task in ('ravens', 'sequences'),
            requires_example_check=bool(intro.get('example_response_type')),
            requires_example_check_js='true' if intro.get('example_response_type') else 'false',
            preload_images=preload_images,
        )

    @staticmethod
    def live_method(player: Player, data):
        if isinstance(data, dict) and data.get('action') == 'example_checked':
            player.participant.vars['task_intro_checked'] = True
            return {player.id_in_group: dict(action='example_checked')}

    @staticmethod
    def error_message(player: Player, values):
        spec = round_spec(player)
        intro = TASK_INTRO.get(spec['task'], {})
        if not intro.get('example_response_type'):
            return
        if player.participant.vars.get('task_intro_checked'):
            return
        return (
            "Please answer the example and click Check answer before continuing."
        )


class QuestionPage(Page):
    """One cognitive question (task type depends on the round's plan).

    On feedback rounds (every 5th) the block summary and peer-message step are
    shown on the separate, untimed ``BlockFeedback`` page that immediately
    follows this one. Keeping them apart means this page's countdown can never
    run behind an open overlay and, crucially, that a page refresh can never
    let the participant skip the feedback (a refresh just reloads the untimed
    ``BlockFeedback`` page instead of auto-advancing on an expired timer).
    """
    form_model = 'player'
    form_fields = [
        'q_answer',
        'q_response_time',
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

    @staticmethod
    def error_message(player: Player, values):
        if values.get('timeout_happened'):
            return
        if not (values.get('q_answer') or '').strip():
            return "Please answer the question before continuing."


class BlockFeedback(Page):
    """Block performance summary + (in social conditions) the received peer
    message and the compose-your-own-message step.

    This is its own page, deliberately **without** a timer, and appears right
    after every feedback-round ``QuestionPage``. Because there is no timeout, a
    page refresh simply reloads this page (oTree never auto-advances), so the
    participant can no longer skip the summary or the message step by
    refreshing while it is on screen.
    """
    form_model = 'player'
    form_fields = [
        'report_number',
        'report_emoji',
        'report_message',
        'report_shared',
        'report_edit_back_count',
        'report_compose_history',
    ]

    @staticmethod
    def is_displayed(player: Player):
        if is_third_period(player) and not third_period_played(player):
            return False
        if CFG['show_iq']:
            # In IQ/Main pilots, end-of-period feedback rounds (15/30/45) show
            # only the IQ sidebar (IQFeedback); BlockFeedback covers mid-period
            # feedback rounds only.
            return (
                is_feedback_round(player)
                and player.round_number not in C.END_OF_PERIOD_ROUNDS
                and player.round_number != C.NUM_ROUNDS
            )
        return is_feedback_round(player)

    @staticmethod
    def vars_for_template(player: Player):
        spec = round_spec(player)
        task = spec['task']
        item = QD.QUESTIONS[task][spec['item_id']]
        period, q_in_period = _period_index_and_qnum(player.round_number)
        response_type = QD.TASK_RESPONSE[task]
        prior_answer = str(player.field_maybe_none('q_answer') or '')
        cond = get_condition(player)
        signal = pilot_feedback_signals(player)
        signal_name = (signal.get('name') or '') if isinstance(signal, dict) else ''
        signal_initial = signal_name[:1].upper() if signal_name else '?'
        return dict(
            condition=cond,
            block_score=block_correct(player),
            report_options=list(range(6)),
            display_name=player.participant.vars.get('display_name', ''),
            signal=signal,
            signal_initial=signal_initial,
            qual_emojis=QUAL_EMOJIS,
            in_treatment=cond in ('quantitative_social', 'qualitative_social'),
            is_quantitative=cond == 'quantitative_social',
            is_qualitative=cond == 'qualitative_social',
            has_received_message=isinstance(signal, dict) and signal.get('type') in ('quantitative', 'qualitative'),
            task_construct=TASK_CONSTRUCT.get(task, "task"),
            iq_component_title=task_iq_title(task),
            # Read-only backdrop: re-render the question they just completed so
            # the summary looks like a popup over it. Purely cosmetic; no form.
            period=period,
            question_in_period=q_in_period,
            task=task,
            response_type=response_type,
            question_prompt=TASK_PROMPT.get(task, ''),
            big_image=task in ('ravens', 'sequences'),
            item=item,
            image=item.get('image'),
            is_placeholder=item.get('is_placeholder', False),
            prior_answer=prior_answer,
            # Pre-mark the participant's chosen option so the read-only backdrop
            # can highlight it (oTree's template engine has no stringformat).
            option_rows=[
                dict(value=o, selected=(str(o) == prior_answer))
                for o in item.get('options', [])
            ],
        )

    @staticmethod
    def error_message(player: Player, values):
        cond = get_condition(player)
        if cond not in ('quantitative_social', 'qualitative_social'):
            return
        if cond == 'quantitative_social':
            rn = values.get('report_number')
            if rn is None or rn == '':
                return "Please type how many out of 5 you got correct."
        else:
            msg = (values.get('report_message') or '').strip()
            if not msg:
                return "Please add a short note before continuing."
            if len(msg) < 5:
                return "Please write at least 5 characters in your note."
            if not values.get('report_emoji'):
                return "Please indicate how you feel."
        if values.get('report_shared') is None:
            return "Please choose whether to share your message."

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        spec = round_spec(player)

        cond = get_condition(player)
        signal = pilot_feedback_signals(player)
        username = (player.participant.vars.get('display_name') or '').strip()
        if cond in ('quantitative_social', 'qualitative_social'):
            # Name comes from the username chosen on the Further-instructions page.
            player.report_display_name = username
            if cond == 'quantitative_social':
                n = player.field_maybe_none('report_number')
                if n is not None:
                    construct = TASK_CONSTRUCT.get(spec['task'], 'these')
                    player.report_message = (
                        f"I got {n} out of 5 {construct} questions in this block correct."
                    )
        else:
            # Control: no message composed; keep report fields blank.
            player.report_number = None
            player.report_emoji = None
            player.report_message = None
            player.report_display_name = None
            player.report_edit_back_count = 0
            player.report_compose_history = ''
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
            edit_back_count=player.field_maybe_none('report_edit_back_count') or 0,
            compose_history=player.field_maybe_none('report_compose_history') or '',
        ))
        if signal.get('type') in ('quantitative', 'qualitative'):
            player.received_signal_name = signal.get('name') or ''
            if signal.get('type') == 'quantitative':
                n = signal.get('number')
                player.received_signal_value = str(n)
                player.received_signal_text = f"I got {n} out of 5 correct."
            else:
                player.received_signal_value = signal.get('emoji') or ''
                player.received_signal_text = (signal.get('sentence') or '')[:200]
            if signal.get('simulated'):
                player.received_signal_source = 'simulated'
            else:
                player.received_signal_source = (
                    f"{signal.get('source_task') or '?'}/"
                    f"{signal.get('source_set_id') or '?'}"
                )[:60]


class IQFeedback(Page):
    """End-of-period IQ feedback popup (IQ / Main pilots), mirroring the
    BlockFeedback sidebar look. The estimated IQ score is the hero; in social
    conditions the participant composes an IQ-based message (after seeing our
    estimate) and receives a simulated peer IQ message.

    Like BlockFeedback, this page has no timer and is refresh-proof.
    """
    form_model = 'player'
    form_fields = [
        'report_iq',
        'report_emoji',
        'report_message',
        'report_shared',
        'report_edit_back_count',
        'report_compose_history',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return CFG['show_iq'] and is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        spec = round_spec(player)
        task = spec['task']
        item = QD.QUESTIONS[task][spec['item_id']]
        period, q_in_period = _period_index_and_qnum(player.round_number)
        response_type = QD.TASK_RESPONSE[task]
        prior_answer = str(player.field_maybe_none('q_answer') or '')
        cond = get_condition(player)

        component = component_for_player(player)
        label = iq_component_label(component)
        n_correct = period_correct(player)
        iq = estimate_iq(component, n_correct, C.PERIOD_LENGTH)
        player.iq_estimate = iq

        signal = pilot_iq_feedback_signal(player)
        signal_name = (signal.get('name') or '') if isinstance(signal, dict) else ''
        signal_initial = signal_name[:1].upper() if signal_name else '?'
        return dict(
            condition=cond,
            component=component,
            label=label,
            n_correct=n_correct,
            iq=iq,
            display_name=player.participant.vars.get('display_name', ''),
            signal=signal,
            signal_initial=signal_initial,
            qual_emojis=QUAL_EMOJIS,
            in_treatment=cond in ('quantitative_social', 'qualitative_social'),
            is_quantitative=cond == 'quantitative_social',
            is_qualitative=cond == 'qualitative_social',
            has_received_message=isinstance(signal, dict) and signal.get('type') in ('quantitative', 'qualitative'),
            task_construct=TASK_CONSTRUCT.get(task, "task"),
            iq_component_title=task_iq_title(task),
            # Read-only backdrop: re-render the just-completed question.
            period=period,
            question_in_period=q_in_period,
            task=task,
            response_type=response_type,
            question_prompt=TASK_PROMPT.get(task, ''),
            big_image=task in ('ravens', 'sequences'),
            item=item,
            image=item.get('image'),
            is_placeholder=item.get('is_placeholder', False),
            prior_answer=prior_answer,
            option_rows=[
                dict(value=o, selected=(str(o) == prior_answer))
                for o in item.get('options', [])
            ],
        )

    @staticmethod
    def error_message(player: Player, values):
        cond = get_condition(player)
        if cond not in ('quantitative_social', 'qualitative_social'):
            return
        if cond == 'quantitative_social':
            v = values.get('report_iq')
            if v is None or v == '':
                return "Please enter your IQ score."
            if v < IQ_REPORT_MIN or v > IQ_REPORT_MAX:
                return f"Please enter an IQ score between {IQ_REPORT_MIN} and {IQ_REPORT_MAX}."
        else:
            msg = (values.get('report_message') or '').strip()
            if not msg:
                return "Please add a short note before continuing."
            if len(msg) < 5:
                return "Please write at least 5 characters in your note."
            if not values.get('report_emoji'):
                return "Please indicate how you feel."
        if values.get('report_shared') is None:
            return "Please choose whether to share your message."

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        spec = round_spec(player)
        component = component_for_player(player)
        label = iq_component_label(component)
        n_correct = period_correct(player)
        iq = player.field_maybe_none('iq_estimate')
        if iq is None:
            iq = estimate_iq(component, n_correct, C.PERIOD_LENGTH)
            player.iq_estimate = iq

        cond = get_condition(player)
        signal = pilot_iq_feedback_signal(player)
        username = (player.participant.vars.get('display_name') or '').strip()
        if cond in ('quantitative_social', 'qualitative_social'):
            # Name comes from the username chosen on the Further-instructions page.
            player.report_display_name = username
            if cond == 'quantitative_social':
                n = player.field_maybe_none('report_iq')
                if n is not None:
                    player.report_message = f"My {label} IQ score is {n}."
        else:
            # Control: no message composed; keep report fields blank.
            player.report_iq = None
            player.report_emoji = None
            player.report_message = None
            player.report_display_name = None
            player.report_edit_back_count = 0
            player.report_compose_history = ''
        player.feedback_snapshot = json.dumps(dict(
            round=player.round_number,
            condition=cond,
            task=spec['task'],
            set_id=spec['set_id'],
            component=component,
            iq=iq,
            n_correct=n_correct,
            signal=signal,
            sent_iq=player.field_maybe_none('report_iq'),
            sent_emoji=player.field_maybe_none('report_emoji'),
            sent_message=player.field_maybe_none('report_message'),
            shared=player.field_maybe_none('report_shared'),
            sent_display_name=player.field_maybe_none('report_display_name'),
            edit_back_count=player.field_maybe_none('report_edit_back_count') or 0,
            compose_history=player.field_maybe_none('report_compose_history') or '',
        ))
        if signal.get('type') == 'quantitative':
            player.received_signal_name = signal.get('name') or ''
            player.received_signal_value = str(signal.get('iq'))
        elif signal.get('type') == 'qualitative':
            player.received_signal_name = signal.get('name') or ''
            player.received_signal_value = signal.get('emoji') or ''


class GlobalIQFeedback(Page):
    """After periods 1–2: overall IQ readout + optional send (mirrors IQFeedback).

    Shown before the WTA elicitation so participants know their combined score
    before deciding whether to take the optional third period.
    """
    form_model = 'player'
    form_fields = [
        'global_report_iq',
        'global_report_emoji',
        'global_report_message',
        'global_report_shared',
        'global_report_edit_back_count',
        'global_report_compose_history',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return (
            CFG['show_iq']
            and CFG['use_wta']
            and player.round_number == 2 * C.PERIOD_LENGTH
        )

    @staticmethod
    def vars_for_template(player: Player):
        iq = global_iq_for_player(player)
        player.global_iq_estimate = iq
        treatment, _ = experienced_conditions(player)
        cond = treatment
        signal = dict(type='none', name=None)
        return dict(
            condition=cond,
            component='overall',
            label='overall',
            n_correct=None,
            iq=iq,
            display_name=player.participant.vars.get('display_name', ''),
            signal=signal,
            signal_initial='?',
            qual_emojis=QUAL_EMOJIS,
            in_treatment=cond in ('quantitative_social', 'qualitative_social'),
            is_quantitative=cond == 'quantitative_social',
            is_qualitative=cond == 'qualitative_social',
            has_received_message=False,
            task_construct='IQ',
            iq_component_title='Overall IQ',
            # Backdrop fields unused when we hide the question card; keep keys.
            period=None,
            question_in_period=None,
            task=None,
            response_type=None,
            question_prompt='',
            big_image=False,
            item={},
            image=None,
            is_placeholder=True,
            prior_answer='',
            option_rows=[],
        )

    @staticmethod
    def error_message(player: Player, values):
        treatment, _ = experienced_conditions(player)
        cond = treatment
        if cond not in ('quantitative_social', 'qualitative_social'):
            return
        if cond == 'quantitative_social':
            v = values.get('global_report_iq')
            if v is None or v == '':
                return "Please enter your IQ score."
            if v < IQ_REPORT_MIN or v > IQ_REPORT_MAX:
                return f"Please enter an IQ score between {IQ_REPORT_MIN} and {IQ_REPORT_MAX}."
        else:
            msg = (values.get('global_report_message') or '').strip()
            if not msg:
                return "Please add a short note before continuing."
            if len(msg) < 5:
                return "Please write at least 5 characters in your note."
            if not values.get('global_report_emoji'):
                return "Please indicate how you feel."
        if values.get('global_report_shared') is None:
            return "Please choose whether to share your message."

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        iq = player.field_maybe_none('global_iq_estimate')
        if iq is None:
            iq = global_iq_for_player(player)
            player.global_iq_estimate = iq
        treatment, _ = experienced_conditions(player)
        cond = treatment
        username = (player.participant.vars.get('display_name') or '').strip()
        if cond in ('quantitative_social', 'qualitative_social'):
            if cond == 'quantitative_social':
                n = player.field_maybe_none('global_report_iq')
                if n is not None:
                    player.global_report_message = f"My overall IQ score is {n}."
        else:
            player.global_report_iq = None
            player.global_report_emoji = None
            player.global_report_message = None
            player.global_report_shared = None
            player.global_report_edit_back_count = 0
            player.global_report_compose_history = ''


class PerceivedPercentile(Page):
    form_model = 'player'
    form_fields = ['perceived_relative_performance']

    @staticmethod
    def is_displayed(player: Player):
        return is_end_of_period_with_p3(player)

    @staticmethod
    def vars_for_template(player: Player):
        period, _ = _period_index_and_qnum(player.round_number)
        task = round_spec(player)['task']
        return dict(
            period=period,
            iq_component=TASK_IQ_LABEL.get(task, 'IQ'),
            iq_component_title=task_iq_title(task),
        )

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
        task = round_spec(player)['task']
        return dict(
            period=period,
            prior_guess=prior_guess,
            has_prior_guess=prior_guess is not None,
            iq_component_title=task_iq_title(task),
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
    form_fields = ['mood', 'performance_satisfaction', 'payment_satisfaction', 'task_enjoyment']

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

        question_keys = _stable_shuffled(
            player,
            f'eop-survey-{period}',
            ['mood', 'performance_satisfaction', 'payment_satisfaction', 'task_enjoyment'],
        )

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
        if (values.get('mood') is None
                or values.get('performance_satisfaction') is None
                or values.get('task_enjoyment') is None
                or values.get('payment_satisfaction') is None):
            return "Please answer all questions before continuing."


class TaskEffort(Page):
    """0-100 slider for overall effort on main cognitive tasks.

    Shown once at the end of the study for everyone, after demographics.
    """
    form_model = 'player'
    form_fields = ['task_effort']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def error_message(player: Player, values):
        if values.get('task_effort') is None or values.get('task_effort') == '':
            return "Please move the slider to indicate your effort before continuing."


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

        period_tasks = player.participant.vars.get('period_tasks', [])
        third_task = period_tasks[2] if len(period_tasks) >= 3 else None
        period_3_component = TASK_CONSTRUCT.get(third_task, third_task or 'third')

        return dict(
            treatment_condition=treatment,
            blocks=blocks,
            period_3_component=period_3_component,
        )

    @staticmethod
    def error_message(player: Player, values):
        for i in range(1, len(WTA_AMOUNTS) + 1):
            if not values.get(f'wta_t_{i}') or not values.get(f'wta_c_{i}'):
                return "Please make a choice for every payment level in both blocks."


class PlatformUsage(Page):
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
                "Please write at least 50 characters about your experience "
                "during the study (currently "
                f"{len(text)} characters)."
            )


def _checklist_vars(player: Player, motives: list, shuffle_key: str | None) -> list:
    items = [dict(m) for m in motives if not m['is_none']]
    if shuffle_key:
        items = _stable_shuffled(player, shuffle_key, items)
    none_item = next(m for m in motives if m['is_none'])
    ordered = items + [dict(none_item)]
    for m in ordered:
        m['checked'] = bool(player.field_maybe_none(m['field']))
        m['data_none'] = '1' if m['is_none'] else '0'
    return ordered


def _checklist_error(values: dict, motives: list):
    none_field = next(m['field'] for m in motives if m['is_none'])
    none = bool(values.get(none_field))
    others = [bool(values.get(m['field'])) for m in motives if not m['is_none']]
    if none and any(others):
        return "If you select 'None of these', please leave the other options unchecked."
    if not none and not any(others):
        return "Please select at least one option (or 'None of these')."


def experience_page_order(participant) -> list[str]:
    key = 'experience_page_order'
    if key not in participant.vars:
        rng = random.Random(f"{participant.code}-exp-pages")
        order = list(EXPERIENCE_PAGE_KEYS)
        rng.shuffle(order)
        participant.vars[key] = order
    return participant.vars[key]


def _impact_item_order(player: Player) -> list[str]:
    """Shared suffix order (mood/sat/effort) applied identically to both blocks."""
    suffixes = [suffix for suffix, _ in _MESSAGE_IMPACT_OUTCOMES]
    return _stable_shuffled(player, 'impact-items', list(suffixes))


def _impact_motives_for_player(player: Player) -> list:
    blocks = _stable_shuffled(player, 'impact-activities', list(MESSAGE_IMPACT_BLOCKS))
    suffix_order = _impact_item_order(player)
    items = []
    for block in blocks:
        by_suffix = {m['field'].rsplit('_', 1)[-1]: m for m in block['items']}
        for suffix in suffix_order:
            items.append(dict(by_suffix[suffix]))
    return items + [dict(MESSAGE_IMPACT_NONE)]


def _impact_blocks_for_player(player: Player) -> list:
    blocks = _stable_shuffled(player, 'impact-activities', list(MESSAGE_IMPACT_BLOCKS))
    suffix_order = _impact_item_order(player)
    out = []
    for block in blocks:
        by_suffix = {m['field'].rsplit('_', 1)[-1]: m for m in block['items']}
        items = []
        for suffix in suffix_order:
            item = dict(by_suffix[suffix])
            item['checked'] = bool(player.field_maybe_none(item['field']))
            item['data_none'] = '0'
            items.append(item)
        out.append(dict(heading=block['heading'], choices=items))
    return out


def _motives_for_experience_page(player: Player, page_key: str) -> list:
    if page_key == 'impacts':
        return _impact_motives_for_player(player)
    return EXPERIENCE_PAGE_META[page_key]['motives']


def _experience_form_fields(player: Player, slot: int) -> list[str]:
    page_key = experience_page_order(player.participant)[slot]
    return [m['field'] for m in _motives_for_experience_page(player, page_key)]


def _make_experience_slot(slot: int):
    class ExperienceChecklist(Page):
        """One slot in the randomized writing / sharing / impacts checklist sequence."""
        form_model = 'player'
        template_name = 'social_media/MotiveChecklist.html'

        @staticmethod
        def is_displayed(player: Player):
            return player.round_number == C.NUM_ROUNDS

        @staticmethod
        def get_form_fields(player: Player):
            return _experience_form_fields(player, slot)

        @staticmethod
        def vars_for_template(player: Player):
            page_key = experience_page_order(player.participant)[slot]
            meta = EXPERIENCE_PAGE_META[page_key]
            if page_key == 'impacts':
                none_item = dict(MESSAGE_IMPACT_NONE)
                none_item['checked'] = bool(player.field_maybe_none(none_item['field']))
                none_item['data_none'] = '1'
                return dict(
                    motive_blocks=_impact_blocks_for_player(player),
                    none_motive=none_item,
                    motives=[],
                )
            return dict(
                motives=_checklist_vars(player, meta['motives'], f'experience-{page_key}'),
                motive_blocks=[],
            )

        @staticmethod
        def error_message(player: Player, values):
            page_key = experience_page_order(player.participant)[slot]
            return _checklist_error(values, _motives_for_experience_page(player, page_key))

    ExperienceChecklist.__name__ = f'ExperienceChecklist{slot + 1}'
    ExperienceChecklist.__qualname__ = ExperienceChecklist.__name__
    return ExperienceChecklist


ExperienceChecklist1 = _make_experience_slot(0)
ExperienceChecklist2 = _make_experience_slot(1)
ExperienceChecklist3 = _make_experience_slot(2)


TOOL_FIELDS = [
    'tool_pen_paper',
    'tool_ai',
    'tool_cellphone_camera',
    'tool_search_engine',
    'tool_ask_someone_else',
    'tool_calculator',
]


class ToolsUsed(Page):
    """Unpaid tools checklist; does not affect Prolific approval or bonus."""
    form_model = 'player'
    form_fields = TOOL_FIELDS + ['tool_none']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def error_message(player: Player, values):
        none = bool(values.get('tool_none'))
        others = [bool(values.get(f)) for f in TOOL_FIELDS]
        if none and any(others):
            return "If you select 'None of the above', please leave the other options unchecked."
        if not none and not any(others):
            return "Please select at least one option (or 'None of the above')."


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

        payoff = cu(0)
        payoff += raven_total * C.PAY_PER_CORRECT

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
            selected_wta_amount=selected_amount,
            selected_wta_column=selected_col,
            selected_for_retake=selected_for_retake,
            payoff=float(payoff),
        )

        selected_accept_decline = 'Accept' if selected_choice == 'Yes' else 'Decline'
        selected_messages_label = (
            'with messages' if selected_col == 't' else 'without messages'
        )

        return dict(
            raven_total=raven_total,
            selected_for_retake=selected_for_retake,
            selected_amount=f"${selected_amount:.2f}",
            selected_column='treatment' if selected_col == 't' else 'control',
            p3_feedback_desc=p3_feedback_desc,
            payoff=payoff,
            selected_accept_decline=selected_accept_decline,
            selected_messages_label=selected_messages_label,
        )


class Comments(Page):
    """Optional free-text comments box, shown as the last survey page."""
    form_model = 'player'
    form_fields = ['comments']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS


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

        total_payoff = cu(question_payoff)
        player.payoff = total_payoff

        # Bonus stripped by tab switching (correct answers that switched tabs).
        switched_p12 = switched_disqualified_count(player, 1, 2 * C.PERIOD_LENGTH)
        subtracted = switched_p12 * rate_per_correct
        if accepted:
            switched_p3 = switched_disqualified_count(player, C.THIRD_PERIOD_START, C.NUM_ROUNDS)
            subtracted += switched_p3 * p3_pay_rate

        # Deferred estimate-accuracy bonus ceiling. Participants who were never
        # asked the baseline IQ reference-point guess cannot earn its $0.50, so
        # we drop it from the ceiling we quote them (1.25 -> 0.75).
        guess_bonus_max = C.GUESS_BONUS_MAX
        if not player.participant.vars.get('iq_reference_asked', False):
            guess_bonus_max = guess_bonus_max - C.PAY_IQ_REFERENCE_GUESS

        return dict(
            total_payoff=total_payoff,
            task_rows=task_rows,
            question_subtotal=f"{question_payoff:.2f}",
            switched_subtracted=f"{subtracted:.2f}",
            had_switch_deduction=subtracted > 0,
            guess_bonus_max_display=f"{float(guess_bonus_max):.2f}",
            prolific_url=PROLIFIC_COMPLETION_URL,
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
    ProlificID,
    IQReferencePoint,
    Intro,
    TaskIntro,
    QuestionPage,
    BlockFeedback,
    IQFeedback,
    PerceivedPercentile,
    PerceivedPercentileConfidence,
    EndOfPeriodSurvey,
    GlobalIQFeedback,
    WTACompare,
    Results,
    BigFiveSurvey,
    SelfEsteemSurvey,
    NarcissismSurvey,
    Demographics,
    TaskEffort,
    PlatformUsage,
    RealismQuestion,
    ExperienceChecklist1,
    ExperienceChecklist2,
    ExperienceChecklist3,
    ToolsUsed,
    SurveyReliabilityOverall,
    Comments,
    FinalResults,
]
