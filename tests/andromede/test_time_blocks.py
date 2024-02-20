"""
This test file checks the consistency of variables and initial conditions gathering within or between time blocks depending on the requested time steps and the block boundary dynamics of the model (essentially the function get_variable_or_init_cond in optimization.py).
"""

import math
from unittest.mock import Mock

import ortools.linear_solver.pywraplp as lp
import pytest
from andromede.expression.indexing_structure import IndexingStructure

from andromede.study.data import DataBase
from andromede.model.model import BlockBoundariesDynamics, Model
from andromede.study.network import Component, Network
from andromede.simulation.optimization import (
    ComponentContext,
    OptimizationContext,
    OrchestrationMethod,
)
from andromede.simulation.time_block import TimeBlock, TimestepComponentVariableKey
from andromede.model.variable import Variable


@pytest.fixture
def mock_network() -> Mock:
    mock_network = Mock(spec=Network)
    mock_base = Mock(spec=Component)

    mock_base_model = Mock(spec=Model)
    mock_gen_var = Mock(spec=Variable)
    mock_gen_var.name = "generation"

    mock_base.id = "B"
    mock_base.model = mock_base_model
    mock_base.model.inter_block_dyn = BlockBoundariesDynamics.CYCLE
    mock_base.model.variables = {
        "generation": mock_gen_var,
    }

    mock_network.components = {"base": mock_base}
    return mock_network


@pytest.fixture
def mock_database() -> Mock:
    mock_database = Mock(spec=DataBase)
    return mock_database


@pytest.fixture
def block() -> TimeBlock:
    return TimeBlock(3, [8, 12, 14, 17])


@pytest.fixture
def previous_block() -> TimeBlock:
    return TimeBlock(2, [1, 2, 5, 6])


@pytest.fixture
def opt_context(
    mock_network: Mock, mock_database: Mock, block: TimeBlock, previous_block: TimeBlock
) -> OptimizationContext:
    scenarios = 2
    opt_context = OptimizationContext(
        mock_network,
        mock_database,
        block,
        previous_block,
        scenarios,
        OrchestrationMethod.SEQUENTIAL,
        initial_variables={},
    )

    # Add some variables in the optimization context
    for timestep in range(opt_context.block_length()):
        for scenario in range(scenarios):
            opt_context._component_variables[
                TimestepComponentVariableKey(
                    component_id="B",
                    variable_name="generation",
                    block_timestep=timestep,
                    scenario=scenario,
                )
            ] = Mock(spec=lp.Variable)

    for timestep in range(len(previous_block)):
        for scenario in range(scenarios):
            opt_context._initial_variables[
                TimestepComponentVariableKey(
                    "B",
                    "generation",
                    timestep,
                    scenario,
                )
            ] = Mock(
                spec=lp.Variable, solution_value=Mock(return_value=100.0 * timestep)
            )
    return opt_context


@pytest.fixture
def comp_context(
    opt_context: OptimizationContext, mock_network: Mock
) -> ComponentContext:
    return ComponentContext(opt_context, mock_network.components["base"])


def test_retrieve_variables_from_component_with_cycle_block_boundaries(
    mock_network: Mock,
    opt_context: OptimizationContext,
    comp_context: ComponentContext,
) -> None:
    mock_network.components[
        "base"
    ].model.inter_block_dyn = BlockBoundariesDynamics.CYCLE

    scenario = 1

    # Requested time step is within block
    assert (
        comp_context.get_variable_or_init_cond(
            2, scenario, "generation", IndexingStructure(True, True)
        )
        == opt_context._component_variables[
            TimestepComponentVariableKey("B", "generation", 2, scenario)
        ]
    )

    # Requested time step is outside block, use cycle strategy to get variable
    assert (
        comp_context.get_variable_or_init_cond(
            -4, scenario, "generation", IndexingStructure(True, True)
        )
        == opt_context._component_variables[
            TimestepComponentVariableKey("B", "generation", 0, scenario)
        ]
    )


