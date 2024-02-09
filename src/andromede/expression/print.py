from dataclasses import dataclass
from typing import Dict

from andromede.expression.expression import (
    ComponentParameterNode,
    ComponentVariableNode,
    ExpressionNode,
    PortFieldAggregatorNode,
    PortFieldNode,
)
from andromede.expression.visitor import T

from .expression import (
    AdditionNode,
    Comparator,
    ComparisonNode,
    DivisionNode,
    LiteralNode,
    MultiplicationNode,
    NegationNode,
    ParameterNode,
    ScenarioOperatorNode,
    SubstractionNode,
    TimeAggregatorNode,
    TimeOperatorNode,
    VariableNode,
)
from .visitor import ExpressionVisitor, visit

_COMPARISON_OPERATOR_TO_STRING: Dict[Comparator, str] = {
    Comparator.LESS_THAN: "<=",
    Comparator.EQUAL: "==",
    Comparator.GREATER_THAN: ">=",
}


@dataclass(frozen=True)
class PrinterVisitor(ExpressionVisitor[str]):
    """
    Produces a string representing the mathematical expression.

    TODO: remove parenthis where not necessary.
    """

    def comp_parameter(self, node: ComponentParameterNode) -> str:
        return f"{node.component_id}.{node.name}"

    def comp_variable(self, node: ComponentVariableNode) -> str:
        return f"{node.component_id}.{node.name}"

    def literal(self, node: LiteralNode) -> str:
        return str(node.value)

    def negation(self, node: NegationNode) -> str:
        return f"-({visit(node.operand, self)})"

    def addition(self, node: AdditionNode) -> str:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return f"({left_value} + {right_value})"

    def substraction(self, node: SubstractionNode) -> str:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return f"({left_value} - {right_value})"

    def multiplication(self, node: MultiplicationNode) -> str:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return f"({left_value} * {right_value})"

    def division(self, node: DivisionNode) -> str:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return f"({left_value} / {right_value})"

    def comparison(self, node: ComparisonNode) -> str:
        op = _COMPARISON_OPERATOR_TO_STRING[node.comparator]
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return f"{left_value} {op} {right_value}"

    def variable(self, node: VariableNode) -> str:
        return node.name

    def parameter(self, node: ParameterNode) -> str:
        return node.name

    # TODO: Add pretty print for node.instances_index
    def time_operator(self, node: TimeOperatorNode) -> str:
        return f"({visit(node.operand, self)}.{str(node.name)}({node.instances_index}))"

    def time_aggregator(self, node: TimeAggregatorNode) -> str:
        return f"({visit(node.operand, self)}.{str(node.name)}({node.stay_roll}))"

    def scenario_operator(self, node: ScenarioOperatorNode) -> str:
        return f"({visit(node.operand, self)}.{str(node.name)})"

    def port_field(self, node: PortFieldNode) -> str:
        return f"{node.port_name}.{node.field_name}"

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> str:
        return f"({visit(node.operand, self)}.{node.aggregator})"


def print_expr(expression: ExpressionNode) -> str:
    return visit(expression, PrinterVisitor())
