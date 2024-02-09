import dataclasses
from dataclasses import dataclass
from typing import Optional

import andromede.expression.scenario_operator
import andromede.expression.time_operator
from andromede.expression.evaluate import ValueProvider
from andromede.expression.evaluate_parameters import get_time_ids_from_instances_index
from andromede.expression.expression import (
    ComparisonNode,
    ComponentParameterNode,
    ComponentVariableNode,
    ExpressionNode,
    LiteralNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorNode,
    TimeAggregatorNode,
    TimeOperatorNode,
    VariableNode,
)
from andromede.expression.indexing import IndexingStructureProvider
from andromede.expression.visitor import ExpressionVisitorOperations, T, visit
from andromede.simulation.linear_expression import LinearExpression, Term, generate_key


@dataclass(frozen=True)
class LinearExpressionBuilder(ExpressionVisitorOperations[LinearExpression]):
    """
    Reduces a generic expression to a linear expression.

    Parameters should have been evaluated first.
    """

    structure_provider: IndexingStructureProvider
    value_provider: Optional[ValueProvider] = None

    def literal(self, node: LiteralNode) -> LinearExpression:
        return LinearExpression([], node.value)

    def comparison(self, node: ComparisonNode) -> LinearExpression:
        raise ValueError("Linear expression cannot contain a comparison operator.")

    def variable(self, node: VariableNode) -> LinearExpression:
        raise ValueError(
            "Variables need to be associated with their component ID before linearization."
        )

    def parameter(self, node: ParameterNode) -> LinearExpression:
        raise ValueError("Parameters must be evaluated before linearization.")

    def time_operator(self, node: TimeOperatorNode) -> LinearExpression:
        if self.value_provider is None:
            raise ValueError(
                "A value provider must be specified to linearize a time operator node. This is required in order to evaluate the value of potential parameters used to specified the time ids on which the time operator applies."
            )

        operand_expr = visit(node.operand, self)
        time_operator_cls = getattr(andromede.expression.time_operator, node.name)
        time_ids = get_time_ids_from_instances_index(
            node.instances_index, self.value_provider
        )

        result_terms = {}
        for term in operand_expr.terms.values():
            term_with_operator = dataclasses.replace(
                term, time_operator=time_operator_cls(time_ids)
            )
            result_terms[generate_key(term_with_operator)] = term_with_operator

        # TODO: How can we apply a shift on a parameter ? It seems impossible for now as parameters must already be evaluated...
        result_expr = LinearExpression(result_terms, operand_expr.constant)
        return result_expr

    def time_aggregator(self, node: TimeAggregatorNode) -> LinearExpression:
        # TODO: Very similar to time_operator, may be factorized
        operand_expr = visit(node.operand, self)
        time_aggregator_cls = getattr(andromede.expression.time_operator, node.name)
        result_terms = {}
        for term in operand_expr.terms.values():
            term_with_operator = dataclasses.replace(
                term, time_aggregator=time_aggregator_cls(node.stay_roll)
            )
            result_terms[generate_key(term_with_operator)] = term_with_operator

        result_expr = LinearExpression(result_terms, operand_expr.constant)
        return result_expr

    def scenario_operator(self, node: ScenarioOperatorNode) -> LinearExpression:
        scenario_operator_cls = getattr(
            andromede.expression.scenario_operator, node.name
        )
        if scenario_operator_cls.degree() > 1:
            raise ValueError(
                f"Cannot linearize expression with a non-linear operator: {scenario_operator_cls.__name__}"
            )

        operand_expr = visit(node.operand, self)
        result_terms = {}
        for term in operand_expr.terms.values():
            term_with_operator = dataclasses.replace(
                term, scenario_operator=scenario_operator_cls()
            )
            result_terms[generate_key(term_with_operator)] = term_with_operator

        result_expr = LinearExpression(result_terms, operand_expr.constant)
        return result_expr

    def port_field(self, node: PortFieldNode) -> LinearExpression:
        raise ValueError("Port fields must be replaced before linearization.")

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> LinearExpression:
        raise ValueError("Port fields must be replaced before linearization.")

    def comp_parameter(self, node: ComponentParameterNode) -> LinearExpression:
        raise ValueError("Parameters must be evaluated before linearization.")

    def comp_variable(self, node: ComponentVariableNode) -> LinearExpression:
        return LinearExpression(
            [
                Term(
                    1,
                    node.component_id,
                    node.name,
                    self.structure_provider.get_component_variable_structure(
                        node.component_id, node.name
                    ),
                )
            ],
            0,
        )


def linearize_expression(
    expression: ExpressionNode,
    structure_provider: IndexingStructureProvider,
    value_provider: Optional[ValueProvider] = None,
) -> LinearExpression:
    return visit(
        expression, LinearExpressionBuilder(structure_provider, value_provider)
    )
