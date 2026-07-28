from os import environ
from pathlib import Path

# Load .env for local development (DATABASE_URL, etc.)
if Path('.env').exists():
    from dotenv import load_dotenv
    load_dotenv()

# The active pilot is selected with the EXPERIMENT_PILOT environment variable
# ("initial" | "iq" | "main"), read in social_media/__init__.py. Set it before
# launching, e.g. (PowerShell)  $env:EXPERIMENT_PILOT="iq"; otree devserver
SESSION_CONFIGS = [
    dict(
        name='cognitive_tasks',
        display_name='Cognitive Tasks Study',
        app_sequence=['social_media'],
        num_demo_participants=40,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,
    doc="",
)

PARTICIPANT_FIELDS = ['period_1_condition', 'period_2_condition', 'social_media_summary', 'wta_state', 'third_period_accepted', 'third_period_pay_rate', 'third_period_condition']
SESSION_FIELDS = []

LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = False

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """
# Heroku / production: set OTREE_SECRET_KEY (e.g. `heroku config:set OTREE_SECRET_KEY=...`).
SECRET_KEY = environ.get('OTREE_SECRET_KEY', '2398301291032')

