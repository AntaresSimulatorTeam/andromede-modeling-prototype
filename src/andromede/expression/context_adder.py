from dataclasses import dataclass

from . import CopyVisitor
from .expression import (
    ComponentParameterNode,
    ComponentVariableNode,
    ExpressionNode,
    ParameterNode,
    VariableNode,
)
from .visitor import visit


@dataclass(frozen=True)
class ContextAdder(CopyVisitor):
    """
    Simply copies the whole AST but associates all variables and parameters
    to the provided component ID.
    """

    component_id: str

    def variable(self, node: VariableNode) -> ExpressionNode:
        return ComponentVariableNode(self.component_id, node.name)

    def parameter(self, node: ParameterNode) -> ExpressionNode:
        return ComponentParameterNode(self.component_id, node.name)

    def comp_parameter(self, node: ComponentParameterNode) -> ExpressionNode:
        raise ValueError(
            "This expression has already been associated to another component."
        )

    def comp_variable(self, node: ComponentVariableNode) -> ExpressionNode:
        raise ValueError(
            "This expression has already been associated to another component."
        )


def add_component_context(id: str, expression: ExpressionNode) -> ExpressionNode:
    return visit(expression, ContextAdder(id))
