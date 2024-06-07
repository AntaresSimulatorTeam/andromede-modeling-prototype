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


def test_one_problem_per_scenario() -> None:
    """ """
    number_hours = 168
    scenarios = 2

    for scenario in range(scenarios):
        for week in range(2):
            problem = create_complex_problem(
                {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
                number_hours,
                lp_relaxation=False,
                fast=False,
                week=week,
                scenarios=[scenario],
            )

            parameters = pywraplp.MPSolverParameters()
            parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
            parameters.SetIntegerParam(parameters.SCALING, 0)
            parameters.SetDoubleParam(parameters.PRIMAL_TOLERANCE, 1e-7)
            parameters.SetDoubleParam(parameters.DUAL_TOLERANCE, 1e-7)
            parameters.SetDoubleParam(parameters.RELATIVE_MIP_GAP, 0.0001)

            status = problem.solver.Solve(parameters)

            assert status == problem.solver.OPTIMAL

            expected_cost = [[78933841, 102109698], [17472101, 17424769]]
            assert problem.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )


def test_one_problem_for_all_scenarios() -> None:
    """ """
    number_hours = 168
    scenarios = [0, 1]

    for week in range(2):
        problem = create_complex_problem(
            {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
            number_hours,
            lp_relaxation=False,
            fast=False,
            week=week,
            scenarios=scenarios,
        )

        parameters = pywraplp.MPSolverParameters()
        parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
        parameters.SetIntegerParam(parameters.SCALING, 0)
        parameters.SetDoubleParam(parameters.PRIMAL_TOLERANCE, 1e-7)
        parameters.SetDoubleParam(parameters.DUAL_TOLERANCE, 1e-7)
        parameters.SetDoubleParam(parameters.RELATIVE_MIP_GAP, 0.0001)

        status = problem.solver.Solve(parameters)

        assert status == problem.solver.OPTIMAL

        expected_cost = [[78933841, 102109698], [17472101, 17424769]]
        assert problem.solver.Objective().Value() == pytest.approx(
            sum([expected_cost[s][week] for s in scenarios]) / len(scenarios)
        )


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


def create_complex_problem(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    lp_relaxation: bool,
    fast: bool,
    week: int,
    scenarios: List[int],
) -> OptimizationProblem:

    database = generate_database(
        lower_bound, number_hours, week=week, scenarios=scenarios
    )

    time_block = TimeBlock(1, [i for i in range(number_hours)])

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    demand = create_component(model=DEMAND_MODEL, id="D")

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
        len(scenarios),
        border_management=BlockBorderManagement.CYCLE,
        solver_id="XPRESS",
    )

    return problem


def generate_database(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    week: int,
    scenarios: List[int],
) -> DataBase:
    database = DataBase()

    failures_1 = pd.DataFrame(
        np.transpose(
            [
                np.repeat(get_failures_for_cluster1(week, scenario), 24)
                for scenario in scenarios
            ]
        ),
        index=[i for i in range(number_hours)],
        columns=list(range(len(scenarios))),
    )

    database.add_data("G1", "p_max", ConstantData(410))
    database.add_data("G1", "p_min", ConstantData(180))
    database.add_data("G1", "cost", ConstantData(96))
    database.add_data("G1", "startup_cost", ConstantData(100500))
    database.add_data("G1", "fixed_cost", ConstantData(1))
    database.add_data("G1", "d_min_up", ConstantData(8))
    database.add_data("G1", "d_min_down", ConstantData(8))
    database.add_data("G1", "nb_units_min", lower_bound["G1"])
    database.add_data("G1", "nb_units_max", ConstantData(1))
    database.add_data("G1", "failures", TimeScenarioSeriesData(failures_1))
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
        np.transpose(
            [
                np.repeat(get_failures_for_cluster3(week, scenario), 24)
                for scenario in scenarios
            ]
        ),
        index=[i for i in range(number_hours)],
        columns=list(range(len(scenarios))),
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

    output = {}
    for scenario in scenarios:
        output_file = open(
            "tests/functional/data_complex_case/milp/"
            + str(scenario)
            + "/values-hourly.txt",
            "r",
        )
        output[scenario] = output_file.readlines()

    demand_data = pd.DataFrame(
        data=np.transpose(
            [
                [
                    float(line.strip().split("\t")[10]) - 300
                    for line in output[scenario][168 * week + 7 : 168 * week + 7 + 168]
                ]
                for scenario in scenarios
            ]
        ),
        index=[i for i in range(number_hours)],
        columns=list(range(len(scenarios))),
    )

    demand_time_scenario_series = TimeScenarioSeriesData(demand_data)
    database.add_data("D", "demand", demand_time_scenario_series)
    return database


def get_failures_for_cluster3(week: int, scenario: int) -> List:
    if scenario == 0:
        if week == 0:
            failures_3 = [1100, 1100, 0, 1100, 1100, 1100, 1100]
        elif week == 1:
            failures_3 = [1100, 1100, 1100, 1100, 1100, 0, 1100]
    elif scenario == 1:
        failures_3 = [1100, 1100, 1100, 1100, 1100, 1100, 1100]

    return failures_3


def get_failures_for_cluster1(week: int, scenario: int) -> List:
    if scenario == 0:
        failures = [410, 410, 410, 410, 410, 410, 410]
    elif scenario == 1:
        failures = [410, 410, 410, 410, 0, 410, 410]

    return failures
