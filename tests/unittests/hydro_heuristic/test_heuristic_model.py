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

import pytest

from andromede.expression import literal, param, var
from andromede.expression.indexing_structure import IndexingStructure
from andromede.hydro_heuristic.heuristic_model import HeuristicHydroModelBuilder, Model
from andromede.model import float_parameter, float_variable, model
from andromede.model.constraint import Constraint
from andromede.model.parameter import float_parameter
from andromede.model.variable import float_variable

CONSTANT = IndexingStructure(False, False)
TIME_AND_SCENARIO_FREE = IndexingStructure(True, True)
NON_ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, False)

MINIMAL_HYDRO_MODEL = model(
    id="minimal",
    parameters=[
        float_parameter("max_generating", CONSTANT),
        float_parameter("capacity", CONSTANT),
        float_parameter("initial_level", CONSTANT),
        float_parameter(
            "max_epsilon", NON_ANTICIPATIVE_TIME_VARYING
        ),  # not really a parameter, it is just to implement correctly one constraint
        float_parameter("lower_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("upper_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
    ],
    variables=[
        float_variable(
            "generating",
            lower_bound=literal(0),
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
            + var("epsilon"),
        ),
        Constraint(
            "Initial level",
            var("level").eval(literal(0))
            == param("initial_level")
            - var("generating").eval(literal(0))
            - var("overflow").eval(literal(0)),
        ),
    ],
)


def test_empty_model() -> None:
    model_builder = HeuristicHydroModelBuilder(Model(id="empty"), "monthly")

    with pytest.raises(ValueError):
        heuristic_model = model_builder.get_model()


def test_minimal_model() -> None:
    model_builder = HeuristicHydroModelBuilder(MINIMAL_HYDRO_MODEL, "monthly")

    heuristic_model = model_builder.get_model()

    assert len(heuristic_model.constraints) == 11
    assert len(heuristic_model.variables) == 10
    assert len(heuristic_model.parameters) == 8
