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
from typing import Dict, List, Optional

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
from andromede.model import Model
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
    Node,
    PortRef,
    TimeIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
    create_component,
)
from andromede.study.data import AbstractDataStructure
from andromede.study.parsing import parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    resolve_components_and_cnx,
)
from andromede.thermal_heuristic.data import (
    get_failures_for_cluster,
    get_max_failures,
    get_max_unit,
    get_max_unit_for_min_down_time,
)
from andromede.thermal_heuristic.model import (
    get_accurate_heuristic_model,
    get_model_fast_heuristic,
    get_thermal_cluster_accurate_model,
    get_thermal_cluster_fast_model,
)
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP


def create_main_problem(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    lp_relaxation: bool,
    fast: bool,
    data_dir: Path,
    week: int,
    scenario: int,
) -> OptimizationProblem:

    thermal_model = choose_thermal_model(lp_relaxation, fast)

    lib = library(
        port_types=[BALANCE_PORT_TYPE],
        models=[
            NODE_BALANCE_MODEL,
            DEMAND_MODEL,
            SPILLAGE_MODEL,
            UNSUPPLIED_ENERGY_MODEL,
            thermal_model,
        ],
    )

    network, database = get_network_and_database(
        data_dir,
        lib,
        "components.yml",
        scenarios=[scenario],
        timesteps=list(range(week * number_hours, (week + 1) * number_hours)),
    )

    modify_parameters_of_cluster(
        lower_bound,
        database,
        network,
        THERMAL_CLUSTER_MODEL_MILP.id,
        dir_path=data_dir,
        number_hours=number_hours,
        week=week,
        scenario=scenario,
    )

    time_block = TimeBlock(1, [i for i in range(number_hours)])
    scenarios = 1

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=BlockBorderManagement.CYCLE,
        solver_id="XPRESS",
    )

    return problem


def modify_parameters_of_cluster(
    lower_bound: Dict[str, AbstractDataStructure],
    database: DataBase,
    network: Network,
    cluster_model_id: str,
    dir_path: Path,
    number_hours: int,
    week: int,
    scenario: int,
) -> None:
    for cluster_id in get_cluster_id(network, cluster_model_id):

        data = get_data(
            dir_path,
            "components.yml",
            cluster_id,
            number_hours=number_hours,
            week=week,
            scenario=scenario,
        )

        max_generating = pd.DataFrame(
            np.repeat(
                data["max_generating"],
                1 if type(data["max_generating"]) is list else number_hours,
            ).reshape((number_hours, 1))
        )
        max_units = get_max_unit(data["p_max"], data["nb_units_max"], max_generating)
        max_failures = get_max_failures(max_units)
        nb_units_max_min_down_time = get_max_unit_for_min_down_time(
            int(max(data["d_min_up"], data["d_min_down"])), max_units
        )

        database.add_data(cluster_id, "nb_units_min", lower_bound[cluster_id])
        database.add_data(
            cluster_id,
            "nb_units_max",
            TimeScenarioSeriesData(max_units),
        )
        database.add_data(
            cluster_id,
            "max_generating",
            TimeScenarioSeriesData(max_generating),
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
        database.add_data(cluster_id, "min_generating", lower_bound[cluster_id])


def get_cluster_id(network: Network, cluster_model_id: str) -> list[str]:
    return [c.id for c in network.components if c.model.id == cluster_model_id]


def get_network_and_database(
    data_dir: Path,
    lib: Library,
    yml_file: str,
    scenarios: Optional[List[int]],
    timesteps: Optional[List[int]],
) -> tuple[Network, DataBase]:
    compo_file = data_dir / yml_file

    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    components_input = resolve_components_and_cnx(components_file, lib)
    network = build_network(components_input)

    database = build_data_base(
        components_file, data_dir, scenarios=scenarios, timesteps=timesteps
    )
    return network, database


def choose_thermal_model(lp_relaxation: bool, fast: bool) -> Model:
    if fast:
        thermal_model = get_thermal_cluster_fast_model(THERMAL_CLUSTER_MODEL_MILP)
    elif lp_relaxation:
        thermal_model = get_thermal_cluster_accurate_model(THERMAL_CLUSTER_MODEL_MILP)
    else:
        thermal_model = THERMAL_CLUSTER_MODEL_MILP
    return thermal_model


def create_problem_accurate_heuristic(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    data_dir: Path,
    thermal_cluster: str,
    week: int,
    scenario: int,
) -> OptimizationProblem:

    thermal_model = get_accurate_heuristic_model(THERMAL_CLUSTER_MODEL_MILP)

    lib = library(
        port_types=[],
        models=[
            thermal_model,
        ],
    )

    network, database = get_network_and_database(
        data_dir,
        lib,
        "components_heuristic.yml",
        scenarios=[scenario],
        timesteps=list(range(week * number_hours, (week + 1) * number_hours)),
    )

    modify_parameters_of_cluster(
        lower_bound,
        database,
        network,
        THERMAL_CLUSTER_MODEL_MILP.id,
        dir_path=data_dir,
        number_hours=number_hours,
        week=week,
        scenario=scenario,
    )

    time_block = TimeBlock(1, [i for i in range(number_hours)])
    scenarios = 1

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=BlockBorderManagement.CYCLE,
        solver_id="XPRESS",
    )

    return problem


def get_data(
    data_dir: Path,
    yml_file: str,
    id_cluster: str,
    week: int,
    number_hours: int,
    scenario: int,
) -> Dict:
    compo_file = data_dir / yml_file

    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    cluster = [c for c in components_file.components if c.id == id_cluster][0]
    parameters = {
        p.name: (
            p.value
            if p.value is not None
            else list(
                np.loadtxt(data_dir / (p.timeseries + ".txt"))[  # type:ignore
                    week * number_hours : (week + 1) * number_hours, scenario
                ]
            )
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
        week=week,
        number_hours=number_hours,
        scenario=scenario,
    )
    delta = int(max(data["d_min_up"], data["d_min_down"]))
    pmax = data["p_max"]
    pmin = data["p_min"]
    nmax = data["nb_units_max"]
    pdispo = np.repeat(
        data["max_generating"],
        1 if type(data["max_generating"]) is list else number_hours,
    ).reshape((number_hours, 1))

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
        model=get_model_fast_heuristic(number_blocks, delta=delta), id="B"
    )

    network = Network("test")
    network.add_component(block)

    problem = build_problem(
        network,
        database,
        time_block,
        1,
        border_management=BlockBorderManagement.CYCLE,
        solver_id="XPRESS",
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
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return mingen_heuristic
