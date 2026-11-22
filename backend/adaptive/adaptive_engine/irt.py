"""Item Response Theory (IRT) primitives: the 2PL model, ability
estimation, and item calibration.

Model
-----
The two-parameter logistic (2PL) model gives the probability that a
learner with ability ``theta`` answers an item with difficulty ``b`` and
discrimination ``a`` correctly:

    P(correct | theta) = 1 / (1 + exp(-a * (theta - b)))

Setting ``a = 1`` for every item recovers the one-parameter (Rasch/1PL)
model. All functions below are NumPy-vectorised over items.

Ability estimation
------------------
EAP (expected a posteriori): the posterior mean of theta under a
standard-normal prior, computed by quadrature over a fixed grid. EAP is
used instead of raw maximum likelihood because the MLE diverges on
all-correct/all-wrong response patterns, and the posterior standard
deviation doubles as the uncertainty estimate.

Item calibration
----------------
:func:`calibrate` fits item parameters from a response matrix by
marginal maximum likelihood using the Bock-Aitkin EM algorithm (the
estimator standard IRT software uses). E-step: each learner's posterior
over an ability quadrature grid, accumulated into expected counts per
item per grid point. M-step: Newton-Raphson refit of each item against
those expected counts. Unlike joint ML, this integrates ability out, so
item estimates keep improving as learners are added. The simulation
tests check recovery of known parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "probability",
    "fisher_information",
    "estimate_ability",
    "AbilityEstimate",
    "calibrate",
]

# Quadrature grid for EAP: 121 points over [-6, 6] is plenty for the
# smooth integrands involved.
_GRID = np.linspace(-6.0, 6.0, 121)
_PRIOR = np.exp(-0.5 * _GRID**2)  # unnormalised N(0, 1) prior


def probability(
    theta: float | np.ndarray,
    difficulty: float | np.ndarray,
    discrimination: float | np.ndarray = 1.0,
) -> np.ndarray:
    """2PL probability of a correct response. Broadcasts like NumPy."""
    z = np.asarray(discrimination) * (np.asarray(theta) - np.asarray(difficulty))
    # Clip to keep exp() well-behaved; |z| = 35 is already p = 1 - 6e-16.
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))


def fisher_information(
    theta: float | np.ndarray,
    difficulty: float | np.ndarray,
    discrimination: float | np.ndarray = 1.0,
) -> np.ndarray:
    """Fisher information the item carries about theta: ``a^2 * p * (1-p)``.

    Maximised when the item's difficulty matches the learner's ability,
    which is what adaptive selection exploits.
    """
    p = probability(theta, difficulty, discrimination)
    return np.asarray(discrimination) ** 2 * p * (1.0 - p)


@dataclass(frozen=True)
class AbilityEstimate:
    """Point estimate of ability with its uncertainty."""

    theta: float  # EAP posterior mean
    se: float  # posterior standard deviation

    def __iter__(self):  # allow  theta, se = estimate_ability(...)
        yield self.theta
        yield self.se


def estimate_ability(
    correct: np.ndarray,
    difficulty: np.ndarray,
    discrimination: np.ndarray | None = None,
) -> AbilityEstimate:
    """EAP estimate of ability from a set of scored responses.

    Parameters
    ----------
    correct:
        Boolean/0-1 array, one entry per answered item.
    difficulty, discrimination:
        Matching arrays of the answered items' parameters.
        ``discrimination`` defaults to all ones (1PL).

    Returns
    -------
    AbilityEstimate
        Posterior mean and posterior SD of theta. With zero responses
        this is simply the prior: ``theta=0.0, se=1.0``.
    """
    correct = np.asarray(correct, dtype=float)
    if correct.size == 0:
        return AbilityEstimate(theta=0.0, se=1.0)
    difficulty = np.asarray(difficulty, dtype=float)
    if discrimination is None:
        discrimination = np.ones_like(difficulty)
    else:
        discrimination = np.asarray(discrimination, dtype=float)

    # log-likelihood of the response pattern at each grid point
    # shape: (grid, items)
    p = probability(_GRID[:, None], difficulty[None, :], discrimination[None, :])
    log_lik = correct[None, :] * np.log(p) + (1.0 - correct[None, :]) * np.log1p(-p)
    log_post = log_lik.sum(axis=1) + np.log(_PRIOR)
    log_post -= log_post.max()  # numerical stability
    post = np.exp(log_post)
    post /= post.sum()

    theta = float(np.dot(post, _GRID))
    var = float(np.dot(post, (_GRID - theta) ** 2))
    return AbilityEstimate(theta=theta, se=float(np.sqrt(var)))


# Coarser grid for EM (the E-step is O(learners x grid x items)).
_EM_GRID = np.linspace(-6.0, 6.0, 61)
_EM_PRIOR = np.exp(-0.5 * _EM_GRID**2)
_EM_PRIOR = _EM_PRIOR / _EM_PRIOR.sum()


def _m_step_item(
    n_bar: np.ndarray,
    r_bar: np.ndarray,
    b: float,
    a: float,
    fit_discrimination: bool,
    n_iter: int = 10,
) -> tuple[float, float]:
    """Newton-Raphson fit of one item's (b, a) to the expected counts at
    each quadrature node (`n_bar` learners, `r_bar` of them correct)."""
    for _ in range(n_iter):
        p = probability(_EM_GRID, b, a)
        w = n_bar * p * (1.0 - p)
        resid = r_bar - n_bar * p
        # dL/db = -a * sum(resid);  -d2L/db2 ~ a^2 * sum(w)
        g_b = -a * resid.sum()
        h_b = a**2 * w.sum() + 1e-6
        b_new = float(np.clip(b + g_b / h_b, -5.0, 5.0))
        if fit_discrimination:
            x = _EM_GRID - b
            g_a = (resid * x).sum()
            h_a = (w * x**2).sum() + 1e-6
            a_new = float(np.clip(a + g_a / h_a, 0.2, 3.0))
        else:
            a_new = a
        if abs(b_new - b) < 1e-5 and abs(a_new - a) < 1e-5:
            return b_new, a_new
        b, a = b_new, a_new
    return b, a


def calibrate(
    response_matrix: np.ndarray,
    model: str = "2PL",
    n_iter: int = 40,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calibrate item parameters from a (learners x items) response
    matrix by marginal maximum likelihood (Bock–Aitkin EM).

    Parameters
    ----------
    response_matrix:
        Array of shape ``(n_learners, n_items)``: 1 = correct,
        0 = incorrect, ``np.nan`` = not answered.
    model:
        ``"2PL"`` (fit difficulty and discrimination) or ``"1PL"``
        (difficulty only, discrimination fixed at 1).
    n_iter:
        EM iterations.

    Returns
    -------
    (difficulty, discrimination, theta):
        Per-item ``b`` and ``a`` arrays, and per-learner EAP thetas.
        The theta scale is anchored by the N(0, 1) ability prior.
    """
    if model not in ("1PL", "2PL"):
        raise ValueError(f"model must be '1PL' or '2PL', got {model!r}")
    resp = np.asarray(response_matrix, dtype=float)
    n_learners, n_items = resp.shape
    answered = ~np.isnan(resp)
    if not answered.any():
        raise ValueError("response matrix contains no answered items")
    x = np.nan_to_num(resp, nan=0.0)

    # Initialise difficulties from raw proportion-correct (logit).
    p_correct = np.clip(np.nan_to_num(np.nanmean(resp, axis=0), nan=0.5), 0.02, 0.98)
    b = -np.log(p_correct / (1.0 - p_correct))
    a = np.ones(n_items)
    posterior = np.tile(_EM_PRIOR, (n_learners, 1))

    for _ in range(n_iter):
        # ----- E-step: learner posteriors over the quadrature grid.
        p = probability(_EM_GRID[:, None], b[None, :], a[None, :])  # (Q, I)
        log_p, log_q = np.log(p), np.log1p(-p)
        # (L, Q) log-likelihood: sum over each learner's answered items.
        log_lik = np.einsum("li,qi->lq", answered * x, log_p) + np.einsum(
            "li,qi->lq", answered * (1.0 - x), log_q
        )
        log_post = log_lik + np.log(_EM_PRIOR)[None, :]
        log_post -= log_post.max(axis=1, keepdims=True)
        posterior = np.exp(log_post)
        posterior /= posterior.sum(axis=1, keepdims=True)

        # ----- M-step: refit each item to its expected counts.
        for j in range(n_items):
            mask = answered[:, j]
            if mask.sum() < 3:
                continue
            n_bar = posterior[mask].sum(axis=0)
            r_bar = (posterior[mask] * x[mask, j][:, None]).sum(axis=0)
            b[j], a[j] = _m_step_item(
                n_bar, r_bar, b[j], a[j], fit_discrimination=(model == "2PL")
            )

    theta = posterior @ _EM_GRID
    return b, a, theta
