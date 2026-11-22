"""Spaced-repetition scheduling via an exponential-forgetting half-life
model.

Model
-----
After a review, the probability of recalling an item decays
exponentially with elapsed time (Ebbinghaus forgetting curve):

    P(recall at t) = 2 ** (-(t - t_last) / h)

where ``h`` is the item's current half-life: the time after which
recall probability has fallen to 50%. Each successful review multiplies
the half-life by an ease factor (the spacing effect, as in SM-2 style
schedulers); each failure resets it toward the initial value. An item
becomes due when its predicted recall drops below a threshold (default
0.5, i.e. one half-life after the last review).

All times are consumer-supplied floats (seconds since epoch); half-lives
are stored in hours.
"""

from __future__ import annotations

from .models import MemoryState

__all__ = [
    "recall_probability",
    "update_memory",
    "next_due_time",
    "is_due",
]

INITIAL_HALF_LIFE_HOURS = 12.0
EASE_FACTOR = 2.2  # successful review multiplies half-life by this
FAILURE_FACTOR = 0.4  # failed review multiplies half-life by this
MIN_HALF_LIFE_HOURS = 1.0
MAX_HALF_LIFE_HOURS = 24.0 * 365  # cap at a year

_SECONDS_PER_HOUR = 3600.0


def recall_probability(memory: MemoryState, now: float) -> float:
    """Predicted probability the learner still recalls the item at ``now``."""
    elapsed_hours = max(0.0, (now - memory.last_review) / _SECONDS_PER_HOUR)
    return 2.0 ** (-elapsed_hours / memory.half_life)


def update_memory(
    memory: MemoryState | None,
    correct: bool,
    now: float,
) -> MemoryState:
    """Return the memory state after a review at time ``now``.

    Pass ``memory=None`` for an item's first-ever review.
    """
    if memory is None:
        half_life = (
            INITIAL_HALF_LIFE_HOURS if correct else INITIAL_HALF_LIFE_HOURS * FAILURE_FACTOR
        )
        return MemoryState(
            half_life=half_life,
            last_review=now,
            streak=1 if correct else 0,
            n_reviews=1,
        )
    if correct:
        half_life = memory.half_life * EASE_FACTOR
        streak = memory.streak + 1
    else:
        half_life = memory.half_life * FAILURE_FACTOR
        streak = 0
    half_life = min(max(half_life, MIN_HALF_LIFE_HOURS), MAX_HALF_LIFE_HOURS)
    return MemoryState(
        half_life=half_life,
        last_review=now,
        streak=streak,
        n_reviews=memory.n_reviews + 1,
    )


def next_due_time(memory: MemoryState, threshold: float = 0.5) -> float:
    """Timestamp at which predicted recall falls to ``threshold``.

    With the default threshold of 0.5 this is exactly one half-life
    after the last review.
    """
    if not 0.0 < threshold < 1.0:
        raise ValueError(f"threshold must be in (0, 1), got {threshold}")
    import math

    hours_until_due = -memory.half_life * math.log2(threshold)
    return memory.last_review + hours_until_due * _SECONDS_PER_HOUR


def is_due(memory: MemoryState, now: float, threshold: float = 0.5) -> bool:
    """True if the item's predicted recall at ``now`` is at or below the
    threshold (i.e. it should be reviewed)."""
    return recall_probability(memory, now) <= threshold
