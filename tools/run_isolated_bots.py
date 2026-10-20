"""Run oTree bots in a fresh in-memory DB, without loading the local study DB."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['OTREE_IN_MEMORY'] = '1'
os.environ.pop('OTREE_EPHEMERAL', None)
os.environ['DATABASE_URL'] = 'sqlite://'
import otree.database
otree.database.load_in_memory_db = lambda: None
from otree.main import execute_from_command_line
sys.argv[:] = ['otree', 'test', 'cognitive_tasks', sys.argv[1] if len(sys.argv)>1 else '8']
execute_from_command_line(sys.argv)
