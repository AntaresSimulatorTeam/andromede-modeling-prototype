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
import io
from pathlib import Path

import pytest

from andromede.expression import literal, param, var
from andromede.expression.expression import port_field
from andromede.expression.parsing.parse_expression import AntaresParseException
from andromede.libs.standard import CONSTANT
from andromede.model import (
    Constraint,
    ModelPort,
    PortField,
    PortType,
    float_parameter,
    float_variable,
    model,
)
from andromede.model.model import PortFieldDefinition, PortFieldId
from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library


def test_library_parsing(data_dir: Path):
    lib_file = data_dir / "lib.yml"

    with lib_file.open() as f:
        input_lib = parse_yaml_library(f)
    assert input_lib.id == "basic"
    assert len(input_lib.models) == 5
    assert len(input_lib.port_types) == 1

    lib = resolve_library(input_lib)
    assert len(lib.models) == 5
    assert len(lib.port_types) == 1
    port_type = lib.port_types["flow"]
    assert port_type == PortType(id="flow", fields=[PortField(name="flow")])
    gen_model = lib.models["generator"]
    assert gen_model == model(
        id="generator",
        parameters=[
            float_parameter("cost", structure=CONSTANT),
            float_parameter("p_max", structure=CONSTANT),
        ],
        variables=[
            float_variable(
                "generation", lower_bound=literal(0), upper_bound=param("p_max")
            )
        ],
        ports=[ModelPort(port_type=port_type, port_name="injection_port")],
        port_fields_definitions=[
            PortFieldDefinition(
                port_field=PortFieldId(port_name="injection_port", field_name="flow"),
                definition=var("generation"),
            )
        ],
        objective_operational_contribution=(param("cost") * var("generation"))
        .sum()
        .expec(),
    )
    short_term_storage = lib.models["short-term-storage"]
    assert short_term_storage == model(
        id="short-term-storage",
        parameters=[
            float_parameter("efficiency", structure=CONSTANT),
            float_parameter("level_min", structure=CONSTANT),
            float_parameter("level_max", structure=CONSTANT),
            float_parameter("p_max_withdrawal", structure=CONSTANT),
            float_parameter("p_max_injection", structure=CONSTANT),
            float_parameter("inflows", structure=CONSTANT),
        ],
        variables=[
            float_variable(
                "injection",
                lower_bound=literal(0),
                upper_bound=param("p_max_injection"),
            ),
            float_variable(
                "withdrawal",
                lower_bound=literal(0),
                upper_bound=param("p_max_withdrawal"),
            ),
            float_variable(
                "level",
                lower_bound=param("level_min"),
                upper_bound=param("level_max"),
            ),
        ],
        ports=[ModelPort(port_type=port_type, port_name="injection_port")],
        port_fields_definitions=[
            PortFieldDefinition(
                port_field=PortFieldId(port_name="injection_port", field_name="flow"),
                definition=var("injection") - var("withdrawal"),
            )
        ],
        constraints=[
            Constraint(
                name="Level equation",
                expression=var("level")
                - var("level").shift(-literal(1))
                - param("efficiency") * var("injection")
                + var("withdrawal")
                == param("inflows"),
            )
        ],
    )


def test_library_error_parsing(data_dir: Path):
    lib_file = data_dir / "model_port_definition_ko.yml"

    with lib_file.open() as f:
        input_lib = parse_yaml_library(f)
    assert input_lib.id == "basic"
    with pytest.raises(
        AntaresParseException,
        match=r"An error occurred during parsing: ParseCancellationException",
    ):
        resolve_library(input_lib)


def test_library_port_model_ok_parsing(data_dir: Path):
    lib_file = data_dir / "model_port_definition_ok.yml"

    with lib_file.open() as f:
        input_lib = parse_yaml_library(f)
    assert input_lib.id == "basic"

    lib = resolve_library(input_lib)
    port_type = lib.port_types["flow"]
    assert port_type == PortType(id="flow", fields=[PortField(name="flow")])
    short_term_storage = lib.models["short-term-storage-2"]
    assert short_term_storage == model(
        id="short-term-storage-2",
        parameters=[
            float_parameter("p_max_withdrawal", structure=CONSTANT),
            float_parameter("p_max_injection", structure=CONSTANT),
        ],
        variables=[
            float_variable(
                "injection",
                lower_bound=literal(0),
                upper_bound=param("p_max_injection"),
            ),
            float_variable(
                "withdrawal",
                lower_bound=literal(0),
                upper_bound=param("p_max_withdrawal"),
            ),
        ],
        ports=[ModelPort(port_type=port_type, port_name="injection_port")],
        constraints=[
            Constraint(
                name="Level equation",
                expression=port_field("injection_port", "flow") == var("withdrawal"),
            )
        ],
    )
