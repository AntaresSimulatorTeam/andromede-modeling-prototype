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

    problem = create_complex_problem(
        {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
        number_hours,
        lp_relaxation=False,
        fast=False,
    )

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    parameters.SetDoubleParam(parameters.DUAL_TOLERANCE, 1e-7)
    parameters.SetDoubleParam(parameters.PRIMAL_TOLERANCE, 1e-7)

    status = problem.solver.Solve(parameters)

    assert status == problem.solver.OPTIMAL

    output = OutputValues(problem)
    assert sum(output.component("G1").var("generation").value[0]) == pytest.approx(
        60670
    )
    assert sum(output.component("G1").var("nb_on").value[0]) == pytest.approx(168)

    assert sum(output.component("G2").var("generation").value[0]) == pytest.approx(6650)
    assert sum(output.component("G2").var("nb_on").value[0]) == pytest.approx(83)

    assert sum(output.component("G3").var("generation").value[0]) == pytest.approx(
        60154
    )
    assert sum(output.component("G3").var("nb_on").value[0]) == pytest.approx(315)

    assert sum(output.component("S").var("spillage").value[0]) == pytest.approx(1427)
    assert sum(
        output.component("U").var("unsupplied_energy").value[0]
    ) == pytest.approx(6529)

    assert problem.solver.Objective().Value() == pytest.approx(78933841)


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    parameters.SetDoubleParam(parameters.DUAL_TOLERANCE, 1e-7)
    parameters.SetDoubleParam(parameters.PRIMAL_TOLERANCE, 1e-7)

    # First optimization
    problem_optimization_1 = create_complex_problem(
        {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
        number_hours,
        lp_relaxation=True,
        fast=False,
    )
    status = problem_optimization_1.solver.Solve(parameters)

    assert status == problem_optimization_1.solver.OPTIMAL

    # Get number of on units and round it to integer
    output_1 = OutputValues(problem_optimization_1)
    nb_on_min = {}
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
            {g: n_guide}, number_hours, thermal_cluster=g
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
        nb_on_min, number_hours, lp_relaxation=True, fast=False
    )
    status = problem_optimization_2.solver.Solve(parameters)

    assert status == problem_optimization_2.solver.OPTIMAL
    assert problem_optimization_2.solver.Objective().Value() == 78996726

    output = OutputValues(problem_optimization_2)
    assert sum(output.component("G1").var("generation").value[0]) == pytest.approx(
        60625
    )
    assert sum(output.component("G1").var("nb_on").value[0]) == pytest.approx(168)

    assert sum(output.component("G2").var("generation").value[0]) == pytest.approx(5730)
    assert sum(output.component("G2").var("nb_on").value[0]) == pytest.approx(68)

    assert sum(output.component("G3").var("generation").value[0]) == pytest.approx(
        61119
    )
    assert sum(output.component("G3").var("nb_on").value[0]) == pytest.approx(320)

    assert sum(output.component("S").var("spillage").value[0]) == pytest.approx(1427)
    assert sum(
        output.component("U").var("unsupplied_energy").value[0]
    ) == pytest.approx(6529)


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

    # First optimization
    problem_optimization_1 = create_complex_problem(
        ConstantData(0), number_hours, lp_relaxation=True, fast=True
    )
    status = problem_optimization_1.solver.Solve()

    assert status == problem_optimization_1.solver.OPTIMAL

    # Get number of on units
    output_1 = OutputValues(problem_optimization_1)

    # Solve heuristic problem
    mingen_heuristic = create_problem_fast_heuristic(
        output_1.component("G").var("generation").value,
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
    problem_optimization_2 = create_complex_problem(
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


def create_complex_problem(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    lp_relaxation: bool,
    fast: bool,
) -> OptimizationProblem:

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
        np.repeat([1100, 1100, 0, 1100, 1100, 1100, 1100], 24),
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

    demand_data = pd.DataFrame(
        [
            672,
            599,
            568,
            548,
            553,
            592,
            672,
            798,
            912,
            985,
            1039,
            1049,
            1030,
            1018,
            1000,
            1001,
            1054,
            1111,
            1071,
            1019,
            987,
            966,
            922,
            831,
            802,
            790,
            810,
            804,
            800,
            826,
            895,
            998,
            1072,
            1103,
            1096,
            1083,
            1057,
            1050,
            1047,
            1036,
            1069,
            1115,
            1092,
            1070,
            1063,
            1051,
            983,
            892,
            749,
            703,
            700,
            700,
            745,
            860,
            1052,
            1229,
            1337,
            1353,
            1323,
            1312,
            1308,
            1361,
            1375,
            1403,
            1452,
            1541,
            1559,
            1528,
            1446,
            1335,
            1205,
            1050,
            920,
            824,
            767,
            744,
            759,
            857,
            1033,
            1169,
            1243,
            1244,
            1232,
            1215,
            1199,
            1253,
            1271,
            1301,
            1361,
            1469,
            1505,
            1471,
            1383,
            1271,
            1172,
            1028,
            922,
            843,
            813,
            809,
            837,
            936,
            1118,
            1278,
            1382,
            1410,
            1400,
            1385,
            1372,
            1425,
            1444,
            1454,
            1503,
            1593,
            1615,
            1584,
            1501,
            1378,
            1250,
            1061,
            852,
            745,
            682,
            631,
            617,
            676,
            830,
            1004,
            1128,
            1163,
            1145,
            1109,
            1083,
            1127,
            1136,
            1157,
            1215,
            1302,
            1285,
            1232,
            1169,
            1112,
            1030,
            950,
            1038,
            893,
            761,
            718,
            718,
            761,
            850,
            1035,
            1204,
            1275,
            1228,
            1186,
            1156,
            1206,
            1234,
            1259,
            1354,
            1469,
            1484,
            1460,
            1404,
            1339,
            1248,
            1085,
        ],
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    demand_data[0] = demand_data[0] - 300

    demand_time_scenario_series = TimeScenarioSeriesData(demand_data)
    database.add_data("D", "demand", demand_time_scenario_series)

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


def create_problem_accurate_heuristic(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    thermal_cluster: str,
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
            np.repeat([1100, 1100, 0, 1100, 1100, 1100, 1100], 24),
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
    )

    return problem


def create_problem_fast_heuristic(
    lower_bound: List[List[float]], number_hours: int
) -> pd.DataFrame:

    delta = 10
    cost = pd.DataFrame(
        np.zeros((delta + 1, 1)),
        index=[i for i in range(delta + 1)],
        columns=[0],
    )
    n = np.zeros((number_hours, delta + 1, 1))
    for h in range(delta + 1):
        cost_h = 0
        t = 0
        while t < number_hours:
            if t < h:
                n_k = max(
                    [convert_to_integer(lower_bound[0][j] / 1000) for j in range(h)]
                    + [
                        convert_to_integer(lower_bound[0][j] / 1000)
                        for j in range(number_hours - delta + h, number_hours)
                    ]
                )
                cost_h += (h - 1) * n_k
                n[0:h, h, 0] = n_k
                t = h
            else:
                k = floor((t - h) / delta) * delta + h
                n_k = max(
                    [
                        convert_to_integer(lower_bound[0][j] / 1000)
                        for j in range(k, min(number_hours, k + delta))
                    ]
                )
                cost_h += delta * n_k
                n[k : min(number_hours, k + delta), h, 0] = n_k
                if t + delta < number_hours:
                    t += delta
                else:
                    t = number_hours
        cost.iloc[h, 0] = cost_h

    database = DataBase()

    database.add_data("G", "cost", TimeScenarioSeriesData(cost))

    time_block = TimeBlock(1, [i for i in range(10)])
    scenarios = 1

    gen = create_component(model=BLOCK_MODEL_FAST_HEURISTIC, id="G")

    network = Network("test")
    network.add_component(gen)

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=BlockBorderManagement.CYCLE,
    )

    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL

    output_heuristic = OutputValues(problem)
    h = np.argmax(output_heuristic.component("G").var("t_ajust").value[0])
    mingen_heuristic = pd.DataFrame(
        n[:, h, :] * 700,
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return mingen_heuristic


def convert_to_integer(x: float) -> int:
    return ceil(round(x, 12))
