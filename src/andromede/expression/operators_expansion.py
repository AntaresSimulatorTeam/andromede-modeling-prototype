import dataclasses
from dataclasses import dataclass
from typing import Callable, TypeVar, Union

from andromede.expression import CopyVisitor, ExpressionNode, sum_expressions, visit
from andromede.expression.expression import (
    AllTimeSumNode,
    ComponentParameterNode,
    ComponentVariableNode,
    NoScenarioIndex,
    NoTimeIndex,
    OneScenarioIndex,
    ProblemParameterNode,
    ProblemVariableNode,
    ScenarioOperatorNode,
    TimeEvalNode,
    TimeShift,
    TimeShiftNode,
    TimeStep,
    TimeSumNode,
    problem_param,
    problem_var,
)
from andromede.expression.visitor import T

ExpressionEvaluator = Callable[[ExpressionNode], int]


@dataclass(frozen=True)
class ProblemDimensions:
    """
    Dimensions for the simulation window
    """

    timesteps_count: int
    scenarios_count: int


@dataclass(frozen=True)
class ProblemIndex:
    """
    Index of an object in the simulation window.
    """

    timestep: int
    scenario: int


@dataclass(frozen=True)
class OperatorsExpansion(CopyVisitor):
    """
    Replaces operators (shift, time sum, expectations ...) by their
    arithmetic expansion for a given timestep and scenario.

    This will allow to easily translate it to a plain linear expression later on,
    without complex handling of operators.
    """

    timesteps_count: int
    scenarios_count: int
    evaluator: ExpressionEvaluator

    def comp_variable(self, node: ComponentVariableNode) -> ExpressionNode:
        return problem_var(
            node.component_id, node.name, TimeShift(0), NoScenarioIndex()
        )

    def comp_parameter(self, node: ComponentParameterNode) -> ExpressionNode:
        return problem_param(
            node.component_id, node.name, TimeShift(0), NoScenarioIndex()
        )

    def time_shift(self, node: TimeShiftNode) -> ExpressionNode:
        shift = self.evaluator(node.time_shift)
        operand = visit(node.operand, self)
        return apply_timeshift(operand, shift)

    def time_eval(self, node: TimeEvalNode) -> ExpressionNode:
        timestep = self.evaluator(node.eval_time)
        operand = visit(node.operand, self)
        return apply_timestep(operand, timestep)

    def time_sum(self, node: TimeSumNode) -> ExpressionNode:
        from_shift = self.evaluator(node.from_time)
        to_shift = self.evaluator(node.to_time)
        operand = visit(node.operand, self)
        nodes = []
        for t in range(from_shift, to_shift + 1):
            nodes.append(apply_timeshift(operand, t))
        return sum_expressions(nodes)

    def all_time_sum(self, node: AllTimeSumNode) -> ExpressionNode:
        nodes = []
        operand = visit(node.operand, self)
        for t in range(self.timesteps_count):
            # if we sum previously "evaluated" variables for example x[0], it's ok
            nodes.append(apply_timestep(operand, t, allow_existing=True))
        return sum_expressions(nodes)

    def scenario_operator(self, node: ScenarioOperatorNode) -> ExpressionNode:
        if node.name != "Expectation":
            raise ValueError(f"Scenario operator not supported: {node.name}")
        nodes = []
        operand = visit(node.operand, self)
        for t in range(self.scenarios_count):
            nodes.append(apply_scenario(operand, t))
        return sum_expressions(nodes) / self.scenarios_count

    def pb_parameter(self, node: ProblemParameterNode) -> T:
        raise ValueError("Should not reach")

    def pb_variable(self, node: ProblemVariableNode) -> T:
        raise ValueError("Should not reach")


def expand_operators(
    expression: ExpressionNode,
    dimensions: ProblemDimensions,
    evaluator: ExpressionEvaluator,
) -> ExpressionNode:
    return visit(
        expression,
        OperatorsExpansion(
            dimensions.timesteps_count, dimensions.scenarios_count, evaluator
        ),
    )


TimeIndexedNode = TypeVar(
    "TimeIndexedNode", bound=Union[ProblemParameterNode, ProblemVariableNode]
)


@dataclass(frozen=True)
class ApplyTimeShift(CopyVisitor):
    """
    Shifts all underlying expressions.
    """

    timeshift: int

    def _apply_timeshift(self, node: TimeIndexedNode) -> TimeIndexedNode:
        current_index = node.time_index
        if isinstance(current_index, TimeShift):
            return dataclasses.replace(
                node, time_index=TimeShift(current_index.timeshift + self.timeshift)
            )
        if isinstance(current_index, TimeStep):
            return dataclasses.replace(
                node, time_index=TimeStep(current_index.timestep + self.timeshift)
            )
        if isinstance(current_index, NoTimeIndex):
            return node
        raise ValueError("Unknown time index type.")

    def pb_parameter(self, node: ProblemParameterNode) -> ProblemParameterNode:
        return self._apply_timeshift(node)

    def pb_variable(self, node: ProblemVariableNode) -> ProblemVariableNode:
        return self._apply_timeshift(node)


def apply_timeshift(expression: ExpressionNode, timeshift: int) -> ExpressionNode:
    return visit(expression, ApplyTimeShift(timeshift))


@dataclass(frozen=True)
class ApplyTimeStep(CopyVisitor):
    """
    Applies timestep to all underlying expressions.
    """

    timestep: int
    allow_existing: bool = False

    def _apply_timestep(self, node: TimeIndexedNode) -> TimeIndexedNode:
        current_index = node.time_index
        if isinstance(current_index, TimeShift):
            return dataclasses.replace(
                node, time_index=TimeStep(current_index.timeshift + self.timestep)
            )
        if isinstance(current_index, TimeStep):
            if not self.allow_existing:
                raise ValueError(
                    "Cannot override a previously defined timestep (for example (x[0])[1])."
                )
            return node
        if isinstance(current_index, NoTimeIndex):
            return node
        raise ValueError("Unknown time index type.")

    def pb_parameter(self, node: ProblemParameterNode) -> ExpressionNode:
        return self._apply_timestep(node)

    def pb_variable(self, node: ProblemVariableNode) -> ExpressionNode:
        return self._apply_timestep(node)


def apply_timestep(
    expression: ExpressionNode, timestep: int, allow_existing: bool = False
) -> ExpressionNode:
    return visit(expression, ApplyTimeStep(timestep, allow_existing))


@dataclass(frozen=True)
class ApplyScenario(CopyVisitor):
    scenario: int

    def pb_parameter(self, node: ProblemParameterNode) -> ExpressionNode:
        return dataclasses.replace(node, scenario_index=OneScenarioIndex(self.scenario))

    def pb_variable(self, node: ProblemVariableNode) -> ExpressionNode:
        return dataclasses.replace(node, scenario_index=OneScenarioIndex(self.scenario))


def apply_scenario(expression: ExpressionNode, scenario: int) -> ExpressionNode:
    return visit(expression, ApplyScenario(scenario))
