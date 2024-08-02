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

import ortools.linear_solver.pywraplp as pywraplp

from andromede.simulation import (
    BlockBorderManagement,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.study import (
    DataBase,
    Network,
)


class ResolutionStep:
    def __init__(
        self,
        timesteps: list[int],
        scenarios: list[int],
        database: DataBase,
        network: Network,
    ) -> None:
        self.timesteps = timesteps
        self.scenarios = scenarios

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
        solver_parameters: pywraplp.MPSolverParameters = pywraplp.MPSolverParameters(),
    ) -> None:
        status = self.problem.solver.Solve(solver_parameters)

        self.output = OutputValues(self.problem)
        self.objective = self.problem.solver.Objective().Value()

        assert status == pywraplp.Solver.OPTIMAL


class ConnectionBetweenResolutionSteps:
    def __init__(self) -> None:
        pass


class Workflow:
    def __init__(self) -> None:
        pass
