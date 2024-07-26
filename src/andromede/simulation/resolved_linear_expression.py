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
Specific modelling for "resolved" linear expressions,
with only variables and literal coefficients.
"""

from dataclasses import dataclass, field
from typing import List

import ortools.linear_solver.pywraplp as lp


@dataclass(frozen=True)
class ResolvedTerm:
    """
    Represents a term where parameters and variables id have been resolved, in the form of couple (coefficient, variable_id)
    """

    coefficient: float
    variable: lp.Variable


@dataclass
class ResolvedLinearExpression:
    """
    Represents a linear expression where parameters and variables id have been resolved, in the form of couple (coefficient, variable_id) and a constant
    """

    terms: List[ResolvedTerm] = field(default_factory=list)
    constant: float = field(default=0)
