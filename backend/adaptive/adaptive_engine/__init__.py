"""adaptive-engine: a domain-agnostic adaptive learning engine.

IRT (2PL/1PL) ability estimation, computerised adaptive item selection
(maximum Fisher information with exposure control and content
balancing), and spaced-repetition review scheduling — over any item
bank, with learner state as a plain serialisable value object.

Quick start::

    from adaptive_engine import AdaptiveEngine, Item, ItemBank, LearnerState, Response

    bank = ItemBank([Item("q1", difficulty=-0.5), Item("q2", difficulty=0.8)])
    engine = AdaptiveEngine(bank)
    state = LearnerState()
    item = engine.next_item(state)
    state = engine.record_response(state, Response(item.id, correct=True, timestamp=0.0))
    print(state.ability, state.ability_se)
"""

from .engine import AdaptiveEngine, EngineConfig
from .experiment import ArmComparison, assign_arm, compare_arms, learning_gain
from .irt import (
    AbilityEstimate,
    calibrate,
    estimate_ability,
    fisher_information,
    probability,
)
from .models import Item, ItemBank, LearnerState, MemoryState, Response
from .scheduling import is_due, next_due_time, recall_probability, update_memory
from .selection import select_next

__version__ = "0.1.0"

__all__ = [
    "AdaptiveEngine",
    "EngineConfig",
    "Item",
    "ItemBank",
    "LearnerState",
    "MemoryState",
    "Response",
    "AbilityEstimate",
    "probability",
    "fisher_information",
    "estimate_ability",
    "calibrate",
    "select_next",
    "recall_probability",
    "update_memory",
    "next_due_time",
    "is_due",
    "assign_arm",
    "learning_gain",
    "compare_arms",
    "ArmComparison",
    "__version__",
]
