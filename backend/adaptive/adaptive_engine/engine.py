"""The public facade: :class:`AdaptiveEngine`.

The engine is **stateless with respect to learners**: it holds an item
bank and configuration, and every call takes a :class:`LearnerState` in
and returns results (and, for :meth:`record_response`, a new state).
That makes it trivial to run inside any host — a web request handler, a
batch worker, a notebook — with learner state persisted wherever the
consumer likes.

Typical loop::

    engine = AdaptiveEngine(bank)
    state = LearnerState()
    item = engine.next_item(state)
    # ... learner answers `item` ...
    state = engine.record_response(state, Response(item.id, correct=True, timestamp=now))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from . import scheduling
from .irt import AbilityEstimate, estimate_ability
from .models import Item, ItemBank, LearnerState, Response
from .selection import select_next

__all__ = ["AdaptiveEngine", "EngineConfig"]


@dataclass(frozen=True)
class EngineConfig:
    """Engine configuration.

    exposure_k:
        Randomesque pool size for CAT selection (1 = deterministic
        maximum-information selection).
    content_targets:
        Optional ``tag -> target proportion`` blueprint for coverage
        balancing.
    review_threshold:
        Recall-probability threshold at/below which a seen item is due
        for review.
    review_priority:
        When a review is due, probability that :meth:`next_item` serves
        a due review instead of a new item (interleaves consolidation
        with progression).
    """

    exposure_k: int = 5
    content_targets: Mapping[str, float] | None = None
    review_threshold: float = 0.5
    review_priority: float = 0.5


class AdaptiveEngine:
    """IRT ability estimation + CAT selection + spaced-repetition review,
    over any :class:`ItemBank`."""

    def __init__(
        self,
        bank: ItemBank,
        config: EngineConfig | None = None,
        seed: int | None = None,
    ):
        self.bank = bank
        self.config = config or EngineConfig()
        self._rng = np.random.default_rng(seed)

    # ---------------------------------------------------------------- ability

    def estimate_ability(self, state: LearnerState) -> AbilityEstimate:
        """EAP ability estimate from the state's full response history.

        Responses to items not in this bank are ignored (they carry no
        usable parameters).
        """
        scored = [(r.correct, self.bank[r.item_id]) for r in state.responses if r.item_id in self.bank]
        if not scored:
            return AbilityEstimate(theta=0.0, se=1.0)
        correct = np.array([c for c, _ in scored], dtype=float)
        difficulty = np.array([item.difficulty for _, item in scored])
        discrimination = np.array([item.discrimination for _, item in scored])
        return estimate_ability(correct, difficulty, discrimination)

    # ---------------------------------------------------------------- updates

    def record_response(self, state: LearnerState, response: Response) -> LearnerState:
        """Fold one response into the learner state.

        Returns a **new** state with: the response appended, the ability
        estimate re-computed online, and the item's spaced-repetition
        memory trace updated. The input state is not mutated.
        """
        if response.item_id not in self.bank:
            raise KeyError(f"Response references unknown item {response.item_id!r}")
        new_state = LearnerState(
            ability=state.ability,
            ability_se=state.ability_se,
            responses=[*state.responses, response],
            memory=dict(state.memory),
        )
        est = self.estimate_ability(new_state)
        new_state.ability, new_state.ability_se = est.theta, est.se
        new_state.memory[response.item_id] = scheduling.update_memory(
            state.memory.get(response.item_id), response.correct, response.timestamp
        )
        return new_state

    # -------------------------------------------------------------- selection

    def next_item(self, state: LearnerState, now: float | None = None) -> Item | None:
        """The single next item to serve.

        With probability ``review_priority`` (when reviews are due) this
        is the most overdue review; otherwise it is a CAT-selected new
        item. Falls back to whichever pool is non-empty; returns ``None``
        only when every item has been seen and nothing is due.
        """
        due = self.review_queue(state, now) if now is not None else []
        unseen = [item for item in self.bank if item.id not in state.seen_item_ids]

        serve_review = bool(due) and (
            not unseen or self._rng.random() < self.config.review_priority
        )
        if serve_review:
            return due[0]
        if not unseen:
            return None
        administered = [self.bank[i] for i in state.seen_item_ids if i in self.bank]
        return select_next(
            theta=state.ability,
            candidates=unseen,
            administered=administered,
            exposure_k=self.config.exposure_k,
            content_targets=self.config.content_targets,
            rng=self._rng,
        )

    def next_items(self, state: LearnerState, n: int, now: float | None = None) -> list[Item]:
        """A queue of up to ``n`` recommended items (e.g. for a worker
        that precomputes each user's next questions).

        Simulates administration: each pick is assumed answered at the
        current ability estimate so the queue stays varied and balanced.
        """
        sim_state = state
        queue: list[Item] = []
        for _ in range(n):
            item = self.next_item(sim_state, now)
            if item is None:
                break
            queue.append(item)
            # Mark as seen without changing ability (we don't know the answer yet).
            sim_state = LearnerState(
                ability=sim_state.ability,
                ability_se=sim_state.ability_se,
                responses=[*sim_state.responses, Response(item.id, True, now or 0.0)],
                memory=sim_state.memory,
            )
        return queue

    # ---------------------------------------------------------------- reviews

    def review_queue(self, state: LearnerState, now: float | None = None) -> list[Item]:
        """Seen items due for review, most-forgotten first."""
        if now is None:
            now = max((r.timestamp for r in state.responses), default=0.0)
        due: list[tuple[float, Item]] = []
        for item_id, memory in state.memory.items():
            if item_id not in self.bank:
                continue
            p = scheduling.recall_probability(memory, now)
            if p <= self.config.review_threshold:
                due.append((p, self.bank[item_id]))
        due.sort(key=lambda pair: pair[0])
        return [item for _, item in due]

    def review_schedule(self, state: LearnerState) -> dict[str, float]:
        """``item_id -> timestamp`` at which each seen item next becomes due."""
        return {
            item_id: scheduling.next_due_time(memory, self.config.review_threshold)
            for item_id, memory in state.memory.items()
            if item_id in self.bank
        }
