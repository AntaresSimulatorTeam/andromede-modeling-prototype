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


def get_model_fast_heuristic(Q: int, delta: int) -> Model:
    BLOCK_MODEL_FAST_HEURISTIC = model(
        id="BLOCK_FAST",
        parameters=[
            float_parameter("n_guide", TIME_AND_SCENARIO_FREE),
            float_parameter("delta", CONSTANT),
            float_parameter("n_max", CONSTANT),
        ]
        + [
            int_parameter(f"alpha_{k}_{h}", NON_ANTICIPATIVE_TIME_VARYING)
            for k in range(Q)
            for h in range(delta)
        ]
        + [
            int_parameter(f"alpha_ajust_{h}", NON_ANTICIPATIVE_TIME_VARYING)
            for h in range(delta)
        ],
        variables=[
            float_variable(
                f"n_block_{k}",
                lower_bound=literal(0),
                upper_bound=param("n_max"),
                structure=CONSTANT_PER_SCENARIO,
            )
            for k in range(Q)
        ]
        + [
            float_variable(
                "n_ajust",
                lower_bound=literal(0),
                upper_bound=param("n_max"),
                structure=CONSTANT_PER_SCENARIO,
            )
        ]
        + [
            int_variable(
                f"t_ajust_{h}",
                lower_bound=literal(0),
                upper_bound=literal(1),
                structure=CONSTANT_PER_SCENARIO,
            )
            for h in range(delta)
        ]
        + [
            float_variable(
                "n",
                lower_bound=literal(0),
                upper_bound=param("n_max"),
                structure=TIME_AND_SCENARIO_FREE,
            )
        ],
        constraints=[
            Constraint(
                f"Definition of n block {k} for {h}",
                var(f"n_block_{k}")
                >= param("n_guide") * param(f"alpha_{k}_{h}")
                - param("n_max") * (literal(1) - var(f"t_ajust_{h}")),
            )
            for k in range(Q)
            for h in range(delta)
        ]
        + [
            Constraint(
                f"Definition of n ajust for {h}",
                var(f"n_ajust")
                >= param("n_guide") * param(f"alpha_ajust_{h}")
                - param("n_max") * (literal(1) - var(f"t_ajust_{h}")),
            )
            for h in range(delta)
        ]
        + [
            Constraint(
                f"Definition of n with relation to block {k} for {h}",
                var(f"n")
                >= param(f"alpha_{k}_{h}") * var(f"n_block_{k}")
                - param("n_max") * (literal(1) - var(f"t_ajust_{h}")),
            )
            for k in range(Q)
            for h in range(delta)
        ]
        + [
            Constraint(
                f"Definition of n with relation to ajust for {h}",
                var(f"n")
                >= param(f"alpha_ajust_{h}") * var(f"n_ajust")
                - param("n_max") * (literal(1) - var(f"t_ajust_{h}")),
            )
            for h in range(delta)
        ]
        + [
            Constraint(
                "Choose one t ajust",
                literal(0) + sum([var(f"t_ajust_{h}") for h in range(delta)])
                == literal(1),
            )
        ],
        objective_operational_contribution=(var("n")).sum().expec()
        + sum(
            [var(f"t_ajust_{h}") * (h + 1) / 10 / delta for h in range(delta)]
        ).expec(),  # type:ignore
    )
    return BLOCK_MODEL_FAST_HEURISTIC


def test_milp_version() -> None:
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
                scenario=scenario,
            )

            parameters = pywraplp.MPSolverParameters()
            parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
            parameters.SetIntegerParam(parameters.SCALING, 0)

            status = problem.solver.Solve(parameters)

            assert status == problem.solver.OPTIMAL

            check_output_values(problem, "milp", week, scenario=scenario)

            expected_cost = [[78933841, 102109698], [17472101, 17424769]]
            assert problem.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )


def check_output_values(
    problem: OptimizationProblem, mode: str, week: int, scenario: int
) -> None:
    output = OutputValues(problem)

    expected_output_clusters_file = open(
        "tests/functional/data_complex_case/"
        + mode
        + "/"
        + str(scenario)
        + "/details-hourly.txt",
        "r",
    )
    expected_output_clusters = expected_output_clusters_file.readlines()

    expected_output_general_file = open(
        "tests/functional/data_complex_case/"
        + mode
        + "/"
        + str(scenario)
        + "/values-hourly.txt",
        "r",
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
    scenarios = 2

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for scenario in range(scenarios):
        for week in range(2):
            # First optimization
            problem_optimization_1 = create_complex_problem(
                {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
                number_hours,
                lp_relaxation=True,
                fast=False,
                week=week,
                scenario=scenario,
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
                            np.round(
                                np.array(output_1.component(g).var("nb_on").value), 12
                            )
                        )
                    ),
                    index=[i for i in range(number_hours)],
                    columns=[0],
                )
                n_guide = TimeScenarioSeriesData(nb_on_1)

                # Solve heuristic problem
                problem_accurate_heuristic = create_problem_accurate_heuristic(
                    {g: n_guide},
                    number_hours,
                    thermal_cluster=g,
                    week=week,
                    scenario=scenario,
                )
                status = problem_accurate_heuristic.solver.Solve(parameters)

                assert status == problem_accurate_heuristic.solver.OPTIMAL

                output_heuristic = OutputValues(problem_accurate_heuristic)
                nb_on_heuristic = pd.DataFrame(
                    np.transpose(
                        np.ceil(
                            np.array(output_heuristic.component(g).var("nb_on").value)
                        )
                    ),
                    index=[i for i in range(number_hours)],
                    columns=[0],
                )
                nb_on_min[g] = TimeScenarioSeriesData(nb_on_heuristic)

            # Second optimization with lower bound modified
            problem_optimization_2 = create_complex_problem(
                nb_on_min,
                number_hours,
                lp_relaxation=True,
                fast=False,
                week=week,
                scenario=scenario,
            )
            status = problem_optimization_2.solver.Solve(parameters)

            assert status == problem_optimization_2.solver.OPTIMAL

            check_output_values(
                problem_optimization_2, "accurate", week, scenario=scenario
            )

            expected_cost = [
                [78996726, 102215087 - 69500],
                [17587733, 17650089 - 10081],
            ]
            assert problem_optimization_2.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    """

    number_hours = 168
    scenarios = 2
    weeks = 2

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for scenario in range(scenarios):
        for week in range(weeks):
            # First optimization
            problem_optimization_1 = create_complex_problem(
                {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
                number_hours,
                lp_relaxation=True,
                fast=True,
                week=week,
                scenario=scenario,
            )
            status = problem_optimization_1.solver.Solve(parameters)

            assert status == problem_optimization_1.solver.OPTIMAL

            # Get number of on units
            output_1 = OutputValues(problem_optimization_1)

            # Solve heuristic problem
            mingen: Dict[str, AbstractDataStructure] = {}
            for g in ["G1", "G2", "G3"]:  #
                pmax = {"G1": 410, "G2": 90, "G3": 275}[g]
                nb_on_1 = np.ceil(
                    np.round(
                        np.array(
                            output_1.component(g)
                            .var("generation")
                            .value[0]  # type:ignore
                        )
                        / pmax,
                        12,
                    )
                )
                n_guide = TimeSeriesData(
                    {TimeIndex(i): nb_on_1[i] for i in range(number_hours)}
                )
                mingen_heuristic = create_problem_fast_heuristic(
                    n_guide,
                    number_hours,
                    thermal_cluster=g,
                    week=week,
                    scenario=scenario,
                )

                mingen[g] = TimeScenarioSeriesData(mingen_heuristic)

            # Second optimization with lower bound modified
            problem_optimization_2 = create_complex_problem(
                mingen,
                number_hours,
                lp_relaxation=True,
                fast=True,
                week=week,
                scenario=scenario,
            )
            status = problem_optimization_2.solver.Solve(parameters)

            assert status == problem_optimization_2.solver.OPTIMAL

            check_output_values(problem_optimization_2, "fast", week, scenario)

            expected_cost = [
                [79277215 - 630089, 102461792 - 699765],
                [17803738 - 661246, 17720390 - 661246],
            ]
            assert problem_optimization_2.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )


def create_complex_problem(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    lp_relaxation: bool,
    fast: bool,
    week: int,
    scenario: int,
) -> OptimizationProblem:

    database = generate_database(
        lower_bound, number_hours, week=week, scenario=scenario
    )

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
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    week: int,
    scenario: int,
) -> DataBase:
    database = DataBase()

    failures_1 = pd.DataFrame(
        np.repeat(get_failures_for_cluster1(week, scenario), 24),
        index=[i for i in range(number_hours)],
        columns=[0],
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
        np.repeat(get_failures_for_cluster3(week, scenario), 24),
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

    output_file = open(
        "tests/functional/data_complex_case/milp/"
        + str(scenario)
        + "/values-hourly.txt",
        "r",
    )
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


def create_problem_accurate_heuristic(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    thermal_cluster: str,
    week: int,
    scenario: int,
) -> OptimizationProblem:

    database = DataBase()

    if thermal_cluster == "G1":
        failures_1 = pd.DataFrame(
            np.repeat(get_failures_for_cluster1(week, scenario), 24),
            index=[i for i in range(number_hours)],
            columns=[0],
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
            np.repeat(get_failures_for_cluster3(week, scenario), 24),
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
    lower_bound: AbstractDataStructure,
    number_hours: int,
    thermal_cluster: str,
    week: int,
    scenario: int,
) -> pd.DataFrame:

    delta = {"G1": 8, "G2": 11, "G3": 9}[thermal_cluster]
    pmin = {"G1": 180, "G2": 60, "G3": 150}[thermal_cluster]
    pdispo = {
        "G1": np.reshape(
            np.repeat(get_failures_for_cluster1(week, scenario), 24), (number_hours, 1)
        ),
        "G2": np.array(270),
        "G3": np.reshape(
            np.repeat(get_failures_for_cluster3(week, scenario), 24), (number_hours, 1)
        ),
    }[thermal_cluster]
    nmax = {"G1": 1, "G2": 3, "G3": 4}[thermal_cluster]

    # nopt = {
    #     "G1": np.ones((number_hours)),
    #     "G2": np.array(
    #         [
    #             (
    #                 3.0
    #                 if i in list(range(50, 72))
    #                 else (1.0 if i in list(range(39, 50)) else 0.0)
    #             )
    #             for i in range(number_hours)
    #         ]
    #     ),
    # }[thermal_cluster]
    number_blocks = number_hours // delta

    database = DataBase()

    database.add_data("B", "n_max", ConstantData(nmax))
    database.add_data("B", "delta", ConstantData(delta))
    database.add_data("B", "n_guide", lower_bound)
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
    ).reshape((168, 1))
    mingen_heuristic = pd.DataFrame(
        np.minimum(n_heuristic * pmin, pdispo),
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return mingen_heuristic


def convert_to_integer(x: float) -> int:
    return ceil(round(x, 12))
