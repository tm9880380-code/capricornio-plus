"""A/B experiment harness: stable arm assignment and learning-gain
analysis.

Needs only user identifiers, scored responses, and item parameters -
the platform integration feeds it real attempt logs, the test suite
feeds it synthetic ones.

Metric
------
The pre-registered learning-gain metric (see the repository's
``experiment/PREREGISTRATION.md``, fixed before any live data was
analysed):

    For each eligible user, estimate ability twice from their
    chronological experiment answers: theta_start from the first
    ``window`` answers and theta_end from the last ``window`` answers.
    Learning gain = (theta_end - theta_start), normalised to a rate per
    20 questions using the number of questions between the two window
    midpoints.

Ability — not raw accuracy — is the right outcome variable because the
two arms see systematically different item difficulties (an adaptive arm
serves items near the learner's level, pinning accuracy near a
constant), which confounds raw accuracy; IRT ability estimates are
difficulty-adjusted by construction.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .irt import estimate_ability
from .models import ItemBank, Response

__all__ = [
    "assign_arm",
    "learning_gain",
    "compare_arms",
    "ArmComparison",
]


def assign_arm(
    user_id: str,
    experiment: str = "adaptive-vs-fixed",
    arms: Sequence[str] = ("control", "treatment"),
) -> str:
    """Deterministic, stable arm assignment.

    Hashes ``experiment:user_id`` with SHA-256 and buckets the digest,
    so a given user always lands in the same arm (across sessions,
    devices and deploys), assignment is effectively random across users,
    and changing the experiment name reshuffles independently.
    """
    if not arms:
        raise ValueError("arms must be non-empty")
    digest = hashlib.sha256(f"{experiment}:{user_id}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "big")
    return arms[bucket % len(arms)]


def _window_theta(responses: Sequence[Response], bank: ItemBank) -> float:
    scored = [(r.correct, bank[r.item_id]) for r in responses if r.item_id in bank]
    correct = np.array([c for c, _ in scored], dtype=float)
    difficulty = np.array([item.difficulty for _, item in scored])
    discrimination = np.array([item.discrimination for _, item in scored])
    return estimate_ability(correct, difficulty, discrimination).theta


def learning_gain(
    responses: Sequence[Response],
    bank: ItemBank,
    window: int = 8,
    min_responses: int = 16,
) -> float | None:
    """Pre-registered per-user learning gain, or ``None`` if the user is
    ineligible (fewer than ``min_responses`` scoreable answers).

    Returns the ability change **per 20 questions answered**:

        (theta_end - theta_start) * 20 / (questions between window midpoints)
    """
    if min_responses < 2 * window:
        raise ValueError("min_responses must be at least 2 * window")
    scoreable = [r for r in responses if r.item_id in bank]
    n = len(scoreable)
    if n < min_responses:
        return None
    ordered = sorted(scoreable, key=lambda r: r.timestamp)
    theta_start = _window_theta(ordered[:window], bank)
    theta_end = _window_theta(ordered[-window:], bank)
    midpoint_gap = n - window  # from question (window+1)/2 to n-(window-1)/2
    return (theta_end - theta_start) * 20.0 / midpoint_gap


@dataclass(frozen=True)
class ArmComparison:
    """Treatment-vs-control comparison of per-user learning gains."""

    n_treatment: int
    n_control: int
    mean_treatment: float
    mean_control: float
    diff: float  # mean_treatment - mean_control (theta per 20 questions)
    diff_ci95: tuple[float, float]  # bootstrap CI for the difference
    pct_improvement: float | None  # None when control mean is <= 0
    pct_improvement_ci95: tuple[float, float] | None
    cohens_d: float
    p_value: float  # Welch's t-test, two-sided

    def summary(self) -> str:
        lines = [
            f"treatment: n={self.n_treatment}, mean gain {self.mean_treatment:+.3f} theta/20q",
            f"control:   n={self.n_control}, mean gain {self.mean_control:+.3f} theta/20q",
            f"difference: {self.diff:+.3f} theta/20q "
            f"(95% CI {self.diff_ci95[0]:+.3f} to {self.diff_ci95[1]:+.3f})",
            f"effect size (Cohen's d): {self.cohens_d:+.2f};  Welch p = {self.p_value:.3f}",
        ]
        if self.pct_improvement is not None and self.pct_improvement_ci95 is not None:
            lo, hi = self.pct_improvement_ci95
            lines.append(
                f"improvement: {self.pct_improvement:+.1f}% "
                f"(95% CI {lo:+.1f}% to {hi:+.1f}%)"
            )
        else:
            lines.append(
                "improvement %: not reported — control baseline is not "
                "reliably positive, so a ratio would be unstable; use the "
                "absolute difference above instead"
            )
        return "\n".join(lines)


def _welch_p_value(x: np.ndarray, y: np.ndarray) -> float:
    """Two-sided Welch's t-test p-value.

    Uses scipy's t distribution when available; otherwise falls back to
    a normal approximation, which is accurate for the df sizes this
    analysis sees (and the bootstrap CI is the primary interval anyway).
    """
    nx, ny = len(x), len(y)
    vx, vy = x.var(ddof=1), y.var(ddof=1)
    se2 = vx / nx + vy / ny
    if se2 == 0:
        return 1.0
    t = (x.mean() - y.mean()) / np.sqrt(se2)
    df = se2**2 / ((vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
    try:
        from scipy import stats

        return float(2.0 * stats.t.sf(abs(t), df))
    except ImportError:
        from math import erf, sqrt

        return float(2.0 * (1.0 - 0.5 * (1.0 + erf(abs(t) / sqrt(2.0)))))


def compare_arms(
    gains_treatment: Sequence[float],
    gains_control: Sequence[float],
    n_boot: int = 10_000,
    seed: int | None = 0,
) -> ArmComparison:
    """Compare per-user learning gains between arms.

    Reports the raw difference with a bootstrap 95% CI, Cohen's d and a
    Welch t-test p-value. The percentage improvement (the CV's ``[X]%``)
    is reported **only when the control mean gain is positive** —
    otherwise a ratio is meaningless and the absolute difference is the
    honest number.
    """
    t = np.asarray(list(gains_treatment), dtype=float)
    c = np.asarray(list(gains_control), dtype=float)
    if len(t) < 2 or len(c) < 2:
        raise ValueError(
            f"Need at least 2 users per arm (got treatment={len(t)}, control={len(c)})"
        )
    rng = np.random.default_rng(seed)

    diff = float(t.mean() - c.mean())
    boot_t = rng.choice(t, size=(n_boot, len(t)), replace=True).mean(axis=1)
    boot_c = rng.choice(c, size=(n_boot, len(c)), replace=True).mean(axis=1)
    boot_diff = boot_t - boot_c
    diff_ci = (float(np.percentile(boot_diff, 2.5)), float(np.percentile(boot_diff, 97.5)))

    pct = pct_ci = None
    if c.mean() > 0:
        pct = float(100.0 * diff / c.mean())
        valid = boot_c > 0
        if valid.sum() >= n_boot * 0.99:  # ratio stable enough to report
            boot_pct = 100.0 * (boot_t[valid] - boot_c[valid]) / boot_c[valid]
            pct_ci = (
                float(np.percentile(boot_pct, 2.5)),
                float(np.percentile(boot_pct, 97.5)),
            )
        else:
            pct = None  # control mean too close to zero: ratio unstable

    pooled_sd = np.sqrt(
        ((len(t) - 1) * t.var(ddof=1) + (len(c) - 1) * c.var(ddof=1))
        / (len(t) + len(c) - 2)
    )
    cohens_d = float(diff / pooled_sd) if pooled_sd > 0 else 0.0

    return ArmComparison(
        n_treatment=len(t),
        n_control=len(c),
        mean_treatment=float(t.mean()),
        mean_control=float(c.mean()),
        diff=diff,
        diff_ci95=diff_ci,
        pct_improvement=pct,
        pct_improvement_ci95=pct_ci,
        cohens_d=cohens_d,
        p_value=_welch_p_value(t, c),
    )
