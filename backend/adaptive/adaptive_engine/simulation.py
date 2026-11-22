"""Synthetic-learner simulation: the engine's correctness and efficiency
evidence.

Two experiments, both used by the test suite and the standalone
simulation study:

* :func:`ability_recovery` — generate learners with *known* abilities,
  have them answer items according to the true IRT model, and check the
  estimator recovers those abilities (correlation / RMSE).
* :func:`efficiency_experiment` — how many items adaptive (CAT)
  selection needs to reach a target ability-estimate precision versus
  presenting the same bank in a fixed order ("adaptive reaches the
  target SE in N% fewer items").
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .engine import AdaptiveEngine, EngineConfig
from .irt import estimate_ability, probability
from .models import Item, ItemBank, LearnerState, Response

__all__ = [
    "make_synthetic_bank",
    "simulate_response",
    "ability_recovery",
    "RecoveryResult",
    "efficiency_experiment",
    "EfficiencyResult",
]


def make_synthetic_bank(
    n_items: int,
    seed: int | None = None,
    two_pl: bool = True,
    tags: tuple[str, ...] = (),
) -> ItemBank:
    """A synthetic item bank: difficulties ~ N(0,1), discriminations ~
    lognormal around 1 (or all 1.0 for 1PL), optional round-robin tags."""
    rng = np.random.default_rng(seed)
    difficulty = rng.normal(0.0, 1.0, n_items)
    discrimination = (
        np.exp(rng.normal(0.0, 0.3, n_items)) if two_pl else np.ones(n_items)
    )
    return ItemBank(
        Item(
            id=f"item-{i:04d}",
            difficulty=float(difficulty[i]),
            discrimination=float(discrimination[i]),
            tags=(tags[i % len(tags)],) if tags else (),
        )
        for i in range(n_items)
    )


def simulate_response(
    theta_true: float, item: Item, rng: np.random.Generator
) -> bool:
    """Draw a correct/incorrect answer from the true 2PL model."""
    p = probability(theta_true, item.difficulty, item.discrimination)
    return bool(rng.random() < p)


@dataclass
class RecoveryResult:
    theta_true: np.ndarray
    theta_est: np.ndarray
    correlation: float
    rmse: float
    mean_se: float


def ability_recovery(
    bank: ItemBank,
    n_learners: int = 200,
    n_items_each: int = 40,
    seed: int | None = 0,
    adaptive: bool = True,
) -> RecoveryResult:
    """Do estimated abilities recover the known true abilities?

    Each synthetic learner has a true theta drawn from N(0, 1), answers
    ``n_items_each`` items (adaptively selected or randomly chosen), and
    is then scored by the engine's EAP estimator.
    """
    rng = np.random.default_rng(seed)
    theta_true = rng.normal(0.0, 1.0, n_learners)
    theta_est = np.empty(n_learners)
    ses = np.empty(n_learners)

    for i, t in enumerate(theta_true):
        engine = AdaptiveEngine(bank, EngineConfig(exposure_k=3), seed=int(rng.integers(2**31)))
        state = LearnerState()
        if adaptive:
            for _ in range(n_items_each):
                item = engine.next_item(state)
                if item is None:
                    break
                correct = simulate_response(t, item, rng)
                state = engine.record_response(state, Response(item.id, correct))
        else:
            ids = rng.choice(bank.ids, size=min(n_items_each, len(bank)), replace=False)
            for item_id in ids:
                item = bank[item_id]
                correct = simulate_response(t, item, rng)
                state = engine.record_response(state, Response(item.id, correct))
        theta_est[i] = state.ability
        ses[i] = state.ability_se

    corr = float(np.corrcoef(theta_true, theta_est)[0, 1])
    rmse = float(np.sqrt(np.mean((theta_true - theta_est) ** 2)))
    return RecoveryResult(
        theta_true=theta_true,
        theta_est=theta_est,
        correlation=corr,
        rmse=rmse,
        mean_se=float(ses.mean()),
    )


@dataclass
class EfficiencyResult:
    target_se: float
    adaptive_items: np.ndarray  # per-learner items needed (NaN = never reached)
    fixed_items: np.ndarray
    mean_adaptive: float
    mean_fixed: float
    pct_fewer_items: float
    n_learners: int


def _items_to_target_se(
    theta_true: float,
    bank: ItemBank,
    order: str,
    target_se: float,
    max_items: int,
    rng: np.random.Generator,
) -> float:
    """Number of items a learner needs before the EAP posterior SD drops
    to ``target_se``, under adaptive or fixed-order presentation."""
    engine = AdaptiveEngine(bank, EngineConfig(exposure_k=1), seed=int(rng.integers(2**31)))
    state = LearnerState()
    fixed_order = bank.ids  # deterministic bank order = "fixed syllabus"
    for n in range(1, max_items + 1):
        if order == "adaptive":
            item = engine.next_item(state)
        else:
            item = bank[fixed_order[n - 1]]
        if item is None:
            break
        correct = simulate_response(theta_true, item, rng)
        state = engine.record_response(state, Response(item.id, correct))
        if state.ability_se <= target_se:
            return float(n)
    return float("nan")


def efficiency_experiment(
    bank: ItemBank,
    n_learners: int = 200,
    target_se: float = 0.35,
    max_items: int = 120,
    seed: int | None = 0,
) -> EfficiencyResult:
    """Adaptive vs fixed-order: items needed to reach ``target_se``.

    Learners who never reach the target within ``max_items`` under a
    given regime are excluded from that regime's mean (reported via NaN);
    the headline percentage uses learners who reached the target under
    **both** regimes, so the comparison is paired and fair.
    """
    rng = np.random.default_rng(seed)
    theta_true = rng.normal(0.0, 1.0, n_learners)
    adaptive = np.empty(n_learners)
    fixed = np.empty(n_learners)
    for i, t in enumerate(theta_true):
        adaptive[i] = _items_to_target_se(t, bank, "adaptive", target_se, max_items, rng)
        fixed[i] = _items_to_target_se(t, bank, "fixed", target_se, max_items, rng)

    both = ~np.isnan(adaptive) & ~np.isnan(fixed)
    mean_adaptive = float(np.mean(adaptive[both]))
    mean_fixed = float(np.mean(fixed[both]))
    pct_fewer = 100.0 * (mean_fixed - mean_adaptive) / mean_fixed
    return EfficiencyResult(
        target_se=target_se,
        adaptive_items=adaptive,
        fixed_items=fixed,
        mean_adaptive=mean_adaptive,
        mean_fixed=mean_fixed,
        pct_fewer_items=float(pct_fewer),
        n_learners=int(both.sum()),
    )
