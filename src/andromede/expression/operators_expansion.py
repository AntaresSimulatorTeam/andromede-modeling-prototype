import dataclasses
from dataclasses import dataclass
from typing import Callable

from andromede.expression import CopyVisitor, ExpressionNode, sum_expressions, visit
from andromede.expression.expression import (
    AllTimeSumNode,
    ComponentParameterNode,
    ComponentVariableNode,
    ProblemParameterNode,
    ProblemVariableNode,
    ScenarioOperatorNode,
    TimeEvalNode,
    TimeShiftNode,
    TimeSumNode,
    problem_param,
    problem_var,
)
from andromede.expression.visitor import T

ExpressionEvaluator = Callable[[ExpressionNode], int]


@dataclass(frozen=True)
class OperatorsExpansion(CopyVisitor):
    """
    Replaces operators (shift, time sum, expectations ...) by their
    arithmetic expansion for a given timestep and scenario.

    This will allow to easily translate it to a plain linear expression later on,
    without complex handling of operators.
    """

    timestep: int
    scenario: int
    timesteps_count: int
    scenarios_count: int
    evaluator: ExpressionEvaluator

    def comp_variable(self, node: ComponentVariableNode) -> ExpressionNode:
        return problem_var(node.component_id, node.name, self.timestep, self.scenario)

    def comp_parameter(self, node: ComponentParameterNode) -> ExpressionNode:
        return problem_param(node.component_id, node.name, self.timestep, self.scenario)

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
            nodes.append(apply_timestep(operand, t))
        return sum_expressions(nodes)

    def scenario_operator(self, node: ScenarioOperatorNode) -> ExpressionNode:
        if node.name != "Expectation":
            raise ValueError(f"Scenario operator not supported: {node.name}")
        nodes = []
        operand = visit(node.operand, self)
        for t in range(self.scenarios_count):
            nodes.append(apply_scenario(operand, t))
        return sum_expressions(nodes)

    def pb_parameter(self, node: ProblemParameterNode) -> T:
        raise ValueError("Should not reach")

    def pb_variable(self, node: ProblemVariableNode) -> T:
        raise ValueError("Should not reach")


def expand_operators(
    expression: ExpressionNode,
    timestep: int,
    scenario: int,
    timesteps_count: int,
    scenarios_count: int,
    evaluator: ExpressionEvaluator,
) -> ExpressionNode:
    return visit(
        expression,
        OperatorsExpansion(
            timestep, scenario, timesteps_count, scenarios_count, evaluator
        ),
    )


@dataclass(frozen=True)
class ApplyTimeShift(CopyVisitor):
    timeshift: int

    def pb_parameter(self, node: ProblemParameterNode) -> T:
        return dataclasses.replace(node, timestep=node.timestep + self.timeshift)

    def pb_variable(self, node: ProblemVariableNode) -> T:
        return dataclasses.replace(node, timestep=node.timestep + self.timeshift)


def apply_timeshift(expression: ExpressionNode, timeshift: int) -> ExpressionNode:
    return visit(expression, ApplyTimeShift(timeshift))


@dataclass(frozen=True)
class ApplyTimeStep(CopyVisitor):
    timeshift: int

    def pb_parameter(self, node: ProblemParameterNode) -> ExpressionNode:
        return dataclasses.replace(node, timestep=node.timestep + self.timeshift)

    def pb_variable(self, node: ProblemVariableNode) -> ExpressionNode:
        return dataclasses.replace(node, timestep=node.timestep + self.timeshift)


def apply_timestep(expression: ExpressionNode, timestep: int) -> ExpressionNode:
    return visit(expression, ApplyTimeStep(timestep))


@dataclass(frozen=True)
class ApplyScenario(CopyVisitor):
    scenario: int

    def pb_parameter(self, node: ProblemParameterNode) -> T:
        return dataclasses.replace(node, scenario=self.scenario)

    def pb_variable(self, node: ProblemVariableNode) -> T:
        return dataclasses.replace(node, scenario=self.scenario)


def apply_scenario(expression: ExpressionNode, scenario: int) -> ExpressionNode:
    return visit(expression, ApplyScenario(scenario))
