from os import environ
from pathlib import Path

# Load .env for local development (DATABASE_URL, etc.)
if Path('.env').exists():
    from dotenv import load_dotenv
    load_dotenv()

SESSION_CONFIGS = [
    dict(
        name='social_media',
        display_name='Social Media and Well-being Experiment',
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
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = False

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """
SECRET_KEY = '2398301291032'

