import andromede.expression.scenario_operator
from andromede.expression.expression import (
    ComponentParameterNode,
    ComponentVariableNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    TimeOperatorNode,
)

from .expression import (
    AdditionNode,
    ComparisonNode,
    DivisionNode,
    ExpressionNode,
    LiteralNode,
    MultiplicationNode,
    NegationNode,
    ParameterNode,
    ScenarioOperatorNode,
    SubstractionNode,
    TimeAggregatorNode,
    VariableNode,
)
from .visitor import ExpressionVisitor, T, visit


class ExpressionDegreeVisitor(ExpressionVisitor[int]):
    """
    Computes degree of expression with respect to variables.
    """

    def comp_parameter(self, node: ComponentParameterNode) -> int:
        return 0

    def comp_variable(self, node: ComponentVariableNode) -> int:
        return 1

    def literal(self, node: LiteralNode) -> int:
        return 0

    def negation(self, node: NegationNode) -> int:
        return visit(node.operand, self)

    # TODO: Take into account simplification that can occur with literal coefficient for add, sub, mult, div
    def addition(self, node: AdditionNode) -> int:
        return max(visit(node.left, self), visit(node.right, self))

    def substraction(self, node: SubstractionNode) -> int:
        return max(visit(node.left, self), visit(node.right, self))

    def multiplication(self, node: MultiplicationNode) -> int:
        return visit(node.left, self) + visit(node.right, self)

    def division(self, node: DivisionNode) -> int:
        right_degree = visit(node.right, self)
        if right_degree != 0:
            raise ValueError("Degree computation not implemented for divisions.")
        return visit(node.left, self)

    def comparison(self, node: ComparisonNode) -> int:
        return max(visit(node.left, self), visit(node.right, self))

    def variable(self, node: VariableNode) -> int:
        return 1

    def parameter(self, node: ParameterNode) -> int:
        return 0

    def time_operator(self, node: TimeOperatorNode) -> int:
        if node.name in ["TimeShift", "TimeEvaluation"]:
            return visit(node.operand, self)
        else:
            return NotImplemented

    def time_aggregator(self, node: TimeAggregatorNode) -> int:
        if node.name in ["TimeSum"]:
            return visit(node.operand, self)
        else:
            return NotImplemented

    def scenario_operator(self, node: ScenarioOperatorNode) -> int:
        scenario_operator_cls = getattr(
            andromede.expression.scenario_operator, node.name
        )
        # TODO: Carefully check if this formula is correct
        return scenario_operator_cls.degree() * visit(node.operand, self)

    def port_field(self, node: PortFieldNode) -> int:
        return 1

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> int:
        return visit(node.operand, self)


def compute_degree(expression: ExpressionNode) -> int:
    return visit(expression, ExpressionDegreeVisitor())


def is_constant(expr: ExpressionNode) -> bool:
    """
    True if the expression has no variable.
    """
    return compute_degree(expr) == 0


def is_linear(expr: ExpressionNode) -> bool:
    """
    True if the expression is linear with respect to variables.
    """
    return compute_degree(expr) <= 1
