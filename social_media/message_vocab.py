"""Detect task-specific vocabulary in peer message text.

Matches the coding in pilot_1_analysis/notes_coding.py: a message is
task-specific if it names content tied to one task type (numbers, shapes,
dots, matrices, etc.) and therefore should not travel to participants on
other tasks.
"""
import re

# Keep in sync with TASK_VOCAB in pilot_1_analysis/notes_coding.py
_TASK_VOCAB_PATTERNS = [
    r"\bmath\b|\bnumbers?\b|logix|arithmetic|sequenc|equation",
    r"spatial|rotat|\bshapes?\b|\bcubes?\b|\b3d\b",
    r"\bdots?\b|\bsquares?\b|blink|images? stayed|flash|memoriz|"
    r"remember|count (them|the white)",
    r"\bpatterns?\b|\bmatri|\bpuzzles?\b",
]
ANY_VOCAB_RE = re.compile(
    "|".join(f"(?:{p})" for p in _TASK_VOCAB_PATTERNS),
    re.IGNORECASE,
)


def is_task_specific(text: str) -> bool:
    """True if the message names task content (task_specific=1 in analysis)."""
    return bool(ANY_VOCAB_RE.search(text or ""))
