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


def library_thermal_problem(
    port_types: Iterable[PortType],
    models: List[Model],
    lp_relaxation: bool,
    fast: bool,
    initial_thermal_model: Model,
) -> Library:
    thermal_model = edit_thermal_model(lp_relaxation, fast, initial_thermal_model)
    lib = library(
        port_types=port_types,
        models=models + [thermal_model],
    )
    return lib


class ThermalProblemBuilder:

    def __init__(
        self,
        number_hours: int,
        lp_relaxation: bool,
        fast: bool,
        data_dir: Path,
        initial_thermal_model: Model,
        port_types: List[PortType],
        models: List[Model],
    ) -> None:
        lib = library_thermal_problem(
            port_types, models, lp_relaxation, fast, initial_thermal_model
        )

        self.network = get_network(data_dir / "components.yml", lib)

        self.database = get_database(
            data_dir,
            "components.yml",
            get_cluster_id(self.network, initial_thermal_model.id),
            number_hours,
        )
        self.initial_thermal_model = initial_thermal_model
        self.number_hours = number_hours
        self.data_dir = data_dir

    def get_main_problem(
        self, week: int, scenario: int, lower_bound: Dict[str, AbstractDataStructure]
    ) -> OptimizationProblem:
        modify_lower_bound_of_cluster(
            lower_bound,
            self.database,
            get_cluster_id(self.network, self.initial_thermal_model.id),
        )

        problem = build_problem(
            self.network,
            self.database,
            TimeBlock(
                1, list(range(week * self.number_hours, (week + 1) * self.number_hours))
            ),
            [scenario],
            border_management=BlockBorderManagement.CYCLE,
        )

        return problem

    def get_problem_accurate_heuristic(
        self,
        lower_bound: Dict[str, AbstractDataStructure],
        week: int,
        scenario: int,
        cluster_id: str,
    ) -> OptimizationProblem:
        thermal_model_builder = HeuristicAccurateModelBuilder(
            self.initial_thermal_model
        )

        cluster = create_component(model=thermal_model_builder.model, id=cluster_id)

        network = Network("test")
        network.add_component(cluster)

        modify_lower_bound_of_cluster(
            lower_bound,
            self.database,
            [cluster_id],
        )

        problem = build_problem(
            network,
            self.database,
            TimeBlock(
                1, list(range(week * self.number_hours, (week + 1) * self.number_hours))
            ),
            [scenario],
            border_management=BlockBorderManagement.CYCLE,
        )

        return problem

    def get_problem_fast_heuristic(
        self,
        lower_bound: List[float],
        thermal_cluster: str,
        week: int,
        scenario: int,
    ) -> OptimizationProblem:
        delta, pmax, nmax, _, _, number_blocks = self.get_data_fast_heuristic(
            thermal_cluster, week, scenario
        )

        database = self.get_database_fast_heuristic(
            lower_bound, delta, pmax, nmax, number_blocks
        )

        network = self.get_network_fast_heuristic(delta, number_blocks)

        problem = build_problem(
            network,
            database,
            TimeBlock(1, [i for i in range(self.number_hours)]),
            1,
            border_management=BlockBorderManagement.CYCLE,
        )

        return problem

    def get_database_fast_heuristic(
        self,
        lower_bound: list[float],
        delta: int,
        pmax: int,
        nmax: int,
        number_blocks: int,
    ) -> DataBase:
        database = DataBase()

        database.add_data("B", "n_max", ConstantData(nmax))
        database.add_data("B", "delta", ConstantData(delta))

        nb_on_1 = np.ceil(
            np.round(
                np.array(lower_bound) / pmax,
                12,
            )
        )

        database.add_data(
            "B",
            "n_guide",
            TimeSeriesData(
                {TimeIndex(i): nb_on_1[i] for i in range(self.number_hours)}
            ),
        )
        for h in range(delta):
            start_ajust = self.number_hours - delta + h
            database.add_data(
                "B",
                f"alpha_ajust_{h}",
                TimeSeriesData(
                    {
                        TimeIndex(t): 1 if (t >= start_ajust) or (t < h) else 0
                        for t in range(self.number_hours)
                    }
                ),
            )
            for k in range(number_blocks):
                start_k = k * delta + h
                end_k = min(start_ajust, (k + 1) * delta + h)
                database.add_data(
                    "B",
                    f"alpha_{k}_{h}",
                    TimeSeriesData(
                        {
                            TimeIndex(t): 1 if (t >= start_k) and (t < end_k) else 0
                            for t in range(self.number_hours)
                        }
                    ),
                )

        return database

    def get_data_fast_heuristic(
        self, thermal_cluster: str, week: int, scenario: int
    ) -> tuple[int, int, int, int, list[float], int]:
        data = get_data(
            data_dir=self.data_dir,
            yml_file="components.yml",
            id_cluster=thermal_cluster,
        )
        delta = int(max(data["d_min_up"], data["d_min_down"]))
        pmax = data["p_max"]
        pmin = data["p_min"]
        nmax = data["nb_units_max"]
        if type(data["max_generating"]) is float:
            pdispo = np.repeat(
                data["max_generating"],
                self.number_hours,
            ).reshape((self.number_hours, 1))
        else:
            pdispo = data["max_generating"][
                self.number_hours * week : self.number_hours * (week + 1), scenario
            ].reshape((self.number_hours, 1))

        number_blocks = self.number_hours // delta

        return delta, pmax, nmax, pmin, list(pdispo), number_blocks

    def get_output_heuristic_fast(
        self,
        problem: OptimizationProblem,
        week: int,
        scenario: int,
        thermal_cluster: str,
    ) -> pd.DataFrame:

        _, _, _, pmin, pdispo, _ = self.get_data_fast_heuristic(
            thermal_cluster, week, scenario
        )

        parameters = pywraplp.MPSolverParameters()
        parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
        parameters.SetIntegerParam(parameters.SCALING, 0)
        parameters.SetDoubleParam(parameters.RELATIVE_MIP_GAP, 1e-7)
        problem.solver.EnableOutput()

        status = problem.solver.Solve(parameters)

        assert status == problem.solver.OPTIMAL

        output_heuristic = OutputValues(problem)
        n_heuristic = np.array(
            output_heuristic.component("B").var("n").value[0]  # type:ignore
        ).reshape((self.number_hours, 1))

        mingen_heuristic = pd.DataFrame(
            np.minimum(
                n_heuristic * pmin, np.array(pdispo).reshape((self.number_hours, 1))
            ),
            index=[
                list(range(week * self.number_hours, (week + 1) * self.number_hours))
            ],
            columns=[scenario],
        )

        return mingen_heuristic

    def get_network_fast_heuristic(self, delta: int, number_blocks: int) -> Network:
        block = create_component(
            model=HeuristicFastModelBuilder(number_blocks, delta=delta).model, id="B"
        )

        network = Network("test")
        network.add_component(block)
        return network


