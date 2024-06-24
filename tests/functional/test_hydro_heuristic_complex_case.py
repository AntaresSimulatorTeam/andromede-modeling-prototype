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

from andromede.expression import literal, param, var
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

CONSTANT = IndexingStructure(False, False)
TIME_AND_SCENARIO_FREE = IndexingStructure(True, True)
ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, True)
NON_ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, False)
CONSTANT_PER_SCENARIO = IndexingStructure(False, True)


HYDRO_MODEL = model(
    id="H",
    parameters=[
        float_parameter("max_generating", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("min_generating", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("capacity", CONSTANT),
        float_parameter("initial_level", CONSTANT_PER_SCENARIO),
        float_parameter("inflow", TIME_AND_SCENARIO_FREE),
        float_parameter(
            "max_epsilon", NON_ANTICIPATIVE_TIME_VARYING
        ),  # not really a parameter, it is just to implement correctly one constraint
        float_parameter("lower_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("upper_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
    ],
    variables=[
        float_variable(
            "generating",
            lower_bound=param("min_generating"),
            upper_bound=param("max_generating"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "level",
            lower_bound=literal(0),
            upper_bound=param("capacity"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "overflow",
            lower_bound=literal(0),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "epsilon",
            lower_bound=-param("max_epsilon"),
            upper_bound=param("max_epsilon"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
    ],
    constraints=[
        Constraint(
            "Level balance",
            var("level")
            == var("level").shift(-1)
            - var("generating")
            - var("overflow")
            + param("inflow")
            + var("epsilon"),
        ),
        Constraint(
            "Initial level",
            var("level").eval(literal(0))
            == param("initial_level")
            - var("generating").eval(literal(0))
            - var("overflow").eval(literal(0))
            + param("inflow").eval(literal(0)),
        ),
    ],
)


def get_heuristic_hydro_model(
    hydro_model: Model,
    horizon: str,
) -> Model:

    list_constraint = [c for c in hydro_model.constraints.values()] + [
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
    ]
    if horizon == "monthly":
        list_constraint.append(Constraint("No overflow", var("overflow") <= literal(0)))
        list_constraint.append(
            Constraint("No gap to target", var("gap_to_target") <= literal(0))
        )

    HYDRO_HEURISTIC = model(
        id="H",
        parameters=[p for p in hydro_model.parameters.values()]
        + [
            float_parameter("generating_target", TIME_AND_SCENARIO_FREE),
            float_parameter("overall_target", CONSTANT_PER_SCENARIO),
            float_parameter("gamma_d", CONSTANT),
        ],
        variables=[v for v in hydro_model.variables.values()]
        + [
            float_variable(
                "distance_between_target_and_generating",
                lower_bound=literal(0),
                structure=TIME_AND_SCENARIO_FREE,
            ),
        ]
        + [
            (
                float_variable(
                    "gap_to_target",
                    lower_bound=literal(0),
                    structure=CONSTANT_PER_SCENARIO,
                )
                if horizon == "daily"
                else float_variable(
                    "gap_to_target",
                    lower_bound=literal(0),
                    upper_bound=literal(0),
                    structure=CONSTANT,
                )
            )
        ],
        constraints=list_constraint,
        objective_operational_contribution=(
            param("gamma_d") * var("distance_between_target_and_generating")
        )
        .sum()
        .expec(),
    )
    return HYDRO_HEURISTIC


def test_hydro_heuristic() -> None:
    """ """
    scenarios = 1
    interdaily_breakdown = 3

    for scenario in range(scenarios):
        # Répartition des apports mensuels
        monthly_demand = get_load_data(scenario, "monthly")
        monthly_inflow = get_inflow_data(scenario, "monthly")
        monthly_target = (
            sum(monthly_inflow) * np.array(monthly_demand) / sum(monthly_demand)
        )
        monthly_max_generating = get_maxpower_data("monthly")

        # Ajustement de la réapartition mensuelle
        initial_level = 0.5 * 1711510
        monthly_generation, _ = create_hydro_problem(
            horizon="monthly",
            target=list(monthly_target),
            inflow=list(monthly_inflow),
            max_generating=monthly_max_generating,
            initial_level=initial_level,
        )

        weekly_target = np.zeros(52)
        week = 0
        day_in_week = 0
        day_in_year = 0
        daily_demand = get_load_data(scenario, "daily")
        daily_inflow = get_inflow_data(scenario, "daily")
        daily_max_generating = get_maxpower_data("daily")

        for month in range(12):
            number_day_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
            # Répartition des crédits de turbinage jour par jour

            daily_target = (
                monthly_generation[month]
                * np.power(
                    daily_demand[day_in_year : day_in_year + number_day_month],
                    interdaily_breakdown,
                )
                / sum(
                    np.power(
                        daily_demand[day_in_year : day_in_year + number_day_month],
                        interdaily_breakdown,
                    )
                )
            )
            # Ajustement de la répartition jour par jour
            daily_generation, initial_level = create_hydro_problem(
                horizon="daily",
                target=list(daily_target),
                inflow=list(daily_inflow),
                max_generating=list(
                    daily_max_generating[day_in_year : day_in_year + number_day_month]
                ),
                initial_level=initial_level,
            )

            # Calcul des cibles hebdomadaires
            day_in_month = 0
            while day_in_month < number_day_month and week < 52:
                weekly_target[week] += daily_generation[day_in_month]
                day_in_month += 1
                day_in_week += 1
                if day_in_week >= 7:
                    week += 1
                    day_in_week = 0
            day_in_year += number_day_month

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


def create_hydro_problem(
    horizon: str,
    target: List[float],
    inflow: List[float],
    max_generating: List[float],
    initial_level: float,
) -> tuple[List[float], float]:
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

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    status = problem.solver.Solve(parameters)

    assert status == problem.solver.OPTIMAL

    output = OutputValues(problem)

    return (
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
    }

    for name, coeff in objective_function_cost.items():
        database.add_data("H", name, ConstantData(coeff))

    return database


def get_load_data(scenario: int, time_step: str) -> List[float]:
    data = np.loadtxt("tests/functional/data_complex_case/hydro/load.txt")
    data = data[:, scenario]
    if time_step == "monthly":
        montly_data = []
        hour = 0
        for day_for_month in [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]:
            montly_data.append(np.sum(data[hour : hour + 24 * day_for_month]))
            hour += 24 * day_for_month
        return montly_data
    elif time_step == "daily":
        cropped_data = data.reshape((365, 24))
        daily_data = cropped_data.sum(axis=1)
        return list(daily_data)
    return []


def get_inflow_data(scenario: int, time_step: str) -> List[float]:
    data = np.loadtxt("tests/functional/data_complex_case/hydro/mod.txt")
    data = data[:, scenario]
    if time_step == "monthly":
        montly_data = []
        day = 0
        for day_for_month in [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]:
            montly_data.append(np.sum(data[day : day + day_for_month]))
            day += day_for_month
        return montly_data
    elif time_step == "daily":
        return list(data)
    return []


def get_maxpower_data(time_step: str) -> List[float]:
    data = np.loadtxt("tests/functional/data_complex_case/hydro/maxpower.txt")
    data = data[:, 0]
    if time_step == "monthly":
        montly_data = []
        day = 0
        for day_for_month in [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]:
            montly_data.append(np.sum(data[day : day + day_for_month] * 24))
            day += day_for_month
        return montly_data
    elif time_step == "daily":
        return list(data * 24)
    return []
