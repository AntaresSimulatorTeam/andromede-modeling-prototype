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
from typing import List, Tuple

import ortools.linear_solver.pywraplp as pywraplp

from andromede.hydro_heuristic.data import (
    DataAggregatorParameters,
    HydroHeuristicData,
    HydroHeuristicParameters,
    ReservoirParameters,
    get_database,
)
from andromede.model import Model
from andromede.simulation import (
    BlockBorderManagement,
    OptimizationProblem,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.study import DataBase, Network, create_component


@dataclass(frozen=True)
class SolvingOutput:
    status: str
    objective: float


@dataclass(frozen=True)
class OutputHeuristic:
    generating: List[float]
    level: float


def build_hydro_heuristic_problem(
    database: DataBase, heuristic_model: Model, timesteps: int, id: str = "H"
) -> OptimizationProblem:
    hydro = create_component(model=heuristic_model, id=id)
    network = Network("test")
    network.add_component(hydro)

    problem = build_problem(
        network,
        database,
        TimeBlock(1, list(range(timesteps))),
        1,
        border_management=(BlockBorderManagement.CYCLE),
    )

    return problem


def get_default_solver_parameters() -> pywraplp.MPSolverParameters:
    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    return parameters


def retrieve_important_heuristic_output(
    heuristic_problem: OptimizationProblem,
    id: str = "H",
) -> OutputHeuristic:
    output = OutputValues(heuristic_problem)

    heuristic_output = OutputHeuristic(
        output.component(id).var("generating").value[0],  # type:ignore
        output.component(id).var("level").value[0][-1],  # type:ignore
    )

    return heuristic_output


def update_initial_level(
    reservoir_data: ReservoirParameters, daily_output: OutputHeuristic
) -> None:
    reservoir_data.initial_level = daily_output.level