def modify_lower_bound_of_cluster(
    lower_bound: Dict[str, AbstractDataStructure],
    database: DataBase,
    list_cluster_id: List[str],
) -> None:
    for cluster_id in list_cluster_id:
        database.add_data(cluster_id, "nb_units_min", lower_bound[cluster_id])
        database.add_data(cluster_id, "min_generating", lower_bound[cluster_id])


def complete_database_with_cluster_parameters(
    database: DataBase, list_cluster_id: List[str], dir_path: Path, hours_in_week: int
) -> None:
    for cluster_id in list_cluster_id:
        data = get_data(
            dir_path,
            "components.yml",
            cluster_id,
        )

        if type(data["max_generating"]) is float:
            database.add_data(
                cluster_id,
                "max_failure",
                ConstantData(0),
            )
            database.add_data(
                cluster_id,
                "nb_units_max_min_down_time",
                ConstantData(data["nb_units_max"]),
            )

        else:
            max_units, max_failures, nb_units_max_min_down_time = (
                compute_cluster_parameters(hours_in_week, data)
            )
            database.add_data(
                cluster_id,
                "nb_units_max",
                TimeScenarioSeriesData(max_units),
            )
            database.add_data(
                cluster_id,
                "max_failure",
                TimeScenarioSeriesData(max_failures),
            )
            database.add_data(
                cluster_id,
                "nb_units_max_min_down_time",
                TimeScenarioSeriesData(nb_units_max_min_down_time),
            )


def compute_cluster_parameters(
    hours_in_week: int, data: Dict
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    max_generating_shape = data["max_generating"].shape
    if len(max_generating_shape) == 1:
        max_generating = pd.DataFrame(
            data["max_generating"].reshape((max_generating_shape[0], 1))
        )
    else:
        max_generating = pd.DataFrame(data["max_generating"])
    max_units = get_max_unit(data["p_max"], data["nb_units_max"], max_generating)
    max_failures = get_max_failures(max_units, hours_in_week)
    nb_units_max_min_down_time = get_max_unit_for_min_down_time(
        int(max(data["d_min_up"], data["d_min_down"])), max_units, hours_in_week
    )

    return max_units, max_failures, nb_units_max_min_down_time


def get_cluster_id(network: Network, cluster_model_id: str) -> list[str]:
    return [c.id for c in network.components if c.model.id == cluster_model_id]


def get_database(
    data_dir: Path, yml_file: str, cluster_id: List[str], hours_in_week: int
) -> DataBase:
    components_file = get_input_components(data_dir / yml_file)
    database = build_data_base(components_file, data_dir)

    complete_database_with_cluster_parameters(
        database,
        list_cluster_id=cluster_id,
        dir_path=data_dir,
        hours_in_week=hours_in_week,
    )

    return database


def get_network(compo_file: Path, lib: Library) -> Network:
    components_file = get_input_components(compo_file)
    components_input = resolve_components_and_cnx(components_file, lib)
    network = build_network(components_input)
    return network


def get_input_components(compo_file: Path) -> InputComponents:
    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    return components_file


def edit_thermal_model(
    lp_relaxation: bool, fast: bool, initial_thermal_model: Model
) -> Model:
    if fast:
        thermal_model = FastModelBuilder(initial_thermal_model).model
    elif lp_relaxation:
        thermal_model = AccurateModelBuilder(initial_thermal_model).model
    else:
        thermal_model = initial_thermal_model
    return thermal_model


def get_data(
    data_dir: Path,
    yml_file: str,
    id_cluster: str,
) -> Dict:
    compo_file = data_dir / yml_file

    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    cluster = [c for c in components_file.components if c.id == id_cluster][0]
    parameters = {
        p.name: (
            p.value
            if p.value is not None
            else np.loadtxt(data_dir / (p.timeseries + ".txt"))  # type:ignore
        )
        for p in cluster.parameters  # type:ignore
    }
    return parameters  # type:ignore
