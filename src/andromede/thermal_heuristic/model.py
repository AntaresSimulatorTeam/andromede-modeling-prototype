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

from math import ceil
from typing import List

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pandas as pd
import pytest

from andromede.expression import (
    ExpressionNode,
    PrinterVisitor,
    literal,
    param,
    var,
    visit,
)
from andromede.expression.indexing_structure import IndexingStructure
from andromede.libs.standard import (
    DEMAND_MODEL,
    NODE_BALANCE_MODEL,
    SPILLAGE_MODEL,
    UNSUPPLIED_ENERGY_MODEL,
)
from andromede.model import Model, float_parameter, float_variable, model
from andromede.model.constraint import Constraint
from andromede.model.parameter import float_parameter, int_parameter
from andromede.model.variable import ValueType, float_variable, int_variable
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
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP

CONSTANT = IndexingStructure(False, False)
TIME_AND_SCENARIO_FREE = IndexingStructure(True, True)
ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, True)
NON_ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, False)
CONSTANT_PER_SCENARIO = IndexingStructure(False, True)


def get_thermal_cluster_accurate_model(initial_model: Model) -> Model:
    THERMAL_CLUSTER_MODEL_LP = model(
        id=initial_model.id,
        parameters=[p for p in initial_model.parameters.values()],
        variables=[
            float_variable(
                v.name,
                lower_bound=v.lower_bound,
                upper_bound=v.upper_bound,
                structure=v.structure,
            )
            for v in initial_model.variables.values()
        ],
        ports=[p for p in initial_model.ports.values()],
        port_fields_definitions=[
            p for p in initial_model.port_fields_definitions.values()
        ],
        constraints=[c for c in initial_model.constraints.values()],
        objective_operational_contribution=initial_model.objective_operational_contribution,
    )

    return THERMAL_CLUSTER_MODEL_LP


def get_thermal_cluster_fast_model(initial_model: Model) -> Model:
    integer_variables = [
        v.name
        for v in initial_model.variables.values()
        if v.data_type == ValueType.INTEGER
    ]

    THERMAL_CLUSTER_MODEL_FAST = model(
        id=initial_model.id,
        parameters=[p for p in initial_model.parameters.values()],
        variables=[
            float_variable(
                v.name,
                lower_bound=(
                    v.lower_bound if v.data_type == ValueType.FLOAT else literal(0)
                ),
                upper_bound=(
                    v.upper_bound if v.data_type == ValueType.FLOAT else literal(0)
                ),
                structure=v.structure,
            )
            for v in initial_model.variables.values()
        ],
        ports=[p for p in initial_model.ports.values()],
        port_fields_definitions=[
            p for p in initial_model.port_fields_definitions.values()
        ],
        constraints=[
            c
            for c in initial_model.constraints.values()
            if not (variable_in_constraint(c, integer_variables))
        ],
        objective_operational_contribution=initial_model.objective_operational_contribution,
    )

    return THERMAL_CLUSTER_MODEL_FAST


def variable_in_constraint(c: Constraint, variables: List[str]) -> bool:
    res = False
    if variable_in_expression(c.lower_bound, variables):
        res = True
    elif variable_in_expression(c.expression, variables):
        res = True
    elif variable_in_expression(c.upper_bound, variables):
        res = True
    return res


def variable_in_expression(expr: ExpressionNode, variables: List[str]) -> bool:
    res = False
    str_expr = visit(expr, PrinterVisitor())
    for v in variables:
        if v in str_expr:
            res = True
    return res


def get_accurate_heuristic_model(initial_model: Model) -> Model:
    generation_variable = ["generation"]

    THERMAL_CLUSTER_MODEL_ACCURATE_HEURISTIC = model(
        id=initial_model.id,
        parameters=[p for p in initial_model.parameters.values()],
        variables=[
            v
            for v in initial_model.variables.values()
            if v.name not in generation_variable
        ],
        constraints=[
            c
            for c in initial_model.constraints.values()
            if not (variable_in_constraint(c, generation_variable))
        ],
        objective_operational_contribution=(var("nb_on")).sum().expec(),
    )
    return THERMAL_CLUSTER_MODEL_ACCURATE_HEURISTIC


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
