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
        int_parameter("nb_units_max", CONSTANT),
        float_parameter("failures", TIME_AND_SCENARIO_FREE),
    ],
    variables=[
        float_variable(
            "generation",
            lower_bound=literal(0),
            upper_bound=param("failures"),
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
            "Min up time",
            var("nb_start")
            .shift(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            <= var("nb_on"),
        ),
        Constraint(
            "Min down time",
            var("nb_stop")
            .shift(ExpressionRange(-param("d_min_down") + 1, literal(0)))
            .sum()
            <= param("nb_units_max").shift(-param("d_min_down")) - var("nb_on"),
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
        int_parameter("nb_units_max", CONSTANT),
        float_parameter("failures", TIME_AND_SCENARIO_FREE),
    ],
    variables=[
        float_variable(
            "generation",
            lower_bound=literal(0),
            upper_bound=param("failures"),
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
            "Min up time",
            var("nb_start")
            .shift(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            <= var("nb_on"),
        ),
        Constraint(
            "Min down time",
            var("nb_stop")
            .shift(ExpressionRange(-param("d_min_down") + 1, literal(0)))
            .sum()
            <= param("nb_units_max").shift(-param("d_min_down")) - var("nb_on"),
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
        int_parameter("nb_units_max", CONSTANT),
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
            "Min up time",
            var("nb_start")
            .shift(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            <= var("nb_on"),
        ),
        Constraint(
            "Min down time",
            var("nb_stop")
            .shift(ExpressionRange(-param("d_min_down") + 1, literal(0)))
            .sum()
            <= param("nb_units_max").shift(-param("d_min_down")) - var("nb_on"),
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


def test_milp_version() -> None:
    """ """
    number_hours = 168

    for week in range(2):
        problem = create_complex_problem(
            {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
            number_hours,
            lp_relaxation=False,
            fast=False,
            week=week,
        )

        parameters = pywraplp.MPSolverParameters()
        parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
        parameters.SetIntegerParam(parameters.SCALING, 0)

        status = problem.solver.Solve(parameters)

        assert status == problem.solver.OPTIMAL

        check_output_values(problem, "milp", week)

        if week == 0:
            assert problem.solver.Objective().Value() == pytest.approx(78933841)
        elif week == 1:
            assert problem.solver.Objective().Value() == pytest.approx(102109698)


def check_output_values(problem: OptimizationProblem, mode: str, week: int) -> None:
    output = OutputValues(problem)

    expected_output_clusters_file = open(
        "tests/functional/data_complex_case/" + mode + "/details-hourly.txt", "r"
    )
    expected_output_clusters = expected_output_clusters_file.readlines()

    expected_output_general_file = open(
        "tests/functional/data_complex_case/" + mode + "/values-hourly.txt", "r"
    )
    expected_output_general = expected_output_general_file.readlines()

    assert output.component("G1").var("generation").value == [
        [
            pytest.approx(float(line.strip().split("\t")[4]))
            for line in expected_output_clusters[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]
    if mode != "fast":
        assert output.component("G1").var("nb_on").value == [
            [
                pytest.approx(float(line.strip().split("\t")[12]))
                for line in expected_output_clusters[
                    168 * week + 7 : 168 * week + 7 + 168
                ]
            ]
        ]

    assert output.component("G2").var("generation").value == [
        [
            pytest.approx(float(line.strip().split("\t")[5]))
            for line in expected_output_clusters[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]
    if mode != "fast":
        assert output.component("G2").var("nb_on").value == [
            [
                pytest.approx(float(line.strip().split("\t")[13]))
                for line in expected_output_clusters[
                    168 * week + 7 : 168 * week + 7 + 168
                ]
            ]
        ]

    assert output.component("G3").var("generation").value == [
        [
            pytest.approx(float(line.strip().split("\t")[6]))
            for line in expected_output_clusters[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]
    if mode != "fast":
        assert output.component("G3").var("nb_on").value == [
            [
                pytest.approx(float(line.strip().split("\t")[14]))
                for line in expected_output_clusters[
                    168 * week + 7 : 168 * week + 7 + 168
                ]
            ]
        ]

    assert output.component("S").var("spillage").value == [
        [
            pytest.approx(float(line.strip().split("\t")[20 if mode == "milp" else 21]))
            for line in expected_output_general[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]

    assert output.component("U").var("unsupplied_energy").value == [
        [
            pytest.approx(float(line.strip().split("\t")[19 if mode == "milp" else 20]))
            for line in expected_output_general[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for week in range(2):
        # First optimization
        problem_optimization_1 = create_complex_problem(
            {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
            number_hours,
            lp_relaxation=True,
            fast=False,
            week=week,
        )
        status = problem_optimization_1.solver.Solve(parameters)

        assert status == problem_optimization_1.solver.OPTIMAL

        # Get number of on units and round it to integer
        output_1 = OutputValues(problem_optimization_1)
        nb_on_min: Dict[str, AbstractDataStructure] = {}
        for g in ["G1", "G2", "G3"]:
            nb_on_1 = pd.DataFrame(
                np.transpose(
                    np.ceil(
                        np.round(np.array(output_1.component(g).var("nb_on").value), 12)
                    )
                ),
                index=[i for i in range(number_hours)],
                columns=[0],
            )
            n_guide = TimeScenarioSeriesData(nb_on_1)

            # Solve heuristic problem
            problem_accurate_heuristic = create_problem_accurate_heuristic(
                {g: n_guide}, number_hours, thermal_cluster=g, week=week
            )
            status = problem_accurate_heuristic.solver.Solve(parameters)

            assert status == problem_accurate_heuristic.solver.OPTIMAL

            output_heuristic = OutputValues(problem_accurate_heuristic)
            nb_on_heuristic = pd.DataFrame(
                np.transpose(
                    np.ceil(np.array(output_heuristic.component(g).var("nb_on").value))
                ),
                index=[i for i in range(number_hours)],
                columns=[0],
            )
            nb_on_min[g] = TimeScenarioSeriesData(nb_on_heuristic)

        # Second optimization with lower bound modified
        problem_optimization_2 = create_complex_problem(
            nb_on_min, number_hours, lp_relaxation=True, fast=False, week=week
        )
        status = problem_optimization_2.solver.Solve(parameters)

        assert status == problem_optimization_2.solver.OPTIMAL
        if week == 0:
            assert problem_optimization_2.solver.Objective().Value() == 78996726
        elif week == 1:
            assert (
                problem_optimization_2.solver.Objective().Value() == 102215087 - 69500
            )

        check_output_values(problem_optimization_2, "accurate", week)


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    """

    number_hours = 168

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for week in range(2):
        # First optimization
        problem_optimization_1 = create_complex_problem(
            {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
            number_hours,
            lp_relaxation=True,
            fast=True,
            week=week,
        )
        status = problem_optimization_1.solver.Solve(parameters)

        assert status == problem_optimization_1.solver.OPTIMAL

        # Get number of on units
        output_1 = OutputValues(problem_optimization_1)

        # Solve heuristic problem
        mingen: Dict[str, AbstractDataStructure] = {}
        for g in ["G1", "G2", "G3"]:
            mingen_heuristic = create_problem_fast_heuristic(
                output_1.component(g).var("generation").value,  # type:ignore
                number_hours,
                thermal_cluster=g,
                week=week,
            )

            mingen[g] = TimeScenarioSeriesData(mingen_heuristic)

        # Second optimization with lower bound modified
        problem_optimization_2 = create_complex_problem(
            mingen, number_hours, lp_relaxation=True, fast=True, week=week
        )
        status = problem_optimization_2.solver.Solve(parameters)

        assert status == problem_optimization_2.solver.OPTIMAL

        check_output_values(problem_optimization_2, "fast", week)

        if week == 0:
            assert problem_optimization_2.solver.Objective().Value() == pytest.approx(
                79277215 - 630089
            )
        elif week == 1:
            assert (
                problem_optimization_2.solver.Objective().Value() == 102461792 - 699765
            )


def create_complex_problem(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    lp_relaxation: bool,
    fast: bool,
    week: int,
) -> OptimizationProblem:

    database = generate_database(lower_bound, number_hours, week=week)

    time_block = TimeBlock(1, [i for i in range(number_hours)])
    scenarios = 1

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    demand = create_component(model=DEMAND_MODEL, id="D")

    if fast:
        gen1 = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="G1")
        gen2 = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="G2")
        gen3 = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="G3")
    elif lp_relaxation:
        gen1 = create_component(model=THERMAL_CLUSTER_MODEL_LP, id="G1")
        gen2 = create_component(model=THERMAL_CLUSTER_MODEL_LP, id="G2")
        gen3 = create_component(model=THERMAL_CLUSTER_MODEL_LP, id="G3")
    else:
        gen1 = create_component(model=THERMAL_CLUSTER_MODEL_MILP, id="G1")
        gen2 = create_component(model=THERMAL_CLUSTER_MODEL_MILP, id="G2")
        gen3 = create_component(model=THERMAL_CLUSTER_MODEL_MILP, id="G3")

    spillage = create_component(model=SPILLAGE_MODEL, id="S")

    unsupplied_energy = create_component(model=UNSUPPLIED_ENERGY_MODEL, id="U")

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen1)
    network.add_component(gen2)
    network.add_component(gen3)
    network.add_component(spillage)
    network.add_component(unsupplied_energy)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen1, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen2, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen3, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(spillage, "balance_port"), PortRef(node, "balance_port"))
    network.connect(
        PortRef(unsupplied_energy, "balance_port"), PortRef(node, "balance_port")
    )

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=BlockBorderManagement.CYCLE,
        solver_id="XPRESS",
    )

    return problem


def generate_database(
    lower_bound: Dict[str, AbstractDataStructure], number_hours: int, week: int
) -> DataBase:
    database = DataBase()

    database.add_data("G1", "p_max", ConstantData(410))
    database.add_data("G1", "p_min", ConstantData(180))
    database.add_data("G1", "cost", ConstantData(96))
    database.add_data("G1", "startup_cost", ConstantData(100500))
    database.add_data("G1", "fixed_cost", ConstantData(1))
    database.add_data("G1", "d_min_up", ConstantData(8))
    database.add_data("G1", "d_min_down", ConstantData(8))
    database.add_data("G1", "nb_units_min", lower_bound["G1"])
    database.add_data("G1", "nb_units_max", ConstantData(1))
    database.add_data("G1", "failures", ConstantData(410))
    database.add_data("G1", "mingen", lower_bound["G1"])

    database.add_data("G2", "p_max", ConstantData(90))
    database.add_data("G2", "p_min", ConstantData(60))
    database.add_data("G2", "cost", ConstantData(137))
    database.add_data("G2", "startup_cost", ConstantData(24500))
    database.add_data("G2", "fixed_cost", ConstantData(1))
    database.add_data("G2", "d_min_up", ConstantData(11))
    database.add_data("G2", "d_min_down", ConstantData(11))
    database.add_data("G2", "nb_units_min", lower_bound["G2"])
    database.add_data("G2", "nb_units_max", ConstantData(3))
    database.add_data("G2", "failures", ConstantData(270))
    database.add_data("G2", "mingen", lower_bound["G2"])

    failures_3 = pd.DataFrame(
        np.repeat(get_failures_for_cluster3(week), 24),
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    database.add_data("G3", "p_max", ConstantData(275))
    database.add_data("G3", "p_min", ConstantData(150))
    database.add_data("G3", "cost", ConstantData(107))
    database.add_data("G3", "startup_cost", ConstantData(69500))
    database.add_data("G3", "fixed_cost", ConstantData(1))
    database.add_data("G3", "d_min_up", ConstantData(9))
    database.add_data("G3", "d_min_down", ConstantData(9))
    database.add_data("G3", "nb_units_min", lower_bound["G3"])
    database.add_data("G3", "nb_units_max", ConstantData(4))
    database.add_data("G3", "failures", TimeScenarioSeriesData(failures_3))
    database.add_data("G3", "mingen", lower_bound["G3"])

    database.add_data("U", "cost", ConstantData(10000))
    database.add_data("S", "cost", ConstantData(1))

    output_file = open("tests/functional/data_complex_case/milp/values-hourly.txt", "r")
    output = output_file.readlines()

    demand_data = pd.DataFrame(
        data=[
            float(line.strip().split("\t")[10])
            for line in output[168 * week + 7 : 168 * week + 7 + 168]
        ],
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    demand_data[0] = demand_data[0] - 300

    demand_time_scenario_series = TimeScenarioSeriesData(demand_data)
    database.add_data("D", "demand", demand_time_scenario_series)
    return database


def get_failures_for_cluster3(week: int) -> List:
    if week == 0:
        failures_3 = [1100, 1100, 0, 1100, 1100, 1100, 1100]
    elif week == 1:
        failures_3 = [1100, 1100, 1100, 1100, 1100, 0, 1100]

    return failures_3


def create_problem_accurate_heuristic(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    thermal_cluster: str,
    week: int,
) -> OptimizationProblem:

    database = DataBase()

    if thermal_cluster == "G1":
        database.add_data("G1", "p_max", ConstantData(410))
        database.add_data("G1", "p_min", ConstantData(180))
        database.add_data("G1", "cost", ConstantData(96))
        database.add_data("G1", "startup_cost", ConstantData(100500))
        database.add_data("G1", "fixed_cost", ConstantData(1))
        database.add_data("G1", "d_min_up", ConstantData(8))
        database.add_data("G1", "d_min_down", ConstantData(8))
        database.add_data("G1", "nb_units_min", lower_bound["G1"])
        database.add_data("G1", "nb_units_max", ConstantData(1))
        database.add_data("G1", "failures", ConstantData(410))
        database.add_data("G1", "mingen", lower_bound["G1"])
    elif thermal_cluster == "G2":
        database.add_data("G2", "p_max", ConstantData(90))
        database.add_data("G2", "p_min", ConstantData(60))
        database.add_data("G2", "cost", ConstantData(137))
        database.add_data("G2", "startup_cost", ConstantData(24500))
        database.add_data("G2", "fixed_cost", ConstantData(1))
        database.add_data("G2", "d_min_up", ConstantData(11))
        database.add_data("G2", "d_min_down", ConstantData(11))
        database.add_data("G2", "nb_units_min", lower_bound["G2"])
        database.add_data("G2", "nb_units_max", ConstantData(3))
        database.add_data("G2", "failures", ConstantData(270))
        database.add_data("G2", "mingen", lower_bound["G2"])
    elif thermal_cluster == "G3":
        failures_3 = pd.DataFrame(
            np.repeat(get_failures_for_cluster3(week), 24),
            index=[i for i in range(number_hours)],
            columns=[0],
        )

        database.add_data("G3", "p_max", ConstantData(275))
        database.add_data("G3", "p_min", ConstantData(150))
        database.add_data("G3", "cost", ConstantData(107))
        database.add_data("G3", "startup_cost", ConstantData(69500))
        database.add_data("G3", "fixed_cost", ConstantData(1))
        database.add_data("G3", "d_min_up", ConstantData(9))
        database.add_data("G3", "d_min_down", ConstantData(9))
        database.add_data("G3", "nb_units_min", lower_bound["G3"])
        database.add_data("G3", "nb_units_max", ConstantData(4))
        database.add_data("G3", "failures", TimeScenarioSeriesData(failures_3))
        database.add_data("G3", "mingen", lower_bound["G3"])

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
    lower_bound: List[List[float]], number_hours: int, thermal_cluster: str, week: int
) -> pd.DataFrame:

    delta = {"G1": 8, "G2": 11, "G3": 9}[thermal_cluster]
    pmax = {"G1": 410, "G2": 90, "G3": 275}[thermal_cluster]
    pmin = {"G1": 180, "G2": 60, "G3": 150}[thermal_cluster]
    pdispo = {
        "G1": np.array(410),
        "G2": np.array(270),
        "G3": np.reshape(
            np.repeat(get_failures_for_cluster3(week), 24), (number_hours, 1)
        ),
    }

    cost = pd.DataFrame(
        np.zeros((delta + 1, 1)),
        index=[i for i in range(delta + 1)],
        columns=[0],
    )
    n = np.zeros((number_hours, delta + 1, 1))
    for h in range(delta + 1):
        cost_h = 0
        n_k = max(
            [convert_to_integer(lower_bound[0][j] / pmax) for j in range(h)]
            + [
                convert_to_integer(lower_bound[0][j] / pmax)
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
                    convert_to_integer(lower_bound[0][j] / pmax)
                    for j in range(k, min(number_hours - delta + h, k + delta))
                ]
            )
            cost_h += (min(number_hours - delta + h, k + delta) - k) * n_k
            n[k : min(number_hours - delta + h, k + delta), h, 0] = n_k
            t += delta
        cost.iloc[h, 0] = cost_h

    hmin = np.argmin(cost.values[:, 0])
    mingen_heuristic = pd.DataFrame(
        np.minimum(n[:, hmin, :] * pmin, pdispo[thermal_cluster]),
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return mingen_heuristic


def convert_to_integer(x: float) -> int:
    return ceil(round(x, 12))
