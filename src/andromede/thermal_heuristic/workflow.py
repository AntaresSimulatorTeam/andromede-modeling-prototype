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

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pandas as pd

from andromede.model import Model, PortType
from andromede.model.library import Library, library
from andromede.simulation import (
    BlockBorderManagement,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.simulation.optimization import OptimizationProblem
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    TimeIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
    create_component,
)
from andromede.study.data import AbstractDataStructure
from andromede.study.parsing import InputComponents, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    resolve_components_and_cnx,
)
from andromede.thermal_heuristic.data import (
    get_max_failures,
    get_max_unit,
    get_max_unit_for_min_down_time,
)
from andromede.thermal_heuristic.model import (
    AccurateModelBuilder,
    FastModelBuilder,
    HeuristicAccurateModelBuilder,
    HeuristicFastModelBuilder,
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
    ) -> int:
        status = self.problem.solver.Solve(solver_parameters)

        self.output = OutputValues(self.problem)
        self.objective = self.problem.solver.Objective().Value()

        return status


class ConnectionBetweenResolutionSteps:
    def __init__(self) -> None:
        pass


class Workflow:
    def __init__(self) -> None:
        pass