def test_retrieve_variables_from_component_with_ignore_block_boundaries(
    mock_network: Mock,
    opt_context: OptimizationContext,
    comp_context: ComponentContext,
) -> None:
    mock_network.components[
        "base"
    ].model.inter_block_dyn = BlockBoundariesDynamics.IGNORE_BOUNDARIES

    scenario = 1

    # Requested time step is within block
    assert (
        comp_context.get_variable_or_init_cond(
            2, scenario, "generation", IndexingStructure(True, True)
        )
        == opt_context._component_variables[
            TimestepComponentVariableKey("B", "generation", 2, scenario)
        ]
    )

    # Requested time step is outside block, ignore boundaries -> Returns nothing
    assert (
        comp_context.get_variable_or_init_cond(
            -4, scenario, "generation", IndexingStructure(True, True)
        )
        is None
    )


def test_retrieve_variables_from_component_with_interblock_dynamics(
    mock_network: Mock,
    opt_context: OptimizationContext,
    comp_context: ComponentContext,
) -> None:
    mock_network.components[
        "base"
    ].model.inter_block_dyn = BlockBoundariesDynamics.INTERBLOCK_DYNAMICS

    scenario = 1

    # Requested time step is within block
    assert (
        comp_context.get_variable_or_init_cond(
            2, scenario, "generation", IndexingStructure(True, True)
        )
        == opt_context._component_variables[
            TimestepComponentVariableKey("B", "generation", 2, scenario)
        ]
    )
    # Requested time step is outside block in the future, raise Error
    with pytest.raises(
        ValueError,
        match="Cannot retrieve solution value for timesteps in future blocks.",
    ):
        comp_context.get_variable_or_init_cond(
            7, scenario, "generation", IndexingStructure(True, True)
        )

    # Requested time step is in previous block, retrieve variable solution value
    # block_timestep = -1 corresponds to time step 3 of previous time block, with associated solution value 300 in the test
    assert math.isclose(
        comp_context.get_variable_or_init_cond(
            -1, scenario, "generation", IndexingStructure(True, True)
        ),
        300.0,
        rel_tol=1e-16,
    )


def test_retrieve_variables_from_component_for_a_constant_over_time_and_scenario_variable_and_interblock_dynamics(
    mock_network: Mock,
    opt_context: OptimizationContext,
    comp_context: ComponentContext,
) -> None:
    mock_network.components[
        "base"
    ].model.inter_block_dyn = BlockBoundariesDynamics.INTERBLOCK_DYNAMICS

    scenario = 1

    # Requested time step is within block
    assert (
        comp_context.get_variable_or_init_cond(
            2, scenario, "generation", IndexingStructure(False, False)
        )
        == opt_context._component_variables[
            TimestepComponentVariableKey("B", "generation", 0, 0)
        ]
    )
    # Requested time step is outside block in the future, raise Error
    with pytest.raises(
        ValueError,
        match="Cannot retrieve solution value for timesteps in future blocks.",
    ):
        comp_context.get_variable_or_init_cond(
            7, scenario, "generation", IndexingStructure(False, False)
        )

    # Requested time step is in previous block, retrieve variable solution value
    # As variable is constant over time, retrieve value at previous block timestep 0
    assert math.isclose(
        comp_context.get_variable_or_init_cond(
            -1, scenario, "generation", IndexingStructure(False, False)
        ),
        0,
        abs_tol=1e-16,
    )


def test_in_the_first_time_block_ignore_variables_from_component_with_interblock_dynamics(
    mock_network: Network,
    mock_database: DataBase,
) -> None:
    mock_network.components[
        "base"
    ].model.inter_block_dyn = BlockBoundariesDynamics.INTERBLOCK_DYNAMICS

    previous_block = None
    block = TimeBlock(1, [8, 12, 14, 17])

    scenarios = 2

    opt_context = OptimizationContext(
        mock_network,
        mock_database,
        block,
        previous_block,
        scenarios,
        OrchestrationMethod.SEQUENTIAL,
        initial_variables={},
    )
    comp_context = ComponentContext(opt_context, mock_network.components["base"])

    assert (
        comp_context.get_variable_or_init_cond(
            -1, 0, "generation", IndexingStructure(True, False)
        )
        is None
    )
