# Copyright (c) 2024, RTE (https://www.rte-france.com)
#
# See AUTHORS.txt
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0
#
# This file is part of the Antares project.

"""
Operators that allow temporal manipulation of expressions
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Tuple


@dataclass(frozen=True)
class TimeOperator(ABC):
    """
    A time operator on an expression is charactirized by two attributes:
        - time_ids: int, List[int] or range, is the list of time indices to which the operator applies
        - is_rolling: bool, if true, this means that the time_ids are to be understood relatively to the current timestep of the context AND that the represented expression will have to be instanciated for all timesteps. Otherwise, the time_ids are "absolute" times and the expression only has to be instantiated once.
    """

    time_ids: List[int]

    @classmethod
    @abstractmethod
    def rolling(cls) -> bool:
        raise NotImplementedError

    def __post_init__(self) -> None:
        if isinstance(self.time_ids, int):
            object.__setattr__(self, "time_ids", [self.time_ids])
        elif isinstance(self.time_ids, range):
            object.__setattr__(self, "time_ids", list(self.time_ids))

    def key(self) -> Tuple[int, ...]:
        return tuple(self.time_ids)

    def size(self) -> int:
        return len(self.time_ids)


@dataclass(frozen=True)
class TimeShift(TimeOperator):
    """
    Time shift of variables

    Examples:
        >>> x.shift([1, 2, 4]) represents the vector of variables (x[t+1], x[t+2], x[t+4])
    """

    def __str__(self) -> str:
        return f"shift({self.time_ids})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, TimeShift) and self.time_ids == other.time_ids

    def __hash__(self) -> int:
        return hash(self.key())

    @classmethod
    def rolling(cls) -> bool:
        return True


@dataclass(frozen=True)
class TimeEvaluation(TimeOperator):
    """
    Absolute time evalaution of variables

    Examples:
        >>> x.eval([1, 2, 4]) represents the vector of variables (x[1], x[2], x[4])
    """

    def __str__(self) -> str:
        return f"eval({self.time_ids})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, TimeEvaluation) and self.time_ids == other.time_ids

    def __hash__(self) -> int:
        return hash(self.key())

    @classmethod
    def rolling(cls) -> bool:
        return False


@dataclass(frozen=True)
class TimeAggregator:
    stay_roll: bool

    def size(self) -> int:
        return 1


@dataclass(frozen=True)
class TimeSum(TimeAggregator):
    def __str__(self) -> str:
        return f"sum({self.stay_roll})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, TimeSum) and self.stay_roll == other.stay_roll
