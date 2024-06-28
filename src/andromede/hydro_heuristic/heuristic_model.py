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

from typing import List

from andromede.expression import ExpressionNode, literal, param, var
from andromede.expression.indexing_structure import IndexingStructure
from andromede.model import Model, float_parameter, float_variable, model
from andromede.model.constraint import Constraint
from andromede.model.parameter import Parameter, float_parameter
from andromede.model.variable import Variable, float_variable

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
