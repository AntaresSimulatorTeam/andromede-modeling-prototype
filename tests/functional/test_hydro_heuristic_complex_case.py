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

from typing import Dict, List

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pandas as pd

from andromede.expression import literal, param, var, ExpressionNode
from andromede.expression.indexing_structure import IndexingStructure
from andromede.model import Model, float_parameter, float_variable, model
from andromede.model.constraint import Constraint
from andromede.model.parameter import float_parameter
from andromede.model.variable import float_variable
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
from andromede.model.constraint import Constraint
from andromede.model.parameter import Parameter
from andromede.model.variable import Variable
from andromede.simulation.optimization import OptimizationProblem
from tests.functional.libs.lib_hydro_heuristic import HYDRO_MODEL

CONSTANT = IndexingStructure(False, False)
TIME_AND_SCENARIO_FREE = IndexingStructure(True, True)
ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, True)
NON_ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, False)
CONSTANT_PER_SCENARIO = IndexingStructure(False, True)


def get_heuristic_hydro_model(
    hydro_model: Model,
    horizon: str,
) -> Model:

    HYDRO_HEURISTIC = model(
        id="H",
        parameters=[p for p in hydro_model.parameters.values()]
        + get_heuristic_parameters(),
        variables=[v for v in hydro_model.variables.values()]
        + get_heuristic_variables(),
        constraints=[c for c in hydro_model.constraints.values()]
        + get_heuristic_constraints(horizon),
        objective_operational_contribution=get_heuristic_objective(),
    )
    return HYDRO_HEURISTIC


def get_heuristic_objective() -> ExpressionNode:
    return (
        param("gamma_d") * var("distance_between_target_and_generating")
        + param("gamma_v+") * var("violation_upper_rule_curve")
        + param("gamma_v-") * var("violation_lower_rule_curve")
        + param("gamma_o") * var("overflow")
        + param("gamma_s") * var("level")
    ).sum().expec() + (
        param("gamma_delta") * var("max_distance_between_target_and_generating")
        + param("gamma_y") * var("max_violation_lower_rule_curve")
        + param("gamma_w") * var("gap_to_target")
    ).expec()


def get_heuristic_variables() -> List[Variable]:
    return [
        float_variable(
            "distance_between_target_and_generating",
            lower_bound=literal(0),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "max_distance_between_target_and_generating",
            lower_bound=literal(0),
            structure=CONSTANT_PER_SCENARIO,
        ),
        float_variable(
            "violation_lower_rule_curve",
            lower_bound=literal(0),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "violation_upper_rule_curve",
            lower_bound=literal(0),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "max_violation_lower_rule_curve",
            lower_bound=literal(0),
            structure=CONSTANT_PER_SCENARIO,
        ),
        float_variable(
            "gap_to_target",
            lower_bound=literal(0),
            structure=CONSTANT_PER_SCENARIO,
        ),
    ]


def get_heuristic_parameters() -> List[Parameter]:
    return [
        float_parameter("generating_target", TIME_AND_SCENARIO_FREE),
        float_parameter("overall_target", CONSTANT_PER_SCENARIO),
        float_parameter("gamma_d", CONSTANT),
        float_parameter("gamma_delta", CONSTANT),
        float_parameter("gamma_y", CONSTANT),
        float_parameter("gamma_w", CONSTANT),
        float_parameter("gamma_v+", CONSTANT),
        float_parameter("gamma_v-", CONSTANT),
        float_parameter("gamma_o", CONSTANT),
        float_parameter("gamma_s", CONSTANT),
    ]


def get_heuristic_constraints(horizon: str) -> List[Constraint]:
    list_constraint = [
        Constraint(
            "Respect generating target",
            var("generating").sum() + var("gap_to_target") == param("overall_target"),
        ),
        Constraint(
            "Definition of distance between target and generating",
            var("distance_between_target_and_generating")
            >= param("generating_target") - var("generating"),
        ),
        Constraint(
            "Definition of distance between generating and target",
            var("distance_between_target_and_generating")
            >= var("generating") - param("generating_target"),
        ),
        Constraint(
            "Definition of max distance between generating and target",
            var("max_distance_between_target_and_generating")
            >= var("distance_between_target_and_generating"),
        ),
        Constraint(
            "Definition of violation of lower rule curve",
            var("violation_lower_rule_curve") + var("level")
            >= param("lower_rule_curve"),
        ),
        Constraint(
            "Definition of violation of upper rule curve",
            var("violation_upper_rule_curve") - var("level")
            >= -param("upper_rule_curve"),
        ),
        Constraint(
            "Definition of max violation of lower rule curve",
            var("max_violation_lower_rule_curve") >= var("violation_lower_rule_curve"),
        ),
    ]
    if horizon == "monthly":
        list_constraint.append(Constraint("No overflow", var("overflow") <= literal(0)))
        list_constraint.append(
            Constraint("No gap to target", var("gap_to_target") <= literal(0))
        )

    return list_constraint


