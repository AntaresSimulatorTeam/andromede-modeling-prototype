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

from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    DEMAND_MODEL,
    NODE_BALANCE_MODEL,
    SPILLAGE_MODEL,
    UNSUPPLIED_ENERGY_MODEL,
)
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
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP


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


# class ThermalProblemBuilder:

#     def __init__(
#         self,
#         lower_bound: Dict[str, AbstractDataStructure],
#         number_hours: int,
#         lp_relaxation: bool,
#         fast: bool,
#         data_dir: Path,
#         week: int,
#         scenario: int,
#     ) -> None:
#         pass


def create_main_problem(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    lp_relaxation: bool,
    fast: bool,
    data_dir: Path,
    week: int,
    scenario: int,
    initial_thermal_model: Model = THERMAL_CLUSTER_MODEL_MILP,
    port_types: List[PortType] = [BALANCE_PORT_TYPE],
    models: List[Model] = [
        NODE_BALANCE_MODEL,
        DEMAND_MODEL,
        SPILLAGE_MODEL,
        UNSUPPLIED_ENERGY_MODEL,
    ],
) -> OptimizationProblem:
    lib = library_thermal_problem(
        port_types, models, lp_relaxation, fast, initial_thermal_model
    )

    network = get_network(data_dir / "components.yml", lib)

    database = get_database(
        data_dir,
        "components.yml",
        get_cluster_id(network, initial_thermal_model.id),
        number_hours,
    )

    modify_lower_bound_of_cluster(
        lower_bound, database, get_cluster_id(network, initial_thermal_model.id)
    )

    problem = build_problem(
        network,
        database,
        TimeBlock(1, list(range(week * number_hours, (week + 1) * number_hours))),
        [scenario],
        border_management=BlockBorderManagement.CYCLE,
    )

    return problem


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
            max_generating_shape = data["max_generating"].shape
            if len(max_generating_shape) == 1:
                max_generating = pd.DataFrame(
                    data["max_generating"].reshape((max_generating_shape[0], 1))
                )
            else:
                max_generating = pd.DataFrame(data["max_generating"])
            max_units = get_max_unit(
                data["p_max"], data["nb_units_max"], max_generating
            )
            max_failures = get_max_failures(max_units, hours_in_week)
            nb_units_max_min_down_time = get_max_unit_for_min_down_time(
                int(max(data["d_min_up"], data["d_min_down"])), max_units, hours_in_week
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


def create_problem_accurate_heuristic(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    data_dir: Path,
    week: int,
    scenario: int,
    initial_thermal_model: Model = THERMAL_CLUSTER_MODEL_MILP,
) -> OptimizationProblem:
    thermal_model_builder = HeuristicAccurateModelBuilder(initial_thermal_model)

    lib = library(
        port_types=[],
        models=[
            thermal_model_builder.model,
        ],
    )

    network = get_network(data_dir / "components_heuristic.yml", lib)

    database = get_database(
        data_dir,
        "components_heuristic.yml",
        get_cluster_id(network, initial_thermal_model.id),
        number_hours,
    )

    modify_lower_bound_of_cluster(
        lower_bound, database, get_cluster_id(network, initial_thermal_model.id)
    )

    problem = build_problem(
        network,
        database,
        TimeBlock(1, list(range(week * number_hours, (week + 1) * number_hours))),
        [scenario],
        border_management=BlockBorderManagement.CYCLE,
    )

    return problem


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


def create_problem_fast_heuristic(
    lower_bound: List[float],
    number_hours: int,
    thermal_cluster: str,
    data_dir: Path,
    week: int,
    scenario: int,
) -> pd.DataFrame:
    data = get_data(
        data_dir=data_dir,
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
            number_hours,
        ).reshape((number_hours, 1))
    else:
        pdispo = data["max_generating"][
            number_hours * week : number_hours * (week + 1), scenario
        ].reshape((number_hours, 1))

    number_blocks = number_hours // delta

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
        TimeSeriesData({TimeIndex(i): nb_on_1[i] for i in range(number_hours)}),
    )
    for h in range(delta):
        start_ajust = number_hours - delta + h
        database.add_data(
            "B",
            f"alpha_ajust_{h}",
            TimeSeriesData(
                {
                    TimeIndex(t): 1 if (t >= start_ajust) or (t < h) else 0
                    for t in range(number_hours)
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
                        for t in range(number_hours)
                    }
                ),
            )

    time_block = TimeBlock(1, [i for i in range(number_hours)])

    block = create_component(
        model=HeuristicFastModelBuilder(number_blocks, delta=delta).model, id="B"
    )

    network = Network("test")
    network.add_component(block)

    problem = build_problem(
        network,
        database,
        time_block,
        1,
        border_management=BlockBorderManagement.CYCLE,
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
    ).reshape((number_hours, 1))

    mingen_heuristic = pd.DataFrame(
        np.minimum(n_heuristic * pmin, pdispo),
        index=[list(range(week * number_hours, (week + 1) * number_hours))],
        columns=[scenario],
    )

    return mingen_heuristic
