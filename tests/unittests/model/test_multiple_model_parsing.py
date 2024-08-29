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
import re
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


@pytest.fixture(scope="session")
def lib_dir(data_dir: Path) -> Path:
    return data_dir / "lib_for_resolving_test"


# in following tests "lib_A -> lib_B" means lib_A must be resolved before lib_B


def test_simple_dependency_tree(lib_dir: Path) -> None:
    """basic_lib
        |     |
        V     V
    demand   production
    """
    lib_files = [
        lib_dir / "basic_lib.yml",
        lib_dir / "demand.yml",
        lib_dir / "production.yml",
    ]

    input_libs = []
    for lib_file in lib_files:
        with lib_file.open() as f:
            input_libs.append(parse_yaml_library(f))

    lib = resolve_library(input_libs)
    assert len(lib.models) == 3
    assert len(lib.port_types) == 1

    # changing order in lib_files
    lib_files = [
        lib_dir / "demand.yml",
        lib_dir / "production.yml",
        lib_dir / "basic_lib.yml",
    ]

    input_libs = []
    for lib_file in lib_files:
        with lib_file.open() as f:
            input_libs.append(parse_yaml_library(f))

    lib = resolve_library(input_libs)
    assert len(lib.models) == 3
    assert len(lib.port_types) == 1


def test_multiple_dependencies_tree(lib_dir: Path) -> None:
    """basic_lib   CO2_port
        |     |       |
        V     V       V
    demand   production_with_CO2
    """
    lib_files = [
        lib_dir / "basic_lib.yml",
        lib_dir / "CO2_port.yml",
        lib_dir / "demand.yml",
        lib_dir / "production_with_CO2.yml",
    ]

    input_libs = []
    for lib_file in lib_files:
        with lib_file.open() as f:
            input_libs.append(parse_yaml_library(f))

    lib = resolve_library(input_libs)
    assert len(lib.models) == 3
    assert len(lib.port_types) == 2


def test_looping_dependency(lib_dir: Path) -> None:
    """looping_lib_1 -> looping_lib_2
    <-
    """
    lib_files = [
        lib_dir / "looping_lib_1.yml",
        lib_dir / "looping_lib_2.yml",
    ]

    input_libs = []
    for lib_file in lib_files:
        with lib_file.open() as f:
            input_libs.append(parse_yaml_library(f))

    with pytest.raises(Exception, match=r"Circular import in yaml libraries"):
        lib = resolve_library(input_libs)


def test_model_redefinition(lib_dir: Path) -> None:
    """basic_lib   CO2_port
            |     |      |
            V     V      V
    production   production_with_CO2
    """
    lib_files = [
        lib_dir / "basic_lib.yml",
        lib_dir / "CO2_port.yml",
        lib_dir / "production.yml",
        lib_dir / "production_with_CO2.yml",
    ]

    input_libs = []
    for lib_file in lib_files:
        with lib_file.open() as f:
            input_libs.append(parse_yaml_library(f))

    with pytest.raises(
        Exception, match=re.escape("Model(s) : {'generator'} is(are) defined twice")
    ):
        lib = resolve_library(input_libs)


def test_port_redefinition(lib_dir: Path) -> None:
    """basic_lib -> port_redefinition"""
    lib_files = [
        lib_dir / "basic_lib.yml",
        lib_dir / "port_redefinition.yml",
    ]

    input_libs = []
    for lib_file in lib_files:
        with lib_file.open() as f:
            input_libs.append(parse_yaml_library(f))

    with pytest.raises(
        Exception, match=re.escape("Port(s) : {'flow'} is(are) defined twice")
    ):
        lib = resolve_library(input_libs)
