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

import pandas as pd
import pytest
import numpy as np
from typing import List, Dict
from math import ceil, floor
import ortools.linear_solver.pywraplp as pywraplp

from andromede.expression import literal, param, var
from andromede.expression.expression import ExpressionRange, port_field
from andromede.expression.indexing_structure import IndexingStructure
from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    DEMAND_MODEL,
    NODE_BALANCE_MODEL,
    SPILLAGE_MODEL,
    UNSUPPLIED_ENERGY_MODEL,
)
from andromede.model import Model, ModelPort, float_parameter, float_variable, model
from andromede.model.model import PortFieldDefinition, PortFieldId
from andromede.model.parameter import float_parameter, int_parameter
from andromede.model.variable import float_variable, int_variable
from andromede.model.constraint import Constraint
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
    TimeScenarioIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
    TimeIndex,
    create_component,
)
from andromede.study.data import AbstractDataStructure

CONSTANT = IndexingStructure(False, False)
TIME_AND_SCENARIO_FREE = IndexingStructure(True, True)
ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, True)
NON_ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, False)
CONSTANT_PER_SCENARIO = IndexingStructure(False, True)

THERMAL_CLUSTER_MODEL_MILP = model(
    id="GEN",
    parameters=[
        float_parameter("p_max", CONSTANT),  # p_max of a single unit
        float_parameter("p_min", CONSTANT),
        float_parameter("d_min_up", CONSTANT),
        float_parameter("d_min_down", CONSTANT),
        float_parameter("cost", CONSTANT),
        float_parameter("startup_cost", CONSTANT),
        float_parameter("fixed_cost", CONSTANT),
        int_parameter("nb_units_min", TIME_AND_SCENARIO_FREE),
        int_parameter("nb_units_max", TIME_AND_SCENARIO_FREE),
        float_parameter("max_generating", TIME_AND_SCENARIO_FREE),
        int_parameter("max_failure", TIME_AND_SCENARIO_FREE),
        int_parameter("nb_units_max_min_down_time", TIME_AND_SCENARIO_FREE),
    ],
    variables=[
        float_variable(
            "generation",
            lower_bound=literal(0),
            upper_bound=param("max_generating"),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        int_variable(
            "nb_on",
            lower_bound=param("nb_units_min"),
            upper_bound=param("nb_units_max"),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        int_variable(
            "nb_stop",
            lower_bound=literal(0),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        int_variable(
            "nb_failure",
            lower_bound=literal(0),
            upper_bound=param("max_failure"),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        int_variable(
            "nb_start",
            lower_bound=literal(0),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
    ],
    ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("balance_port", "flow"),
            definition=var("generation"),
        )
    ],
    constraints=[
        Constraint(
            "Max generation",
            var("generation") <= param("p_max") * var("nb_on"),
        ),
        Constraint(
            "Min generation",
            var("generation") >= param("p_min") * var("nb_on"),
        ),
        Constraint(
            "NODU balance",
            var("nb_on") == var("nb_on").shift(-1) + var("nb_start") - var("nb_stop"),
        ),
        Constraint(
            "Max failures",
            var("nb_failure") <= var("nb_stop"),
        ),
        Constraint(
            "Min up time",
            var("nb_start")
            .shift(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            - var("nb_failure")
            .shift(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            <= var("nb_on"),
        ),
        Constraint(
            "Min down time",
            var("nb_stop")
            .shift(ExpressionRange(-param("d_min_down") + 1, literal(0)))
            .sum()
            <= param("nb_units_max_min_down_time") - var("nb_on"),
        ),
        # It also works by writing ExpressionRange(-param("d_min_down") + 1, 0) as ExpressionRange's __post_init__ wraps integers to literal nodes. However, MyPy does not seem to infer that ExpressionRange's attributes are necessarily of ExpressionNode type and raises an error if the arguments in the constructor are integer (whereas it runs correctly), this why we specify it here with literal(0) instead of 0.
    ],
    objective_operational_contribution=(
        param("cost") * var("generation")
        + param("startup_cost") * var("nb_start")
        + param("fixed_cost") * var("nb_on")
    )
    .sum()
    .expec(),
)

THERMAL_CLUSTER_MODEL_LP = model(
    id="GEN",
    parameters=[
        float_parameter("p_max", CONSTANT),  # p_max of a single unit
        float_parameter("p_min", CONSTANT),
        float_parameter("d_min_up", CONSTANT),
        float_parameter("d_min_down", CONSTANT),
        float_parameter("cost", CONSTANT),
        float_parameter("startup_cost", CONSTANT),
        float_parameter("fixed_cost", CONSTANT),
        int_parameter("nb_units_min", TIME_AND_SCENARIO_FREE),
        int_parameter("nb_units_max", TIME_AND_SCENARIO_FREE),
        float_parameter("max_generating", TIME_AND_SCENARIO_FREE),
        int_parameter("max_failure", TIME_AND_SCENARIO_FREE),
        int_parameter("nb_units_max_min_down_time", TIME_AND_SCENARIO_FREE),
    ],
    variables=[
        float_variable(
            "generation",
            lower_bound=literal(0),
            upper_bound=param("max_generating"),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        float_variable(
            "nb_on",
            lower_bound=param("nb_units_min"),
            upper_bound=param("nb_units_max"),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        float_variable(
            "nb_stop",
            lower_bound=literal(0),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        float_variable(
            "nb_failure",
            lower_bound=literal(0),
            upper_bound=param("max_failure"),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        float_variable(
            "nb_start",
            lower_bound=literal(0),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
    ],
    ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("balance_port", "flow"),
            definition=var("generation"),
        )
    ],
    constraints=[
        Constraint(
            "Max generation",
            var("generation") <= param("p_max") * var("nb_on"),
        ),
        Constraint(
            "Min generation",
            var("generation") >= param("p_min") * var("nb_on"),
        ),
        Constraint(
            "NODU balance",
            var("nb_on") == var("nb_on").shift(-1) + var("nb_start") - var("nb_stop"),
        ),
        Constraint(
            "Max failures",
            var("nb_failure") <= var("nb_stop"),
        ),
        Constraint(
            "Min up time",
            var("nb_start")
            .shift(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            - var("nb_failure")
            .shift(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            <= var("nb_on"),
        ),
        Constraint(
            "Min down time",
            var("nb_stop")
            .shift(ExpressionRange(-param("d_min_down") + 1, literal(0)))
            .sum()
            <= param("nb_units_max_min_down_time") - var("nb_on"),
        ),
        # It also works by writing ExpressionRange(-param("d_min_down") + 1, 0) as ExpressionRange's __post_init__ wraps integers to literal nodes. However, MyPy does not seem to infer that ExpressionRange's attributes are necessarily of ExpressionNode type and raises an error if the arguments in the constructor are integer (whereas it runs correctly), this why we specify it here with literal(0) instead of 0.
    ],
    objective_operational_contribution=(
        param("cost") * var("generation")
        + param("startup_cost") * var("nb_start")
        + param("fixed_cost") * var("nb_on")
    )
    .sum()
    .expec(),
)

THERMAL_CLUSTER_MODEL_FAST = model(
    id="GEN",
    parameters=[
        float_parameter("p_max", CONSTANT),  # p_max of a single unit
        float_parameter("cost", CONSTANT),
        int_parameter("nb_units_max", CONSTANT),
        float_parameter("mingen", TIME_AND_SCENARIO_FREE),
        float_parameter("failures", TIME_AND_SCENARIO_FREE),
    ],
    variables=[
        float_variable(
            "generation",
            lower_bound=param("mingen"),
            upper_bound=param("failures"),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
    ],
    ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("balance_port", "flow"),
            definition=var("generation"),
        )
    ],
    constraints=[
        Constraint(
            "Max generation",
            var("generation") <= param("p_max") * param("nb_units_max"),
        ),
    ],
    objective_operational_contribution=(param("cost") * var("generation"))
    .sum()
    .expec(),
)


THERMAL_CLUSTER_MODEL_ACCURATE_HEURISTIC = model(
    id="GEN",
    parameters=[
        float_parameter("d_min_up", CONSTANT),
        float_parameter("d_min_down", CONSTANT),
        int_parameter("nb_units_min", TIME_AND_SCENARIO_FREE),
        int_parameter("nb_units_max", TIME_AND_SCENARIO_FREE),
        float_parameter("max_generating", TIME_AND_SCENARIO_FREE),
        int_parameter("max_failure", TIME_AND_SCENARIO_FREE),
        int_parameter("nb_units_max_min_down_time", TIME_AND_SCENARIO_FREE),
    ],
    variables=[
        float_variable(
            "nb_on",
            lower_bound=param("nb_units_min"),
            upper_bound=param("nb_units_max"),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        float_variable(
            "nb_stop",
            lower_bound=literal(0),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        float_variable(
            "nb_failure",
            lower_bound=literal(0),
            upper_bound=param("max_failure"),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
        float_variable(
            "nb_start",
            lower_bound=literal(0),
            structure=ANTICIPATIVE_TIME_VARYING,
        ),
    ],
    constraints=[
        Constraint(
            "NODU balance",
            var("nb_on") == var("nb_on").shift(-1) + var("nb_start") - var("nb_stop"),
        ),
        Constraint(
            "Max failures",
            var("nb_failure") <= var("nb_stop"),
        ),
        Constraint(
            "Min up time",
            var("nb_start")
            .shift(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            - var("nb_failure")
            .shift(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            <= var("nb_on"),
        ),
        Constraint(
            "Min down time",
            var("nb_stop")
            .shift(ExpressionRange(-param("d_min_down") + 1, literal(0)))
            .sum()
            <= param("nb_units_max_min_down_time") - var("nb_on"),
        ),
        # It also works by writing ExpressionRange(-param("d_min_down") + 1, 0) as ExpressionRange's __post_init__ wraps integers to literal nodes. However, MyPy does not seem to infer that ExpressionRange's attributes are necessarily of ExpressionNode type and raises an error if the arguments in the constructor are integer (whereas it runs correctly), this why we specify it here with literal(0) instead of 0.
    ],
    objective_operational_contribution=(var("nb_on")).sum().expec(),
)

BLOCK_MODEL_FAST_HEURISTIC = model(
    id="GEN",
    parameters=[float_parameter("cost", TIME_AND_SCENARIO_FREE)],
    variables=[
        int_variable(
            "t_ajust",
            lower_bound=literal(0),
            upper_bound=literal(1),
            structure=TIME_AND_SCENARIO_FREE,
        )
    ],
    constraints=[
        Constraint(
            "Choose one t ajust",
            var("t_ajust").sum() == literal(1),
        )
    ],
    objective_operational_contribution=(var("t_ajust") * param("cost")).sum().expec(),
)


def check_output_values(
    problem: OptimizationProblem, mode: str, week: int, scenario: int
) -> None:
    output = OutputValues(problem)

    expected_output_clusters_file = open(
        "tests/functional/data_second_complex_case/"
        + mode
        + "/"
        + str(scenario)
        + "/details-hourly.txt",
        "r",
    )
    expected_output_clusters = expected_output_clusters_file.readlines()

    expected_output_general_file = open(
        "tests/functional/data_second_complex_case/"
        + mode
        + "/"
        + str(scenario)
        + "/values-hourly.txt",
        "r",
    )
    expected_output_general = expected_output_general_file.readlines()

    for i, cluster in enumerate(["G" + str(i) for i in [2]]):

        assert output.component(cluster).var("generation").value == [
            [
                pytest.approx(float(line.strip().split("\t")[4 + i]), abs=1e-10)
                for line in expected_output_clusters[
                    168 * week + 7 : 168 * week + 7 + 168
                ]
            ]
        ]
        if mode != "fast":
            assert output.component(cluster).var("nb_on").value == [
                [
                    pytest.approx(float(line.strip().split("\t")[6 + i]))
                    for line in expected_output_clusters[
                        168 * week + 7 : 168 * week + 7 + 168
                    ]
                ]
            ]

    assert output.component("S").var("spillage").value == [
        [
            pytest.approx(float(line.strip().split("\t")[11 if mode == "milp" else 12]))
            for line in expected_output_general[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]

    assert output.component("U").var("unsupplied_energy").value == [
        [
            pytest.approx(float(line.strip().split("\t")[10 if mode == "milp" else 11]))
            for line in expected_output_general[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168
    scenario = 0
    week = 0

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for j, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):
        nb_on_1 = pd.DataFrame(
            np.transpose(
                np.ceil(
                    np.round(
                        np.loadtxt(
                            f"tests/functional/data_second_complex_case/accurate/itr1_accurate_cluster{j+1}.txt"
                        ),
                        12,
                    )
                )
            ),
            index=[i for i in range(number_hours)],
            columns=[0],
        )
        n_guide = TimeScenarioSeriesData(nb_on_1)

        # Solve heuristic problem
        problem_accurate_heuristic = create_problem_accurate_heuristic(
            {
                "G" + str(i): ConstantData(0) if "G" + str(i) != cluster else n_guide
                for i in range(1, 7)
            },
            number_hours,
            thermal_cluster=cluster,
            week=week,
            scenario=scenario,
        )
        status = problem_accurate_heuristic.solver.Solve(parameters)

        assert status == problem_accurate_heuristic.solver.OPTIMAL

        output_heuristic = OutputValues(problem_accurate_heuristic)
        nb_on_heuristic = np.transpose(
            np.ceil(np.array(output_heuristic.component(cluster).var("nb_on").value))
        )

        expected_output = np.loadtxt(
            f"tests/functional/data_second_complex_case/accurate/itr2_accurate_cluster{j+1}.txt"
        )
        for time_step in range(number_hours):
            assert nb_on_heuristic[time_step, 0] == expected_output[time_step]


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    """
    number_hours = 168
    scenario = 0
    week = 0

    for j, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):
        nb_on_1 = np.loadtxt(
            f"tests/functional/data_second_complex_case/fast/itr1_fast_cluster{j+1}.txt"
        )

        # Solve heuristic problem
        mingen_heuristic = create_problem_fast_heuristic(
            nb_on_1,  # type:ignore
            number_hours,
            thermal_cluster=cluster,
            week=week,
            scenario=scenario,
        )

        expected_output = np.loadtxt(
            f"tests/functional/data_second_complex_case/fast/itr2_fast_cluster{j+1}.txt"
        )
        for time_step in range(number_hours):
            assert mingen_heuristic.values[time_step, 0] == expected_output[time_step]


def generate_database(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    week: int,
    scenario: int,
) -> DataBase:

    delta, pmax, pmin, cost, units = get_data()

    database = DataBase()

    for i, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):

        max_generating = get_failures_for_cluster(week, scenario, cluster, number_hours)
        max_units = max_generating / pmax[cluster]
        max_units.where(max_units < units[cluster], units[cluster], inplace=True)
        max_failures = (
            pd.DataFrame(np.roll(max_units.values, 1), index=max_units.index)
            - max_units
        )
        max_failures.where(max_failures > 0, 0, inplace=True)
        nb_units_max_min_down_time = pd.DataFrame(
            np.roll(max_units.values, delta[cluster]), index=max_units.index
        )
        end_failures = max_units - pd.DataFrame(
            np.roll(max_units.values, 1), index=max_units.index
        )
        end_failures.where(end_failures > 0, 0, inplace=True)
        for j in range(delta[cluster]):
            nb_units_max_min_down_time += pd.DataFrame(
                np.roll(end_failures.values, j), index=end_failures.index
            )

        database.add_data(cluster, "p_max", ConstantData(pmax[cluster]))
        database.add_data(cluster, "p_min", ConstantData(pmin[cluster]))
        database.add_data(cluster, "cost", ConstantData(cost[cluster]))
        database.add_data(cluster, "startup_cost", ConstantData(10 * (i + 1)))
        database.add_data(cluster, "fixed_cost", ConstantData(i + 1))
        database.add_data(cluster, "d_min_up", ConstantData(delta[cluster]))
        database.add_data(cluster, "d_min_down", ConstantData(delta[cluster]))
        database.add_data(cluster, "nb_units_min", lower_bound[cluster])
        database.add_data(
            cluster,
            "nb_units_max",
            TimeScenarioSeriesData(max_units),
        )
        database.add_data(
            cluster,
            "max_generating",
            TimeScenarioSeriesData(max_generating),
        )
        database.add_data(
            cluster,
            "max_failure",
            TimeScenarioSeriesData(max_failures),
        )
        database.add_data(
            cluster,
            "nb_units_max_min_down_time",
            TimeScenarioSeriesData(nb_units_max_min_down_time),
        )
        database.add_data(cluster, "mingen", lower_bound[cluster])

    database.add_data("U", "cost", ConstantData(750))
    database.add_data("S", "cost", ConstantData(10))

    output_file = open(
        "tests/functional/data_second_complex_case/milp/"
        + str(scenario)
        + "/values-hourly.txt",
        "r",
    )
    output = output_file.readlines()

    demand_data = pd.DataFrame(
        data=[
            float(line.strip().split("\t")[7])
            for line in output[168 * week + 7 : 168 * week + 7 + 168]
        ],
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    demand_time_scenario_series = TimeScenarioSeriesData(demand_data)
    database.add_data("D", "demand", demand_time_scenario_series)
    return database


def get_data() -> (
    tuple[
        Dict[str, int], Dict[str, int], Dict[str, int], Dict[str, int], Dict[str, int]
    ]
):
    delta = {"G1": 3, "G2": 3, "G3": 2, "G4": 1, "G5": 1, "G6": 3}
    pmax = {"G1": 64, "G2": 221, "G3": 486, "G4": 218, "G5": 29, "G6": 159}
    pmin = {"G1": 32, "G2": 111, "G3": 194, "G4": 87, "G5": 14, "G6": 80}
    cost = {
        "G1": 165,
        "G2": 117,
        "G3": 106,
        "G4": 135,
        "G5": 191,
        "G6": 166,
    }
    units = {"G1": 21, "G2": 13, "G3": 13, "G4": 2, "G5": 7, "G6": 16}
    return delta, pmax, pmin, cost, units


def get_failures_for_cluster(
    week: int, scenario: int, cluster: str, number_hours: int
) -> pd.DataFrame:
    input_file = np.loadtxt(
        f"tests/functional/data_second_complex_case/series_{cluster}.txt",
        delimiter="\t",
    )

    failures_data = pd.DataFrame(
        data=input_file[
            number_hours * week : number_hours * week + number_hours, scenario
        ],
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return failures_data


def create_problem_accurate_heuristic(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    thermal_cluster: str,
    week: int,
    scenario: int,
) -> OptimizationProblem:

    database = generate_database(
        lower_bound, number_hours, week=week, scenario=scenario
    )

    time_block = TimeBlock(1, [i for i in range(number_hours)])
    scenarios = 1

    gen = create_component(
        model=THERMAL_CLUSTER_MODEL_ACCURATE_HEURISTIC, id=thermal_cluster
    )

    network = Network("test")
    network.add_component(gen)

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=BlockBorderManagement.CYCLE,
        solver_id="XPRESS",
    )

    return problem


def create_problem_fast_heuristic(
    lower_bound: List[float],
    number_hours: int,
    thermal_cluster: str,
    week: int,
    scenario: int,
) -> pd.DataFrame:

    data_delta, data_pmax, data_pmin, _, _ = get_data()
    delta = data_delta[thermal_cluster]
    pmax = data_pmax[thermal_cluster]
    pmin = data_pmin[thermal_cluster]
    pdispo = get_failures_for_cluster(week, scenario, thermal_cluster, number_hours)

    cost = pd.DataFrame(
        np.zeros((delta + 1, 1)),
        index=[i for i in range(delta + 1)],
        columns=[0],
    )
    n = np.zeros((number_hours, delta + 1, 1))
    for h in range(delta + 1):
        cost_h = 0
        n_k = max(
            [convert_to_integer(lower_bound[j] / pmax) for j in range(h)]
            + [
                convert_to_integer(lower_bound[j] / pmax)
                for j in range(number_hours - delta + h, number_hours)
            ]
        )
        cost_h += delta * n_k
        n[0:h, h, 0] = n_k
        n[number_hours - delta + h : number_hours, h, 0] = n_k
        t = h
        while t < number_hours - delta + h:
            k = floor((t - h) / delta) * delta + h
            n_k = max(
                [
                    convert_to_integer(lower_bound[j] / pmax)
                    for j in range(k, min(number_hours - delta + h, k + delta))
                ]
            )
            cost_h += (min(number_hours - delta + h, k + delta) - k) * n_k
            n[k : min(number_hours - delta + h, k + delta), h, 0] = n_k
            t += delta
        cost.iloc[h, 0] = cost_h

    hmin = np.argmin(cost.values[:, 0])
    mingen_heuristic = pd.DataFrame(
        np.minimum(n[:, hmin, :] * pmin, pdispo.values),
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return mingen_heuristic


def convert_to_integer(x: float) -> int:
    return ceil(round(x, 12))