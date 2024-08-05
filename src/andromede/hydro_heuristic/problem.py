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
import pandas as pd

from andromede.hydro_heuristic.data import (
    DataAggregatorParameters,
    HydroHeuristicData,
    HydroHeuristicParameters,
    ReservoirParameters,
)
from andromede.model import Model
from andromede.simulation import (
    BlockBorderManagement,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    TimeIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
    create_component,
)


@dataclass
class SolvingOutput:
    status: str
    objective: float


@dataclass
class OutputHeuristic:
    generating: list[float]
    level: float


class HydroHeuristicProblem:
    def __init__(self, hydro_data: HydroHeuristicData, heuristic_model: Model) -> None:
        self.hydro_data = hydro_data
        self.id = "H"
        database = self.generate_database()

        hydro = create_component(
            model=heuristic_model,
            id=self.id,
        )

        network = Network("test")
        network.add_component(hydro)

        problem = build_problem(
            network,
            database,
            TimeBlock(1, [i for i in range(len(hydro_data.target))]),
            1,
            border_management=(BlockBorderManagement.CYCLE),
        )

        self.problem = problem

    def solve_hydro_problem(self) -> tuple[SolvingOutput, OutputHeuristic]:
        parameters = pywraplp.MPSolverParameters()
        parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
        parameters.SetIntegerParam(parameters.SCALING, 0)

        status = self.problem.solver.Solve(parameters)

        output = OutputValues(self.problem)

        return (
            SolvingOutput(status, self.problem.solver.Objective().Value()),
            OutputHeuristic(
                output.component(self.id).var("generating").value[0],  # type:ignore
                output.component(self.id).var("level").value[0][-1],  # type:ignore
            ),
        )

    def generate_database(
        self,
    ) -> DataBase:
        database = DataBase()

        database.add_data(
            self.id, "capacity", ConstantData(self.hydro_data.reservoir_data.capacity)
        )
        database.add_data(
            self.id,
            "initial_level",
            ConstantData(self.hydro_data.reservoir_data.initial_level),
        )

        inflow_data = pd.DataFrame(
            self.hydro_data.inflow,
            index=[i for i in range(len(self.hydro_data.inflow))],
            columns=[0],
        )
        database.add_data(self.id, "inflow", TimeScenarioSeriesData(inflow_data))

        target_data = pd.DataFrame(
            self.hydro_data.target,
            index=[i for i in range(len(self.hydro_data.target))],
            columns=[0],
        )
        database.add_data(
            self.id, "generating_target", TimeScenarioSeriesData(target_data)
        )
        database.add_data(
            self.id, "overall_target", ConstantData(sum(self.hydro_data.target))
        )

        database.add_data(
            self.id,
            "lower_rule_curve",
            TimeSeriesData(
                {
                    TimeIndex(i): self.hydro_data.lower_rule_curve[i]
                    * self.hydro_data.reservoir_data.capacity
                    for i in range(len(self.hydro_data.lower_rule_curve))
                }
            ),
        )
        database.add_data(
            self.id,
            "upper_rule_curve",
            TimeSeriesData(
                {
                    TimeIndex(i): self.hydro_data.upper_rule_curve[i]
                    * self.hydro_data.reservoir_data.capacity
                    for i in range(len(self.hydro_data.lower_rule_curve))
                }
            ),
        )
        database.add_data(self.id, "min_generating", ConstantData(0))

        database.add_data(
            self.id,
            "max_generating",
            TimeSeriesData(
                {
                    TimeIndex(i): self.hydro_data.max_generating[i]
                    for i in range(len(self.hydro_data.max_generating))
                }
            ),
        )

        database.add_data(
            self.id,
            "max_epsilon",
            TimeSeriesData(
                {
                    TimeIndex(i): (
                        self.hydro_data.reservoir_data.capacity if i == 0 else 0
                    )
                    for i in range(len(self.hydro_data.max_generating))
                }
            ),
        )

        return database


def optimize_target(
    heuristic_parameters: HydroHeuristicParameters,
    data_aggregator_parameters: DataAggregatorParameters,
    reservoir_data: ReservoirParameters,
    heuristic_model: Model,
) -> tuple[SolvingOutput, OutputHeuristic]:
    # Récupération des données
    data = HydroHeuristicData(
        data_aggregator_parameters,
        reservoir_data,
    )
    # Calcul de la préallocation
    data.compute_target(heuristic_parameters)

    # Ajustement de la réapartition
    heuristic_problem = HydroHeuristicProblem(
        hydro_data=data, heuristic_model=heuristic_model
    )

    solving_output, heuristic_output = heuristic_problem.solve_hydro_problem()

    return solving_output, heuristic_output
