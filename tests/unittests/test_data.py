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
from pathlib import Path
from typing import Union

import pandas as pd
import pytest

from andromede.expression.expression_efficient import param
from andromede.expression.indexing_structure import IndexingStructure
from andromede.expression.linear_expression_efficient import var
from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    CONSTANT,
    DEMAND_MODEL,
    GENERATOR_MODEL,
    NODE_BALANCE_MODEL,
    NON_ANTICIPATIVE_TIME_VARYING,
)
from andromede.model import (
    Constraint,
    Model,
    ModelPort,
    float_parameter,
    float_variable,
    model,
)
from andromede.model.model import PortFieldDefinition, PortFieldId
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    ScenarioIndex,
    ScenarioSeriesData,
    TimeIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
    create_component,
)
from andromede.study.data import load_ts_from_txt


@pytest.fixture
def mock_network() -> Network:
    node = Node(model=NODE_BALANCE_MODEL, id="1")
    demand = create_component(model=DEMAND_MODEL, id="D")

    gen = create_component(model=GENERATOR_MODEL, id="G")

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))

    return network


@pytest.fixture
def mock_generator_with_fixed_scenario_time_varying_param() -> Model:
    fixed_scenario_time_varying_param_generator = model(
        id="GEN",
        parameters=[
            float_parameter("p_max", CONSTANT),
            float_parameter("cost", NON_ANTICIPATIVE_TIME_VARYING),
        ],
        variables=[float_variable("generation")],
        ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
        port_fields_definitions=[
            PortFieldDefinition(
                port_field=PortFieldId("balance_port", "flow"),
                definition=var("generation"),
            )
        ],
        constraints=[
            Constraint(
                name="Max generation", expression=var("generation") <= param("p_max")
            )
        ],
        objective_operational_contribution=(param("cost") * var("generation"))
        .sum()
        .expec(),
    )
    return fixed_scenario_time_varying_param_generator


@pytest.fixture
def mock_generator_with_scenario_varying_fixed_time_param() -> Model:
    scenario_varying_fixed_time_generator = model(
        id="GEN",
        parameters=[
            float_parameter("p_max", CONSTANT),
            float_parameter("cost", IndexingStructure(False, True)),
        ],
        variables=[float_variable("generation")],
        ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
        port_fields_definitions=[
            PortFieldDefinition(
                port_field=PortFieldId("balance_port", "flow"),
                definition=var("generation"),
            )
        ],
        constraints=[
            Constraint(
                name="Max generation", expression=var("generation") <= param("p_max")
            )
        ],
        objective_operational_contribution=(param("cost") * var("generation"))
        .sum()
        .expec(),
    )
    return scenario_varying_fixed_time_generator


@pytest.fixture
def demand_data() -> TimeScenarioSeriesData:
    demand_data = pd.DataFrame(
        [
            [100],
            [50],
        ],
        index=[0, 1],
        columns=[0],
    )

    return TimeScenarioSeriesData(demand_data)


def test_requirements_consistency_demand_model_fix_ok(
    mock_network: Network, demand_data: TimeScenarioSeriesData
) -> None:
    # Given
    # database data for "demand" defined as Time varying
    # and model "D" DEMAND_MODEL is TIME_AND_SCENARIO_FREE
    database = DataBase()
    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(30))

    database.add_data("D", "demand", demand_data)

    # When
    # No ValueError should be raised
    database.requirements_consistency(mock_network)


def test_requirements_consistency_generator_model_ok(mock_network: Network) -> None:
    # Given
    # database data for "demand" defined as CONSTANT
    # model "D" DEMAND_MODEL is TIME_AND_SCENARIO_FREE
    database = DataBase()
    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(30))
    database.add_data("D", "demand", ConstantData(30))

    # When
    database.requirements_consistency(mock_network)


def test_consistency_generation_time_free_for_constant_model_raises_exception(
    mock_network: Network, demand_data: TimeScenarioSeriesData
) -> None:
    # Given
    # database data for "p_max" defined as time varying
    # but model "GENERATOR_MODEL" is CONSTANT

    database = DataBase()

    database.add_data("G", "cost", ConstantData(30))

    database.add_data("D", "demand", demand_data)
    database.add_data("G", "p_max", demand_data)

    # When
    with pytest.raises(ValueError, match="Data inconsistency"):
        database.requirements_consistency(mock_network)


