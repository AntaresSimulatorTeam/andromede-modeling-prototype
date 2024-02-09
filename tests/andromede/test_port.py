import pytest

from andromede.expression import literal
from andromede.expression.expression import port_field
from andromede.libs.standard import DEMAND_MODEL
from andromede.model import Constraint, ModelPort, PortType, model
from andromede.study import Node, PortRef, PortsConnection, create_component


def test_port_type_compatibility_ko() -> None:
    NODE_BALANCE_MODEL_FAKE = model(
        id="NODE_BALANCE_MODEL",
        ports=[
            ModelPort(port_type=PortType("balance_fake", []), port_name="balance_port")
        ],
        constraints=[
            Constraint(
                name="Balance",
                expression=port_field("balance_port", "flow").sum() == literal(0),
            )
        ],
    )
    node = Node(id="N", model=NODE_BALANCE_MODEL_FAKE)
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    port_1 = PortRef(demand, "balance_port")
    port_2 = PortRef(node, "balance_port")

    with pytest.raises(ValueError):
        PortsConnection(port_1, port_2)
