from typing import List

import pytest

from andromede.expression.expression import ExpressionRange, literal, param, var
from andromede.libs.standard import (
    ANTICIPATIVE_TIME_VARYING,
    BALANCE_PORT_TYPE,
    CONSTANT,
    DEMAND_MODEL,
    NODE_WITH_SPILL_AND_ENS_MODEL,
    SPILLAGE_MODEL,
    THERMAL_CLUSTER_MODEL_HD,
    TIME_AND_SCENARIO_FREE,
    UNSUPPLIED_ENERGY_MODEL,
)
from andromede.model.constraint import Constraint
from andromede.model.model import (
    BlockBoundariesDynamics,
    Model,
    ModelPort,
    PortFieldDefinition,
    PortFieldId,
    model,
)
from andromede.model.parameter import float_parameter, int_parameter
from andromede.model.variable import float_variable, int_variable
from andromede.simulation.optimization import build_problem
from andromede.simulation.optimization_orchestrator import (
    OptimizationOrchestrator,
    OrchestrationMethod,
)
from andromede.simulation.time_block import TimeBlock
from andromede.study.data import ConstantData, DataBase, TimeIndex, TimeSeriesData
from andromede.study.network import Component, Network, Node, PortRef, create_component
from tests.andromede.test_utils import generate_data


@pytest.fixture
def database() -> DataBase:
    database = DataBase()

    data = {}
    data[TimeIndex(0)] = 0
    data[TimeIndex(1)] = 0
    data[TimeIndex(2)] = 0
    data[TimeIndex(3)] = 500
    data[TimeIndex(4)] = 0
    data[TimeIndex(5)] = 0
    data[TimeIndex(6)] = 500
    data[TimeIndex(7)] = 0
    data[TimeIndex(8)] = 0
    data[TimeIndex(9)] = 0

    demand_data = TimeSeriesData(time_series=data)

    database.add_data("D", "demand", demand_data)

    database.add_data("N", "spillage_cost", ConstantData(10))
    database.add_data("N", "ens_cost", ConstantData(1000))

    database.add_data("BASE", "nb_failures", generate_data(1, horizon=5, scenarios=1))

    database.add_data("BASE", "p_max", ConstantData(500))
    database.add_data("BASE", "p_min", ConstantData(100))
    database.add_data("BASE", "cost", ConstantData(30))
    database.add_data("BASE", "d_min_up", ConstantData(1))
    database.add_data("BASE", "d_min_down", ConstantData(4))
    database.add_data("BASE", "nb_units_max", ConstantData(1))

    return database


@pytest.fixture
def thermal_cycle_dynamics() -> Model:
    return THERMAL_CLUSTER_MODEL_HD


@pytest.fixture
def thermal_with_dynamics() -> Model:
    thermal_with_dynamics = model(
        id="GEN_WITH_DYN",
        inter_block_dyn=BlockBoundariesDynamics.INTERBLOCK_DYNAMICS,
        parameters=[
            float_parameter("p_max", CONSTANT),  # p_max of a single unit
            float_parameter("p_min", CONSTANT),
            float_parameter("d_min_up", CONSTANT),
            float_parameter("d_min_down", CONSTANT),
            float_parameter("cost", CONSTANT),
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
                lower_bound=literal(0),
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
                var("nb_on")
                == var("nb_on").shift(-1) + var("nb_start") - var("nb_stop"),
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
        ],
        objective_operational_contribution=(param("cost") * var("generation"))
        .sum()
        .expec(),
    )
    return thermal_with_dynamics


@pytest.fixture
def demand() -> Component:
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )
    return demand


@pytest.fixture
def spillage() -> Component:
    spillage = create_component(model=SPILLAGE_MODEL, id="S")
    return spillage


@pytest.fixture
def unsupplied_energy() -> Component:
    unsupplied_energy = create_component(
        model=UNSUPPLIED_ENERGY_MODEL,
        id="U",
    )
    return unsupplied_energy


@pytest.fixture
def time_blocks() -> List[TimeBlock]:
    time_blocks = [TimeBlock(1, [0, 1, 2, 3, 4]), TimeBlock(2, [5, 6, 7, 8, 9])]
    return time_blocks


def test_thermal_no_dynamics(
    database: DataBase,
    time_blocks: List[TimeBlock],
    demand: Component,
    thermal_cycle_dynamics: Model,
) -> None:
    """
    No interblock dynamics is taken into account in the thermal cluster, hence the optimization are independent by block.

    The demand is as follows :
    -------- Block 1 ---------
    demand[0] = 0
    demand[1] = 0
    demand[2] = 0
    demand[3] = 500
    demand[4] = 0
    -------- Block 2 --------
    demand[5] = 0
    demand[6] = 500
    demand[7] = 0
    demand[8] = 0
    demand[9] = 0

    Ad d_min_up = 1, the optimal solution is to turn on the thermal cluster when the demand is 500 and turn it off otherwise. The optimal value of each block problem is 500 x 30
    """

    node = Node(model=NODE_WITH_SPILL_AND_ENS_MODEL, id="N")

    base = create_component(
        model=thermal_cycle_dynamics,
        id="BASE",
    )

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(base)

    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(base, "balance_port"), PortRef(node, "balance_port"))

    scenarios = 1
    for block in time_blocks:
        problem = build_problem(network, database, block, scenarios)
        status = problem.solver.Solve()

        assert status == problem.solver.OPTIMAL
        assert problem.solver.Objective().Value() == 500 * 30


def test_thermal_with_dynamics(
    database: DataBase,
    time_blocks: List[TimeBlock],
    demand: Component,
    thermal_with_dynamics: Model,
) -> None:
    """
    An interblock dynamics is taken into account in the thermal cluster.

    The demand is as follows :
    -------- Block 1 ---------
    demand[0] = 0
    demand[1] = 0
    demand[2] = 0
    demand[3] = 500
    demand[4] = 0
    -------- Block 2 --------
    demand[5] = 0
    demand[6] = 500
    demand[7] = 0
    demand[8] = 0
    demand[9] = 0

    If we solve the blocks sequentially, the optimal solution of the first problem will turn on the cluster at time 3 and then turn it off. The optimal value is 500 x 30.

    Then, on the second block, as we have d_min_down = 4, the unit will not be able to turn on at time 6, hence there is unsupplied energy. The optimal solution is 500 x 1000.
    """

    node = Node(model=NODE_WITH_SPILL_AND_ENS_MODEL, id="N")

    base = create_component(
        model=thermal_with_dynamics,
        id="BASE",
    )

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(base)

    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(base, "balance_port"), PortRef(node, "balance_port"))

    scenarios = 1
    orchestrator = OptimizationOrchestrator(
        network, database, time_blocks, OrchestrationMethod.SEQUENTIAL, scenarios
    )
    block_solution_dict = orchestrator.run()

    for block_id, problem_status in block_solution_dict.items():
        assert problem_status[1] == problem_status[0].solver.OPTIMAL
        if block_id == 1:
            assert problem_status[0].solver.Objective().Value() == pytest.approx(
                500 * 30, rel=1e-10
            )
        else:
            assert problem_status[0].solver.Objective().Value() == pytest.approx(
                500 * 1000, rel=1e-10
            )
