"""
Operators that allow manipulation of expressions with respect to scenarios
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioOperator(ABC):
    def __str__(self) -> str:
        return NotImplemented

    @classmethod
    @abstractmethod
    def degree(cls) -> int:
        raise NotImplementedError


@dataclass(frozen=True)
class Expectation(ScenarioOperator):
    def __str__(self) -> str:
        return "expec()"

    @classmethod
    def degree(cls) -> int:
        return 1


@dataclass(frozen=True)
class Variance(ScenarioOperator):
    def __str__(self) -> str:
        return "variance()"

    @classmethod
    def degree(cls) -> int:
        return 2
