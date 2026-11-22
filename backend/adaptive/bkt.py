"""
Actualización Bayesian Knowledge Tracing (BKT).

Adaptado del algoritmo BKT de OATutor.
Copyright (c) 2023 Zachary A. Pardos - CAHL research lab.
Licencia MIT: consultar LICENSE-OATutor.

Los parámetros predeterminados son experimentales y deben calibrarse
con datos reales antes de interpretar las estimaciones como medidas validadas.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BKTParameters:
    initial_mastery: float = 0.10
    learning_transition: float = 0.10
    guess: float = 0.20
    slip: float = 0.10

    def __post_init__(self):
        for name, value in vars(self).items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} debe estar entre 0 y 1.")
        if self.guess + self.slip >= 1.0:
            raise ValueError("La suma de guess y slip debe ser menor que 1.")


def update_mastery(
    mastery: float,
    correct: bool,
    parameters: BKTParameters | None = None,
) -> float:
    """Actualiza la probabilidad de dominio tras una respuesta."""
    params = parameters or BKTParameters()

    if not 0.0 <= mastery <= 1.0:
        raise ValueError("mastery debe estar entre 0 y 1.")

    if correct:
        numerator = mastery * (1.0 - params.slip)
        alternative = (1.0 - mastery) * params.guess
    else:
        numerator = mastery * params.slip
        alternative = (1.0 - mastery) * (1.0 - params.guess)

    denominator = numerator + alternative

    if denominator == 0.0:
        posterior = mastery
    else:
        posterior = numerator / denominator

    return posterior + (1.0 - posterior) * params.learning_transition