def test_hydro_heuristic() -> None:
    """ """
    scenarios = 1
    interdaily_breakdown = 3

    capacity = 1711510

    for scenario in range(scenarios):
        initial_level = 0.5 * capacity

        # Répartition des apports mensuels
        (
            monthly_demand,
            monthly_inflow,
            monthly_max_generating,
        ) = get_all_data(scenario, "monthly")
        monthly_target = get_target(monthly_demand, sum(monthly_inflow))

        # Ajustement de la réapartition mensuelle
        problem = create_hydro_problem(
            horizon="monthly",
            target=monthly_target,
            inflow=monthly_inflow,
            max_generating=monthly_max_generating,
            initial_level=initial_level,
        )

        status, monthly_generation, _ = solve_hydro_problem(problem)

        assert status == problem.solver.OPTIMAL

        all_daily_generation: List[float] = []
        day_in_year = 0
        (
            daily_demand,
            daily_inflow,
            daily_max_generating,
        ) = get_all_data(scenario, "daily")

        for month in range(12):
            number_day_month = get_number_of_days_in_month(month)
            # Répartition des crédits de turbinage jour par jour

            daily_target = get_target(
                demand=daily_demand[day_in_year : day_in_year + number_day_month],
                total_target=monthly_generation[month],
                inter_breakdown=interdaily_breakdown,
            )
            # Ajustement de la répartition jour par jour
            problem = create_hydro_problem(
                horizon="daily",
                target=daily_target,
                inflow=daily_inflow[day_in_year : day_in_year + number_day_month],
                max_generating=daily_max_generating[
                    day_in_year : day_in_year + number_day_month
                ],
                initial_level=initial_level,
            )

            status, daily_generation, initial_level = solve_hydro_problem(problem)

            assert status == problem.solver.OPTIMAL

            all_daily_generation = all_daily_generation + daily_generation
            day_in_year += number_day_month

        # Calcul des cibles hebdomadaires
        weekly_target = calculate_weekly_target(
            all_daily_generation,
        )

        # Vérification des valeurs trouvées
        expected_output_file = open(
            "tests/functional/data_complex_case/hydro/values-weekly.txt",
            "r",
        )
        expected_output = expected_output_file.readlines()
        for week in range(52):
            assert float(expected_output[week + 7].strip().split("\t")[9]) == round(
                weekly_target[week]
            )


def calculate_weekly_target(all_daily_generation: list[float]) -> list[float]:
    weekly_target = np.zeros(52)
    week = 0
    day_in_week = 0
    day_in_year = 0

    while week < 52:
        weekly_target[week] += all_daily_generation[day_in_year]
        day_in_year += 1
        day_in_week += 1
        if day_in_week >= 7:
            week += 1
            day_in_week = 0

    return list(weekly_target)


def get_number_of_days_in_month(month: int) -> int:
    number_day_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    return number_day_month


def get_target(
    demand: List[float], total_target: float, inter_breakdown: int = 1
) -> List[float]:
    target = (
        total_target
        * np.power(demand, inter_breakdown)
        / sum(np.power(demand, inter_breakdown))
    )

    return list(target)


def get_all_data(
    scenario: int, horizon: str
) -> tuple[List[float], List[float], List[float]]:
    if horizon == "monthly":
        hours_aggregated_time_steps = [
            24 * get_number_of_days_in_month(m) for m in range(12)
        ]
    elif horizon == "daily":
        hours_aggregated_time_steps = [24 for d in range(365)]

    demand = get_input_data(
        name_file="load",
        column=scenario,
        hours_aggregated_time_steps=hours_aggregated_time_steps,
        hours_input=1,
        operator="sum",
    )
    inflow = get_input_data(
        name_file="mod",
        column=scenario,
        hours_aggregated_time_steps=hours_aggregated_time_steps,
        hours_input=24,
        operator="sum",
    )
    max_generating = get_input_data(
        name_file="maxpower",
        column=0,
        hours_aggregated_time_steps=hours_aggregated_time_steps,
        hours_input=24,
        operator="sum",
    )
    max_generating = [x * 24 for x in max_generating]
    return (
        demand,
        inflow,
        max_generating,
    )


