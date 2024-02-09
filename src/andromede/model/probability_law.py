"""
Describes probability distributions used in the models
"""

from abc import ABC
from dataclasses import dataclass
from typing import List

import numpy as np

from andromede.expression.expression import ExpressionNode


class AbstractProbabilityLaw(ABC):
    def get_sample(self, size: int) -> List[float]:
        return NotImplemented


@dataclass(frozen=True)
class Normal(AbstractProbabilityLaw):
    mean: ExpressionNode
    standard_deviation: ExpressionNode

    def get_sample(self, size: int) -> List[float]:
        return NotImplemented


@dataclass(frozen=True)
class Uniform(AbstractProbabilityLaw):
    lower_bound: ExpressionNode
    upper_bound: ExpressionNode

    def get_sample(self, size: int) -> List[float]:
        return NotImplemented


@dataclass(frozen=True)
class UniformIntegers(AbstractProbabilityLaw):
    lower_bound: ExpressionNode
    upper_bound: ExpressionNode

    def get_sample(self, size: int) -> List[float]:
        return NotImplemented
