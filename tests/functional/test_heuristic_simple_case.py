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
from typing import List
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
        int_parameter("nb_failures", TIME_AND_SCENARIO_FREE),
    ],
    variables=[
        float_variable(
            "generation",
            lower_bound=literal(0),
            upper_bound=param("nb_units_max") * param("p_max"),
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
        int_parameter("nb_failures", TIME_AND_SCENARIO_FREE),
    ],
    variables=[
        float_variable(
            "generation",
            lower_bound=literal(0),
            upper_bound=param("nb_units_max") * param("p_max"),
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
    ],
    variables=[
        float_variable(
            "generation",
            lower_bound=param("mingen"),
            upper_bound=param("nb_units_max") * param("p_max"),
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
    constraints=[],
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

Q = 16  # number of blocks
R = 8  # length of the last block
Delta = 10
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
        for h in range(Delta)
    ]
    + [
        int_parameter(f"alpha_ajust_{h}", NON_ANTICIPATIVE_TIME_VARYING)
        for h in range(Delta)
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
        for h in range(Delta)
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
        for h in range(Delta)
    ]
    + [
        Constraint(
            f"Definition of n ajust for {h}",
            var(f"n_ajust")
            >= param("n_guide") * param(f"alpha_ajust_{h}")
            - param("n_max") * (literal(1) - var(f"t_ajust_{h}")),
        )
        for h in range(Delta)
    ]
    + [
        Constraint(
            f"Definition of n with relation to block {k} for {h}",
            var(f"n")
            >= param(f"alpha_{k}_{h}") * var(f"n_block_{k}")
            - param("n_max") * (literal(1) - var(f"t_ajust_{h}")),
        )
        for k in range(Q)
        for h in range(Delta)
    ]
    + [
        Constraint(
            f"Definition of n with relation to ajust for {h}",
            var(f"n")
            >= param(f"alpha_ajust_{h}") * var(f"n_ajust")
            - param("n_max") * (literal(1) - var(f"t_ajust_{h}")),
        )
        for h in range(Delta)
    ]
    + [
        Constraint(
            "Choose one t ajust",
            literal(0) + sum([var(f"t_ajust_{h}") for h in range(Delta)]) == literal(1),
        )
    ],
    objective_operational_contribution=(var("n")).sum().expec(),
)


def test_milp_version() -> None:
    """
    Model on 168 time steps with one thermal generation and one demand on a single node.
        - Demand is constant to 2000 MW except for the 13th hour for which it is 2050 MW
        - Thermal generation is characterized with:
            - P_min = 700 MW
            - P_max = 1000 MW
            - Min up time = 3
            - Min down time = 10
            - Generation cost = 50€ / MWh
            - Startup cost = 50
            - Fixed cost = 1 /h
            - Number of unit = 3
        - Unsupplied energy = 1000 €/MWh
        - Spillage = 0 €/MWh

    The optimal solution consists in turning on two thermal plants at the begining, turning on a third thermal plant at the 13th hour and turning off the first thermal plant at the 14th hour, the other two thermal plants stay on for the rest of the week producing 1000MW each. At the 13th hour, the production is [700,700,700] to satisfy Pmin constraints.

    The optimal cost is then :
          50 x 2 x 1000 x 167 (prod step 1-12 and 14-168)
        + 50 x 3 x 700 (prod step 13)
        + 50 (start up step 13)
        + 2 x 1 x 167 (fixed cost step 1-12 and 14-168)
        + 3 x 1 (fixed cost step 13)
        = 16 805 387
    """
    number_hours = 168

    problem = create_simple_problem(
        ConstantData(0), number_hours, lp_relaxation=False, fast=False
    )
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 16805387

    output = OutputValues(problem)
    assert output.component("G").var("generation").value == [
        [
            pytest.approx(2000.0) if time_step != 12 else pytest.approx(2100.0)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("G").var("nb_on").value == [
        [
            pytest.approx(2.0) if time_step != 12 else pytest.approx(3.0)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("G").var("nb_start").value == [
        [
            pytest.approx(0.0) if time_step != 12 else pytest.approx(1.0)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("G").var("nb_stop").value == [
        [
            pytest.approx(0.0) if time_step != 13 else pytest.approx(1.0)
            for time_step in range(number_hours)
        ]
    ]

    assert output.component("S").var("spillage").value == [
        [
            pytest.approx(0.0) if time_step != 12 else pytest.approx(50.0)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("U").var("unsupplied_energy").value == [
        [pytest.approx(0.0)] * number_hours
    ]


def test_lp_version() -> None:
    """
    Model on 168 time steps with one thermal generation and one demand on a single node.
        - Demand is constant to 2000 MW except for the 13th hour for which it is 2050 MW
        - Thermal generation is characterized with:
            - P_min = 700 MW
            - P_max = 1000 MW
            - Min up time = 3
            - Min down time = 10
            - Generation cost = 50€ / MWh
            - Startup cost = 50
            - Fixed cost = 1 /h
            - Number of unit = 3
        - Unsupplied energy = 1000 €/MWh
        - Spillage = 0 €/MWh

    The optimal solution consists in producing exactly the demand at each hour. The number of on units is equal to the production divided by P_max.

    The optimal cost is then :
          50 x 2000 x 167 (prod step 1-12 and 14-168)
        + 50 x 2050 (prod step 13)
        + 2 x 1 x 168 (fixed cost step 1-12 and 14-168)
        + 2050/1000 x 1 (fixed cost step 13)
        + 0,05 x 50 (start up cost step 13)
        = 16 802 840,55
    """
    number_hours = 168
    problem = create_simple_problem(
        ConstantData(0), number_hours, lp_relaxation=True, fast=False
    )
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == pytest.approx(16802840.55)

    output = OutputValues(problem)
    assert output.component("G").var("generation").value == [
        [
            pytest.approx(2000.0) if time_step != 12 else 2050.0
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("G").var("nb_on").value == [
        [
            pytest.approx(2) if time_step != 12 else pytest.approx(2050 / 1000)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("G").var("nb_start").value == [
        [
            pytest.approx(0.0) if time_step != 12 else pytest.approx(0.05)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("G").var("nb_stop").value == [
        [
            pytest.approx(0.0) if time_step != 13 else pytest.approx(0.05)
            for time_step in range(number_hours)
        ]
    ]

    assert output.component("S").var("spillage").value == [
        [pytest.approx(0.0)] * number_hours
    ]
    assert output.component("U").var("unsupplied_energy").value == [
        [pytest.approx(0.0)] * number_hours
    ]


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168

    # First optimization
    problem_optimization_1 = create_simple_problem(
        ConstantData(0), number_hours, lp_relaxation=True, fast=False
    )
    status = problem_optimization_1.solver.Solve()

    assert status == problem_optimization_1.solver.OPTIMAL

    # Get number of on units and round it to integer
    output_1 = OutputValues(problem_optimization_1)
    nb_on_1 = pd.DataFrame(
        np.transpose(
            np.ceil(np.round(np.array(output_1.component("G").var("nb_on").value), 12))
        ),
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    n_guide = TimeScenarioSeriesData(nb_on_1)
    for time_step in range(number_hours):
        assert nb_on_1.iloc[time_step, 0] == 2 if time_step != 12 else 3

    # Solve heuristic problem
    problem_accurate_heuristic = create_problem_accurate_heuristic(
        n_guide, number_hours
    )
    status = problem_accurate_heuristic.solver.Solve()

    assert status == problem_accurate_heuristic.solver.OPTIMAL

    output_heuristic = OutputValues(problem_accurate_heuristic)
    nb_on_heuristic = pd.DataFrame(
        np.transpose(
            np.ceil(np.array(output_heuristic.component("G").var("nb_on").value))
        ),
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    nb_on_min = TimeScenarioSeriesData(nb_on_heuristic)

    for time_step in range(number_hours):
        assert nb_on_heuristic.iloc[time_step, 0] == 2 if time_step != 12 else 3

    # Second optimization with lower bound modified
    problem_optimization_2 = create_simple_problem(
        nb_on_min, number_hours, lp_relaxation=True, fast=False
    )
    status = problem_optimization_2.solver.Solve()

    assert status == problem_optimization_2.solver.OPTIMAL
    assert problem_optimization_2.solver.Objective().Value() == 16805387

    output = OutputValues(problem_optimization_2)
    assert output.component("G").var("generation").value == [
        [
            pytest.approx(2000.0) if time_step != 12 else pytest.approx(2100.0)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("G").var("nb_on").value == [
        [
            pytest.approx(2.0) if time_step != 12 else pytest.approx(3.0)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("G").var("nb_start").value == [
        [
            pytest.approx(0.0) if time_step != 12 else pytest.approx(1.0)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("G").var("nb_stop").value == [
        [
            pytest.approx(0.0) if time_step != 13 else pytest.approx(1.0)
            for time_step in range(number_hours)
        ]
    ]

    assert output.component("S").var("spillage").value == [
        [
            pytest.approx(0.0) if time_step != 12 else pytest.approx(50.0)
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("U").var("unsupplied_energy").value == [
        [pytest.approx(0.0)] * number_hours
    ]


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    Model on 168 time steps with one thermal generation and one demand on a single node.
        - Demand is constant to 2000 MW except for the 13th hour for which it is 2050 MW
        - Thermal generation is characterized with:
            - P_min = 700 MW
            - P_max = 1000 MW
            - Min up time = 3
            - Min down time = 10
            - Generation cost = 50€ / MWh
            - Startup cost = 50
            - Fixed cost = 1 /h
            - Number of unit = 3
        - Unsupplied energy = 1000 €/MWh
        - Spillage = 0 €/MWh

    The optimal solution consists in having 3 units turned on between time steps 10 and 19 with production equal to 2100 to respect pmin and 2 the rest of the time.

    The optimal cost is then :
          50 x 2000 x 158 (prod step 1-9 and 20-168)
        + 50 x 2100 x 10 (prod step 10-19)
        = 16 850 000
    """

    number_hours = 168
    pmax = 1000

    # First optimization
    problem_optimization_1 = create_simple_problem(
        ConstantData(0), number_hours, lp_relaxation=True, fast=True
    )
    status = problem_optimization_1.solver.Solve()

    assert status == problem_optimization_1.solver.OPTIMAL

    # Get number of on units
    output_1 = OutputValues(problem_optimization_1)

    nb_on_1 = pd.DataFrame(
        np.transpose(
            np.ceil(
                np.round(
                    np.array(
                        output_1.component("G")
                        .var("generation")
                        .value[0]  # type:ignore
                    )
                    / pmax,
                    12,
                )
            )
        ),
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    n_guide = TimeScenarioSeriesData(nb_on_1)

    # Solve heuristic problem
    mingen_heuristic = create_problem_fast_heuristic(
        n_guide,
        number_hours,
    )

    mingen = TimeScenarioSeriesData(mingen_heuristic)

    for time_step in range(number_hours):
        assert (
            mingen_heuristic.iloc[time_step, 0] == 3 * 700
            if time_step in [t for t in range(10, 20)]
            else 2 * 700
        )

    # Second optimization with lower bound modified
    problem_optimization_2 = create_simple_problem(
        mingen, number_hours, lp_relaxation=True, fast=True
    )
    status = problem_optimization_2.solver.Solve()

    assert status == problem_optimization_2.solver.OPTIMAL
    assert problem_optimization_2.solver.Objective().Value() == pytest.approx(16850000)

    output = OutputValues(problem_optimization_2)
    assert output.component("G").var("generation").value == [
        [
            (
                pytest.approx(2100.0)
                if time_step in [t for t in range(10, 20)]
                else pytest.approx(2000.0)
            )
            for time_step in range(number_hours)
        ]
    ]

    assert output.component("S").var("spillage").value == [
        [
            (
                pytest.approx(100.0)
                if time_step in [t for t in range(10, 20) if t != 12]
                else (pytest.approx(0.0) if time_step != 12 else pytest.approx(50.0))
            )
            for time_step in range(number_hours)
        ]
    ]
    assert output.component("U").var("unsupplied_energy").value == [
        [pytest.approx(0.0)] * number_hours
    ]


def create_simple_problem(
    lower_bound: AbstractDataStructure,
    number_hours: int,
    lp_relaxation: bool,
    fast: bool,
) -> OptimizationProblem:

    database = DataBase()

    database.add_data("G", "p_max", ConstantData(1000))
    database.add_data("G", "p_min", ConstantData(700))
    database.add_data("G", "cost", ConstantData(50))
    database.add_data("G", "startup_cost", ConstantData(50))
    database.add_data("G", "fixed_cost", ConstantData(1))
    database.add_data("G", "d_min_up", ConstantData(3))
    database.add_data("G", "d_min_down", ConstantData(10))
    database.add_data("G", "nb_units_min", lower_bound)
    database.add_data("G", "nb_units_max", ConstantData(3))
    database.add_data("G", "nb_failures", ConstantData(0))
    database.add_data("G", "mingen", lower_bound)

    database.add_data("U", "cost", ConstantData(1000))
    database.add_data("S", "cost", ConstantData(0))

    demand_data = pd.DataFrame(
        [[2000.0]] * number_hours,
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    demand_data.iloc[12, 0] = 2050.0

    demand_time_scenario_series = TimeScenarioSeriesData(demand_data)
    database.add_data("D", "demand", demand_time_scenario_series)

    time_block = TimeBlock(1, [i for i in range(number_hours)])
    scenarios = 1

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    demand = create_component(model=DEMAND_MODEL, id="D")

    if fast:
        gen = create_component(model=THERMAL_CLUSTER_MODEL_FAST, id="G")
    elif lp_relaxation:
        gen = create_component(model=THERMAL_CLUSTER_MODEL_LP, id="G")
    else:
        gen = create_component(model=THERMAL_CLUSTER_MODEL_MILP, id="G")

    spillage = create_component(model=SPILLAGE_MODEL, id="S")

    unsupplied_energy = create_component(model=UNSUPPLIED_ENERGY_MODEL, id="U")

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen)
    network.add_component(spillage)
    network.add_component(unsupplied_energy)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))
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
    )

    return problem


def create_problem_accurate_heuristic(
    lower_bound: AbstractDataStructure, number_hours: int
) -> OptimizationProblem:

    database = DataBase()

    database.add_data("G", "d_min_up", ConstantData(3))
    database.add_data("G", "d_min_down", ConstantData(10))
    database.add_data("G", "nb_units_min", lower_bound)
    database.add_data("G", "nb_units_max", ConstantData(3))

    time_block = TimeBlock(1, [i for i in range(number_hours)])
    scenarios = 1

    gen = create_component(model=THERMAL_CLUSTER_MODEL_ACCURATE_HEURISTIC, id="G")

    network = Network("test")
    network.add_component(gen)

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=BlockBorderManagement.CYCLE,
    )

    return problem


def create_problem_fast_heuristic(
    lower_bound: AbstractDataStructure, number_hours: int
) -> pd.DataFrame:

    delta = 10
    pmin = 700
    pdispo = np.array(3000)
    nmax = 3

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
        for k in range(Q):
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

    block = create_component(model=BLOCK_MODEL_FAST_HEURISTIC, id="B")

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
    problem.solver.EnableOutput()

    status = problem.solver.Solve(parameters)

    assert status == problem.solver.OPTIMAL

    output_heuristic = OutputValues(problem)
    n_heuristic = np.array(
        output_heuristic.component("B").var("n").value[0]  # type:ignore
    )
    mingen_heuristic = pd.DataFrame(
        np.minimum(n_heuristic * pmin, pdispo),
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return mingen_heuristic


def convert_to_integer(x: float) -> int:
    return ceil(round(x, 12))
