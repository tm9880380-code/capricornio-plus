"""Computerised adaptive testing (CAT) item selection.

Maximum Fisher information with randomesque exposure control and
optional content balancing:

* Maximum information: prefer the items with the highest Fisher
  information at the current ability estimate, i.e. the ones that
  shrink uncertainty about theta fastest. For the 2PL this favours
  difficulty near the learner's ability, weighted by discrimination
  squared.
* Randomesque exposure control (Kingsbury & Zara, 1989): always serving
  the single most informative item over-exposes a handful of items and
  makes every session identical, so instead pick uniformly at random
  among the top ``exposure_k`` candidates.
* Content balancing: if items carry tags and the caller supplies target
  proportions, restrict candidates to the tag furthest below its target
  (max-deficit), so coverage tracks the blueprint while selection stays
  adaptive within it.
"""

from __future__ import annotations

from collections import Counter
from typing import Mapping, Sequence

import numpy as np

from .irt import fisher_information
from .models import Item

__all__ = ["select_next"]


def _balanced_tag(
    candidates: Sequence[Item],
    administered: Sequence[Item],
    targets: Mapping[str, float],
) -> str | None:
    """Return the target tag with the largest coverage deficit that still
    has available candidates, or None if balancing cannot apply."""
    available_tags = {t for item in candidates for t in item.tags if t in targets}
    if not available_tags:
        return None
    counts: Counter[str] = Counter()
    for item in administered:
        for t in item.tags:
            if t in targets:
                counts[t] += 1
    total = sum(counts.values())
    if total == 0:
        # Nothing administered yet: start with the largest target share.
        return max(available_tags, key=lambda t: targets[t])
    deficit = {t: targets[t] - counts[t] / total for t in available_tags}
    return max(deficit, key=deficit.get)


def select_next(
    theta: float,
    candidates: Sequence[Item],
    administered: Sequence[Item] = (),
    exposure_k: int = 5,
    content_targets: Mapping[str, float] | None = None,
    rng: np.random.Generator | None = None,
) -> Item:
    """Choose the next item to administer.

    Parameters
    ----------
    theta:
        Current ability estimate.
    candidates:
        Items eligible for administration (the caller filters out items
        already seen, not yet due, etc.).
    administered:
        Items already administered this session — used only for content
        balancing.
    exposure_k:
        Size of the "randomesque" pool: the item is drawn uniformly from
        the ``exposure_k`` most informative candidates. ``1`` gives pure
        maximum-information selection (deterministic).
    content_targets:
        Optional mapping ``tag -> target proportion``. When provided,
        selection is restricted to the tag currently furthest below its
        target (among tags with available candidates).
    rng:
        NumPy random generator for reproducibility.

    Returns
    -------
    Item
        The selected item.
    """
    if not candidates:
        raise ValueError("select_next: no candidate items")
    if exposure_k < 1:
        raise ValueError(f"exposure_k must be >= 1, got {exposure_k}")
    rng = rng or np.random.default_rng()

    pool = list(candidates)
    if content_targets:
        tag = _balanced_tag(pool, administered, content_targets)
        if tag is not None:
            tagged = [item for item in pool if tag in item.tags]
            if tagged:
                pool = tagged

    difficulty = np.array([item.difficulty for item in pool])
    discrimination = np.array([item.discrimination for item in pool])
    info = fisher_information(theta, difficulty, discrimination)

    k = min(exposure_k, len(pool))
    # argpartition: indices of the k most informative items, O(n).
    top_k = np.argpartition(info, -k)[-k:]
    choice = int(rng.choice(top_k))
    return pool[choice]