def test_requirements_consistency_demand_model_time_varying_ok(
    mock_network: Network, demand_data: TimeScenarioSeriesData
) -> None:
    # Given
    # database data for "demand" defined as constant
    # and model "D" DEMAND_MODEL is TIME_AND_SCENARIO_FREE
    database = DataBase()
    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(30))
    database.add_data("D", "demand", demand_data)

    # When
    # No ValueError should be raised
    database.requirements_consistency(mock_network)


def test_requirements_consistency_time_varying_parameter_with_correct_data_passes(
    mock_generator_with_fixed_scenario_time_varying_param: Model,
) -> None:
    # Given
    # Model for test with parameter NON_ANTICIPATIVE_TIME_VARYING

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    gen = create_component(
        model=mock_generator_with_fixed_scenario_time_varying_param, id="G"
    )

    cost_data = TimeSeriesData({TimeIndex(0): 100, TimeIndex(1): 50})

    database = DataBase()
    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", cost_data)
    network = Network("test")
    network.add_node(node)
    network.add_component(gen)
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))

    # No ValueError should be raised
    database.requirements_consistency(network)


@pytest.mark.parametrize(
    "cost_data",
    [
        (ScenarioSeriesData({ScenarioIndex(0): 100, ScenarioIndex(1): 50})),
        (
            TimeScenarioSeriesData(
                pd.DataFrame(
                    [
                        [100, 500],
                        [500, 540],
                    ],
                    index=[0, 1],
                    columns=[0, 1],
                )
            )
        ),
    ],
)
def test_requirements_consistency_time_varying_parameter_with_scenario_varying_data_raises_exception(
    mock_generator_with_fixed_scenario_time_varying_param: Model,
    cost_data: Union[ScenarioSeriesData, TimeScenarioSeriesData],
) -> None:
    # Given
    # Model for test with parameter NON_ANTICIPATIVE_TIME_VARYING

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    gen = create_component(
        model=mock_generator_with_fixed_scenario_time_varying_param,
        id="G",
    )

    database = DataBase()
    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", cost_data)
    network = Network("test")
    network.add_node(node)
    network.add_component(gen)
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))

    # When
    # ValueError should be raised
    with pytest.raises(ValueError, match="Data inconsistency"):
        database.requirements_consistency(network)


@pytest.mark.parametrize(
    "cost_data",
    [
        (TimeSeriesData({TimeIndex(0): 100, TimeIndex(1): 50})),
        (
            TimeScenarioSeriesData(
                pd.DataFrame({(0, 0): [100, 500], (0, 1): [50, 540]}, index=[0, 1])
            )
        ),
    ],
)
def test_requirements_consistency_scenario_varying_parameter_with_time_varying_data_raises_exception(
    mock_generator_with_scenario_varying_fixed_time_param: Model,
    cost_data: Union[TimeSeriesData, TimeScenarioSeriesData],
) -> None:
    # Given
    # Model for test with parameter indexed by scenario only

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    gen = create_component(
        model=mock_generator_with_scenario_varying_fixed_time_param, id="G"
    )

    database = DataBase()
    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", cost_data)
    network = Network("test")
    network.add_node(node)
    network.add_component(gen)
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))

    # ValueError should be raised
    with pytest.raises(ValueError, match="Data inconsistency"):
        database.requirements_consistency(network)


def test_requirements_consistency_scenario_varying_parameter_with_correct_data_passes(
    mock_generator_with_scenario_varying_fixed_time_param: Model,
) -> None:
    # Given
    # Model for test with parameter indexed by scenario only

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    gen = create_component(
        model=mock_generator_with_scenario_varying_fixed_time_param, id="G"
    )

    cost_data = ScenarioSeriesData({ScenarioIndex(0): 100, ScenarioIndex(1): 50})

    database = DataBase()
    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", cost_data)
    network = Network("test")
    network.add_node(node)
    network.add_component(gen)
    network.add_component(gen)

    # No ValueError should be raised
    database.requirements_consistency(network)


def test_load_data_from_txt(data_dir: Path):
    txt_file = "gen-costs"

    gen_costs = load_ts_from_txt(txt_file, data_dir)
    expected_timeseries = pd.DataFrame(
        [[100, 200], [50, 100]], index=[0, 1], columns=[0, 1]
    )
    assert gen_costs.equals(expected_timeseries)
