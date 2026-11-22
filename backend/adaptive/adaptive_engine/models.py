"""Core data model.

An :class:`Item` is anything with IRT parameters and optional free-form
metadata; a :class:`Response` is a correct/incorrect observation at a
point in time. Nothing in the library knows about any particular
subject or product.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping

__all__ = ["Item", "ItemBank", "Response", "MemoryState", "LearnerState"]


@dataclass(frozen=True)
class Item:
    """A single assessable item.

    Parameters
    ----------
    id:
        Unique identifier within its :class:`ItemBank` (any string —
        a database UUID, a slug, a word, ...).
    difficulty:
        IRT difficulty ``b``: the ability level at which a learner has a
        50% chance of answering correctly (2PL, no guessing).
    discrimination:
        IRT discrimination ``a``: how sharply the item separates
        learners just below from just above its difficulty. ``1.0``
        reduces the 2PL model to 1PL (Rasch).
    tags:
        Optional free-form content labels ("fractions", "verbs", ...)
        used only for coverage balancing. The engine attaches no meaning
        to them.
    metadata:
        Arbitrary consumer payload (question text, answer key, ...).
        The engine never reads it.
    """

    id: str
    difficulty: float
    discrimination: float = 1.0
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.discrimination <= 0:
            raise ValueError(
                f"Item {self.id!r}: discrimination must be > 0, got {self.discrimination}"
            )


class ItemBank:
    """An immutable, indexed collection of :class:`Item` objects."""

    def __init__(self, items: Iterable[Item]):
        self._items: dict[str, Item] = {}
        for item in items:
            if item.id in self._items:
                raise ValueError(f"Duplicate item id: {item.id!r}")
            self._items[item.id] = item
        if not self._items:
            raise ValueError("ItemBank cannot be empty")

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Item]:
        return iter(self._items.values())

    def __contains__(self, item_id: str) -> bool:
        return item_id in self._items

    def __getitem__(self, item_id: str) -> Item:
        return self._items[item_id]

    @property
    def ids(self) -> list[str]:
        return list(self._items.keys())

    @property
    def tags(self) -> set[str]:
        return {tag for item in self for tag in item.tags}


@dataclass(frozen=True)
class Response:
    """One observed answer: which item, whether it was correct, and when.

    ``timestamp`` is seconds since the epoch (or any monotonically
    comparable float the consumer chooses); it is used only by the
    spaced-repetition scheduler.
    """

    item_id: str
    correct: bool
    timestamp: float = 0.0


@dataclass
class MemoryState:
    """Per-item memory trace used by the spaced-repetition scheduler."""

    half_life: float  # hours
    last_review: float  # timestamp (seconds since epoch)
    streak: int = 0  # consecutive correct reviews
    n_reviews: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "half_life": self.half_life,
            "last_review": self.last_review,
            "streak": self.streak,
            "n_reviews": self.n_reviews,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "MemoryState":
        return cls(
            half_life=float(d["half_life"]),
            last_review=float(d["last_review"]),
            streak=int(d["streak"]),
            n_reviews=int(d["n_reviews"]),
        )


@dataclass
class LearnerState:
    """Everything the engine knows about one learner.

    The state is a plain, JSON-serialisable value object so consumers can
    persist it anywhere (Postgres row, Redis key, file). The engine never
    holds learner state internally — every API call takes the state in
    and hands a new/updated state back.
    """

    ability: float = 0.0  # current theta estimate
    ability_se: float = 1.0  # posterior SD of theta (uncertainty)
    responses: list[Response] = field(default_factory=list)
    memory: dict[str, MemoryState] = field(default_factory=dict)

    @property
    def seen_item_ids(self) -> set[str]:
        return {r.item_id for r in self.responses}

    def to_dict(self) -> dict[str, Any]:
        return {
            "ability": self.ability,
            "ability_se": self.ability_se,
            "responses": [
                {"item_id": r.item_id, "correct": r.correct, "timestamp": r.timestamp}
                for r in self.responses
            ],
            "memory": {k: m.to_dict() for k, m in self.memory.items()},
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "LearnerState":
        return cls(
            ability=float(d.get("ability", 0.0)),
            ability_se=float(d.get("ability_se", 1.0)),
            responses=[
                Response(r["item_id"], bool(r["correct"]), float(r.get("timestamp", 0.0)))
                for r in d.get("responses", [])
            ],
            memory={
                k: MemoryState.from_dict(m) for k, m in d.get("memory", {}).items()
            },
        )