def create_hydro_problem(
    horizon: str,
    target: List[float],
    inflow: List[float],
    max_generating: List[float],
    initial_level: float,
) -> OptimizationProblem:
    database = generate_database(
        target=target,
        inflow=inflow,
        max_generating=max_generating,
        initial_level=initial_level,
    )

    database = add_objective_coefficients_to_database(database, horizon)

    time_block = TimeBlock(1, [i for i in range(len(target))])
    scenarios = 1

    hydro = create_component(
        model=get_heuristic_hydro_model(HYDRO_MODEL, horizon), id="H"
    )

    network = Network("test")
    network.add_component(hydro)

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=(BlockBorderManagement.CYCLE),
        solver_id="XPRESS",
    )

    return problem


def solve_hydro_problem(problem: OptimizationProblem) -> tuple[int, list[float], float]:
    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    problem.solver.EnableOutput()

    status = problem.solver.Solve(parameters)

    output = OutputValues(problem)

    return (
        status,
        output.component("H").var("generating").value[0],  # type:ignore
        output.component("H").var("level").value[0][-1],  # type:ignore
    )


def generate_database(
    target: List[float],
    inflow: List[float],
    max_generating: List[float],
    initial_level: float,
) -> DataBase:
    database = DataBase()

    database.add_data("H", "capacity", ConstantData(1711510))
    database.add_data("H", "initial_level", ConstantData(initial_level))

    inflow_data = pd.DataFrame(
        inflow,
        index=[i for i in range(len(inflow))],
        columns=[0],
    )
    database.add_data("H", "inflow", TimeScenarioSeriesData(inflow_data))

    target_data = pd.DataFrame(
        target,
        index=[i for i in range(len(target))],
        columns=[0],
    )
    database.add_data("H", "generating_target", TimeScenarioSeriesData(target_data))
    database.add_data("H", "overall_target", ConstantData(sum(target)))

    database.add_data("H", "lower_rule_curve", ConstantData(0))
    database.add_data("H", "upper_rule_curve", ConstantData(1711510))
    database.add_data("H", "min_generating", ConstantData(0))

    database.add_data(
        "H",
        "max_generating",
        TimeSeriesData(
            {TimeIndex(i): max_generating[i] for i in range(len(max_generating))}
        ),
    )

    database.add_data(
        "H",
        "max_epsilon",
        TimeSeriesData(
            {TimeIndex(i): 1711510 if i == 0 else 0 for i in range(len(max_generating))}
        ),
    )

    return database


def add_objective_coefficients_to_database(
    database: DataBase, horizon: str
) -> DataBase:
    objective_function_cost = {
        "gamma_d": 1,
        "gamma_delta": 1 if horizon == "monthly" else 2,
        "gamma_y": 100000 if horizon == "monthly" else 68,
        "gamma_w": 0 if horizon == "monthly" else 34,
        "gamma_v+": 100 if horizon == "monthly" else 0,
        "gamma_v-": 100 if horizon == "monthly" else 68,
        "gamma_o": 0 if horizon == "monthly" else 23 * 68 + 1,
        "gamma_s": 0 if horizon == "monthly" else -1 / 32,
    }

    for name, coeff in objective_function_cost.items():
        database.add_data("H", name, ConstantData(coeff))

    return database


def get_input_data(
    name_file: str,
    column: int,
    hours_aggregated_time_steps: List[int],
    hours_input: int,
    operator: str,
) -> List[float]:
    data = np.loadtxt("tests/functional/data_complex_case/hydro/" + name_file + ".txt")
    data = data[:, column]
    aggregated_data: List[float] = []
    hour = 0
    for hours_time_step in hours_aggregated_time_steps:
        assert hours_time_step % hours_input == 0
        if operator == "sum":
            aggregated_data.append(
                np.sum(data[hour : hour + hours_time_step // hours_input])
            )
        elif operator == "lag_first_element":
            aggregated_data.append(
                data[(hour + hours_time_step // hours_input) % len(data)]
            )
        hour += hours_time_step // hours_input
    return aggregated_data
