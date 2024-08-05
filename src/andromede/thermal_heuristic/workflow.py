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

from dataclasses import dataclass

import ortools.linear_solver.pywraplp as pywraplp

from andromede.simulation import (
    BlockBorderManagement,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.study import DataBase, Network


@dataclass
class SolvingParameters:
    solver_parameters: pywraplp.MPSolverParameters = pywraplp.MPSolverParameters()
    expected_status: str = pywraplp.Solver.OPTIMAL


class ResolutionStep:
    def __init__(
        self,
        timesteps: list[int],
        scenarios: list[int],
        database: DataBase,
        network: Network,
    ) -> None:
        problem = build_problem(
            network,
            database,
            TimeBlock(1, timesteps),
            scenarios,
            border_management=BlockBorderManagement.CYCLE,
        )

        self.problem = problem

    def solve(
        self,
        solving_parameters: SolvingParameters,
    ) -> None:
        self.status = self.problem.solver.Solve(solving_parameters.solver_parameters)

        self.output = OutputValues(self.problem)
        self.objective = self.problem.solver.Objective().Value()

        assert self.status == solving_parameters.expected_status
