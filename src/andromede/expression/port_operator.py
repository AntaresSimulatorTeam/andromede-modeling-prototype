"""
Operators that allow port manipulation of expressions
"""

from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class PortOperator(ABC):
    pass


@dataclass(frozen=True)
class PortAggregator:
    pass


@dataclass(frozen=True)
class PortSum(PortAggregator):
    pass
