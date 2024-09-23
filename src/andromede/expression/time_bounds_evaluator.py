from abc import ABC, abstractmethod
from dataclasses import dataclass

from andromede.expression import (
    ComparisonNode,
    ExpressionNode,
    LiteralNode,
    ParameterNode,
    ParameterValueProvider,
    VariableNode,
    visit,
)
from andromede.expression.expression import (
    AllTimeSumNode,
    ComponentParameterNode,
    ComponentVariableNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ProblemParameterNode,
    ProblemVariableNode,
    ScenarioOperatorNode,
    TimeEvalNode,
    TimeShiftNode,
    TimeSumNode,
)
from andromede.expression.visitor import ExpressionVisitorOperations, T


class ConstantParameterValueProvider(ABC):
    """
    Provides values for constant parameters, does not need to know timestep or scenario.
    """

    @abstractmethod
    def get_parameter_value(self, component_id: str, name: str) -> float:
        pass


def float_to_int(value: float) -> int:
    if isinstance(value, int) or value.is_integer():
        return int(value)
    else:
        raise ValueError(f"{value} is not an integer.")


def evaluate_time_bound(
    expr: ExpressionNode, value_provider: ConstantParameterValueProvider
) -> int:
    float_time_bound = visit(expr, TimeBoundsEvaluator(value_provider))
    try:
        time_bound = float_to_int(float_time_bound)
    except ValueError:
        print(f"{expr} does not represent an integer time index.")
    return time_bound


@dataclass(frozen=True)
class TimeBoundsEvaluator(ExpressionVisitorOperations[float]):
    """
    Specialized evaluator to evaluate an expression that is allowed in time bounds:
    only constant parameters and no variables are allowed.
    """

    value_provider: ConstantParameterValueProvider

    def literal(self, node: LiteralNode) -> float:
        return node.value

    def comparison(self, node: ComparisonNode) -> float:
        raise ValueError(
            "Should not have comparison operator in time bound expressions."
        )

    def pb_parameter(self, node: ProblemParameterNode) -> float:
        raise ValueError("Time bounds should be evaluated before expansion.")

    def pb_variable(self, node: ProblemVariableNode) -> float:
        raise ValueError("Time bounds should be evaluated before expansion.")

    def scenario_operator(self, node: ScenarioOperatorNode) -> float:
        raise ValueError("Scenario operator not supported in time bounds.")

    def port_field(self, node: PortFieldNode) -> float:
        raise ValueError("Port fields not supported in time bounds.")

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> float:
        raise ValueError("Port fields aggregators are not supported in time bounds.")

    def variable(self, node: VariableNode) -> float:
        raise ValueError("A time bound expression cannot contain variables.")

    def comp_variable(self, node: ComponentVariableNode) -> float:
        raise ValueError("A time bound expression cannot contain variables.")

    def parameter(self, node: ParameterNode) -> float:
        raise ValueError("A time bound expression cannot contain parameters.")

    def comp_parameter(self, node: ComponentParameterNode) -> float:
        return self.value_provider.get_parameter_value(node.component_id, node.name)

    def time_shift(self, node: TimeShiftNode) -> float:
        raise ValueError("An instance index expression cannot contain time shift")

    def time_eval(self, node: TimeEvalNode) -> float:
        raise ValueError("An instance index expression cannot contain time eval")

    def time_sum(self, node: TimeSumNode) -> float:
        raise ValueError("An instance index expression cannot contain time sum")

    def all_time_sum(self, node: AllTimeSumNode) -> float:
        raise ValueError("An instance index expression cannot contain time sum")
