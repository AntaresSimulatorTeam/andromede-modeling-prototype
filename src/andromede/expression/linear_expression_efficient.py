# Copyright (c) 2024, RTE (https://www.rte-france.com)
#
# See AUTHORS.txt
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0
#
# This file is part of the Antares project.

"""
Specific modelling for "instantiated" linear expressions,
with only variables and literal coefficients.
"""
import dataclasses
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
    cast,
    overload,
)

import ortools.linear_solver.pywraplp as lp

from andromede.expression.context_adder import add_component_context
from andromede.expression.equality import expressions_equal
from andromede.expression.evaluate import evaluate
from andromede.expression.evaluate_parameters_efficient import (
    check_resolved_expr,
    get_time_ids_from_instances_index,
    resolve_coefficient,
)
from andromede.expression.expression_efficient import (
    ExpressionNodeEfficient,
    ExpressionRange,
    InstancesTimeIndex,
    LiteralNode,
    ScenarioOperatorName,
    ScenarioOperatorNode,
    TimeAggregatorName,
    TimeAggregatorNode,
    TimeOperatorName,
    TimeOperatorNode,
    is_minus_one,
    is_one,
    is_unbound,
    is_zero,
    literal,
    wrap_in_node,
)
from andromede.expression.indexing import IndexingStructureProvider
from andromede.expression.indexing_structure import IndexingStructure, RowIndex
from andromede.expression.port_operator import PortAggregator, PortSum
from andromede.expression.print import print_expr
from andromede.expression.resolved_linear_expression import (
    ResolvedLinearExpression,
    ResolvedTerm,
)
from andromede.expression.scenario_operator import Expectation, ScenarioAggregator
from andromede.expression.time_operator import (
    TimeAggregator,
    TimeEvaluation,
    TimeOperator,
    TimeShift,
    TimeSum,
)
from andromede.expression.value_provider import (
    TimeScenarioIndex,
    TimeScenarioIndices,
    ValueProvider,
)


@dataclass(frozen=True)
class TermKeyEfficient:
    """
    Utility class to provide key for a term that contains all term information except coefficient
    """

    component_id: str
    variable_name: str
    time_operator: Optional[TimeOperator]
    time_aggregator: Optional[TimeAggregator]
    scenario_aggregator: Optional[ScenarioAggregator]


@dataclass(frozen=True)
class TermEfficient:
    """
    One term in a linear expression: for example the "10x" par in "10x + 5y + 5"

    Args:
        coefficient: the coefficient for that term, for example "10" in "10x"
        variable_name: the name of the variable, for example "x" in "10x"
    """

    coefficient: ExpressionNodeEfficient
    component_id: str
    variable_name: str
    structure: IndexingStructure = field(
        default=IndexingStructure(time=True, scenario=True)
    )
    time_operator: Optional[TimeOperator] = None
    time_aggregator: Optional[TimeAggregator] = None
    scenario_aggregator: Optional[ScenarioAggregator] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "coefficient", wrap_in_node(self.coefficient))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, TermEfficient)
            and expressions_equal(self.coefficient, other.coefficient)
            and self.component_id == other.component_id
            and self.variable_name == other.variable_name
            and self.structure == other.structure
            and self.time_operator == other.time_operator
            and self.time_aggregator == other.time_aggregator
            and self.scenario_aggregator == other.scenario_aggregator
        )

    def is_zero(self) -> bool:
        return is_zero(self.coefficient)

    def str_for_coeff(self) -> str:
        str_for_coeff = ""
        if is_one(self.coefficient):
            str_for_coeff = "+"
        elif is_minus_one(self.coefficient):
            str_for_coeff = "-"
        else:
            str_for_coeff = print_expr(self.coefficient)
        return str_for_coeff

    def __str__(self) -> str:
        # Useful for debugging tests
        result = self.str_for_coeff() + str(self.variable_name)
        if self.time_operator is not None:
            result += f".{str(self.time_operator)}"
        if self.time_aggregator is not None:
            result += f".{str(self.time_aggregator)}"
        if self.scenario_aggregator is not None:
            result += f".{str(self.scenario_aggregator)}"
        return result

    def evaluate(self, context: ValueProvider, time_scenario_index: RowIndex) -> float:
        # TODO: Take care of component variables, multiple time scenarios, operators, etc
        time_scenario_indices = TimeScenarioIndices(
            [time_scenario_index.time], [time_scenario_index.scenario]
        )
        # Probably very error prone
        if self.component_id:
            variable_value = context.get_component_variable_value(
                self.component_id, self.variable_name, time_scenario_indices
            )
        else:
            variable_value = context.get_variable_value(
                self.variable_name, time_scenario_indices
            )
        check_resolved_expr(variable_value, time_scenario_index)
        return (
            resolve_coefficient(self.coefficient, context, time_scenario_index)
            * variable_value[
                TimeScenarioIndex(
                    time_scenario_index.time, time_scenario_index.scenario
                )
            ]
        )

    def compute_indexation(
        self, provider: IndexingStructureProvider
    ) -> IndexingStructure:
        return IndexingStructure(
            self._compute_time_indexing(provider),
            self._compute_scenario_indexing(provider),
        )

    def _compute_time_indexing(self, provider: IndexingStructureProvider) -> bool:
        if (self.time_aggregator and not self.time_aggregator.stay_roll) or (
            self.time_operator and not self.time_operator.rolling()
        ):
            time = False
        else:
            if self.component_id:
                time = provider.get_component_variable_structure(
                    self.component_id, self.variable_name
                ).time
            else:
                time = provider.get_variable_structure(self.variable_name).time
        return time

    def _compute_scenario_indexing(self, provider: IndexingStructureProvider) -> bool:
        if self.scenario_aggregator:
            scenario = False
        else:
            # TODO: Improve this if/else structure, probably simplify IndexingStructureProvider
            if self.component_id:
                scenario = provider.get_component_variable_structure(
                    self.component_id, self.variable_name
                ).scenario

            else:
                scenario = provider.get_variable_structure(self.variable_name).scenario
        return scenario

    def sum(
        self,
        shift: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
            None,
        ] = None,
        eval: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
            None,
        ] = None,
    ) -> "TermEfficient":
        if shift is not None and eval is not None:
            raise ValueError("Only shift or eval arguments should specified, not both.")

        # The shift or eval operators applies on the variable, then it will define at which time step the term coefficient * variable will be evaluated

        if shift is not None:
            return dataclasses.replace(
                self,
                # coefficient=TimeOperatorNode(
                #     self.coefficient, TimeOperatorName.SHIFT, InstancesTimeIndex(shift)
                # ),
                time_operator=TimeShift(InstancesTimeIndex(shift)),
                time_aggregator=TimeSum(stay_roll=True),
            )
        elif eval is not None:
            return dataclasses.replace(
                self,
                # coefficient=TimeOperatorNode(
                #     self.coefficient,
                #     TimeOperatorName.EVALUATION,
                #     InstancesTimeIndex(eval),
                # ),
                time_operator=TimeEvaluation(InstancesTimeIndex(eval)),
                time_aggregator=TimeSum(stay_roll=True),
            )
        else:  # x.sum() -> Sum over all time block
            return dataclasses.replace(self, time_aggregator=TimeSum(stay_roll=False))

    def shift(
        self,
        expressions: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
        ],
    ) -> "TermEfficient":
        """
        Shorthand for shift on a single time step

        To refer to x[t-1], it is more natural to write x.shift(-1) than x.sum(shift=-1).

        This function provides the shorthand x.sum(shift=expr), valid only in the case when expr refers to a single time step.

        """

        # The behavior is richer/different than the previous implementation (with linear expr as trees) as we can now apply a shift operator on a whole expression, rather than just on the variables of an expression

        # Example : (param("p") * var("x")).shift(1)
        # Previous behavior : p[t]x[t-1]
        # New behavior : p[t-1]x[t-1]

        if not InstancesTimeIndex(expressions).is_simple():
            raise ValueError(
                "The shift operator can only be applied on expressions refering to a single time step. To apply a shifting sum on multiple time indices on an expression x, you should use x.sum(shift=...)"
            )

        else:
            return self.sum(shift=expressions)

    def eval(
        self,
        expressions: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
        ],
    ) -> "TermEfficient":
        """
        Shorthand for eval on a single time step

        To refer to x[1], it is more natural to write x.eval(1) than x.sum(eval=1).

        This function provides the shorthand x.sum(eval=expr), valid only in the case when expr refers to a single time step.

        """

        # The behavior is richer/different than the previous implementation (with linear expr as trees) as we can now apply a eval operator on a whole expression, rather than just on the variables of an expression

        # Example : (param("p") * var("x")).eval(1)
        # Previous behavior : p[t]x[1]
        # New behavior : p[1]x[1]

        if not InstancesTimeIndex(expressions).is_simple():
            raise ValueError(
                "The eval operator can only be applied on expressions refering to a single time step. To apply a evaluating sum on multiple time indices on an expression x, you should use x.sum(eval=...)"
            )

        else:
            return self.sum(eval=expressions)

    def expec(self) -> "TermEfficient":
        # TODO: Do we need checks, in case a scenario operator is already specified ?
        return dataclasses.replace(self, scenario_aggregator=Expectation())


def generate_key(term: TermEfficient) -> TermKeyEfficient:
    return TermKeyEfficient(
        term.component_id,
        term.variable_name,
        term.time_operator,
        term.time_aggregator,
        term.scenario_aggregator,
    )


@dataclass(frozen=True)
class PortFieldId:
    port_name: str
    field_name: str


@dataclass(eq=True, frozen=True)
class PortFieldKey:
    """
    Identifies the expression node for one component and one port variable.
    """

    component_id: str
    port_variable_id: PortFieldId


@dataclass(frozen=True)
class PortFieldTerm:
    coefficient: ExpressionNodeEfficient
    port_name: str
    field_name: str
    aggregator: Optional[PortAggregator] = None

    def __str__(self) -> str:
        result = f"{self.port_name}.{self.field_name}"
        if self.aggregator is not None:
            result += f".{str(self.aggregator)}"
        return result

    def sum_connections(self) -> "LinearExpressionEfficient":
        if self.aggregator is not None:
            raise ValueError(f"Port field {str(self)} already has a port aggregator")
        return dataclasses.replace(self, aggregator=PortSum())


T_val = TypeVar("T_val", bound=Union[TermEfficient, PortFieldTerm])


@overload
def _merge_dicts(
    lhs: Dict[TermKeyEfficient, TermEfficient],
    rhs: Dict[TermKeyEfficient, TermEfficient],
    merge_func: Callable[[TermEfficient, TermEfficient], TermEfficient],
    neutral: float,
) -> Dict[TermKeyEfficient, TermEfficient]: ...


@overload
def _merge_dicts(
    lhs: Dict[PortFieldId, PortFieldTerm],
    rhs: Dict[PortFieldId, PortFieldTerm],
    merge_func: Callable[[PortFieldTerm, PortFieldTerm], PortFieldTerm],
    neutral: float,
) -> Dict[PortFieldId, PortFieldTerm]: ...


def _get_neutral_term(term: T_val, neutral: float) -> T_val:
    return dataclasses.replace(term, coefficient=neutral)


def _merge_dicts(lhs, rhs, merge_func, neutral):
    res = {}
    for k, v in lhs.items():
        res[k] = merge_func(v, rhs.get(k, _get_neutral_term(v, neutral)))
    for k, v in rhs.items():
        if k not in lhs:
            res[k] = merge_func(_get_neutral_term(v, neutral), v)
    return res


def _merge_is_possible(lhs: T_val, rhs: T_val) -> None:
    if isinstance(lhs, TermEfficient) and isinstance(rhs, TermEfficient):
        _merge_term_is_possible(lhs, rhs)
    elif isinstance(lhs, PortFieldTerm) and isinstance(rhs, PortFieldTerm):
        _merge_port_terms_is_possible(lhs, rhs)
    else:
        raise TypeError("Cannot merge terms of different types")


def _merge_term_is_possible(lhs: TermEfficient, rhs: TermEfficient) -> None:
    if lhs.component_id != rhs.component_id or lhs.variable_name != rhs.variable_name:
        raise ValueError("Cannot merge terms for different variables")
    if (
        lhs.time_operator != rhs.time_operator
        or lhs.time_aggregator != rhs.time_aggregator
        or lhs.scenario_aggregator != rhs.scenario_aggregator
    ):
        raise ValueError("Cannot merge terms with different operators")
    if lhs.structure != rhs.structure:
        raise ValueError("Cannot merge terms with different structures")


def _merge_port_terms_is_possible(lhs: PortFieldTerm, rhs: PortFieldTerm) -> None:
    if lhs.port_name != rhs.port_name or lhs.field_name != rhs.field_name:
        raise ValueError("Cannot merge terms for different ports")
    if lhs.aggregator != rhs.aggregator:
        raise ValueError("Cannot merge port terms with different aggregators")


def _add_terms(lhs: T_val, rhs: T_val) -> T_val:
    _merge_is_possible(lhs, rhs)
    return dataclasses.replace(lhs, coefficient=lhs.coefficient + rhs.coefficient)


def _substract_terms(lhs: T_val, rhs: T_val) -> T_val:
    _merge_is_possible(lhs, rhs)
    return dataclasses.replace(lhs, coefficient=lhs.coefficient - rhs.coefficient)


class LinearExpressionEfficient:
    """
    Represents a linear expression with respect to variable names, for example 10x + 5y + 2.

    Operators may be used for construction.

    Args:
        terms: the list of variable terms, for example 10x and 5y in "10x + 5y + 2".
        constant: the constant term, for example 2 in "10x + 5y + 2"

    Examples:
        Operators may be used for construction:

        >>> LinearExpression([], 10) + LinearExpression([TermEfficient(10, "x")], 0)
        LinearExpression([TermEfficient(10, "x")], 10)
    """

    terms: Dict[TermKeyEfficient, TermEfficient]
    constant: ExpressionNodeEfficient
    port_field_terms: Dict[PortFieldId, PortFieldTerm]

    # TODO: We need to check that terms.key is indeed a TermKey and change the tests that this will break
    def __init__(
        self,
        terms: Optional[
            Union[Dict[TermKeyEfficient, TermEfficient], List[TermEfficient]]
        ] = None,
        constant: Optional[Union[float, ExpressionNodeEfficient]] = None,
        port_field_terms: Optional[
            Union[Dict[PortFieldId, PortFieldTerm], List[PortFieldTerm]]
        ] = None,
    ) -> None:
        if constant is None:
            self.constant = LiteralNode(0)
        else:
            self.constant = wrap_in_node(constant)

        self.terms = {}
        if terms is not None:
            # Allows to give two different syntax in the constructor:
            #   - List[TermEfficient] is natural
            #   - Dict[str, TermEfficient] is useful when constructing a linear expression from the terms of another expression
            if isinstance(terms, dict):
                for term_key, term in terms.items():
                    if not term.is_zero():
                        self.terms[term_key] = term
            elif isinstance(terms, list):
                for term in terms:
                    if not term.is_zero():
                        self.terms[generate_key(term)] = term
            else:
                raise TypeError(
                    f"Terms must be either of type Dict[TermKeyEfficient, Term] or List[Term], whereas {terms} is of type {type(terms)}"
                )

        self.port_field_terms = {}
        if port_field_terms is not None:
            if isinstance(port_field_terms, dict):
                for port_field_term_key, port_field_term in port_field_terms.items():
                    self.port_field_terms[port_field_term_key] = port_field_term
            elif isinstance(port_field_terms, list):
                for port_field_term in port_field_terms:
                    self.port_field_terms[
                        PortFieldId(
                            port_field_term.port_name, port_field_term.field_name
                        )
                    ] = port_field_term
            else:
                raise TypeError(
                    f"Port field terms must be either of type Dict[PortFieldKey, PortFieldTerm] or List[PortFieldTerm], whereas {port_field_terms} is of type {type(port_field_terms)}"
                )

    def is_zero(self) -> bool:
        # TODO : Contribution of portfield ?
        return len(self.terms) == 0 and is_zero(self.constant)

    def str_for_constant(self) -> str:
        if is_zero(self.constant):
            return ""
        else:
            const_str = print_expr(self.constant)
            if const_str.startswith("+"):
                return f" + {const_str[1:]}"
            elif const_str.startswith("-"):
                return f" + ({const_str})"
            else:
                return f" + {print_expr(self.constant)}"

    def __str__(self) -> str:
        # Useful for debugging tests
        result = ""
        if self.is_zero():
            result += "0"
        else:
            for term in self.terms.values():
                result += str(term)

            result += self.str_for_constant()

        return result

    def __le__(self, rhs: Any) -> "StandaloneConstraint":
        return StandaloneConstraint(
            expression=self - rhs,
            lower_bound=wrap_in_linear_expr(literal(-float("inf"))),
            upper_bound=wrap_in_linear_expr(literal(0)),
        )

    def __ge__(self, rhs: Any) -> "StandaloneConstraint":
        return StandaloneConstraint(
            expression=self - rhs,
            lower_bound=wrap_in_linear_expr(literal(0)),
            upper_bound=wrap_in_linear_expr(literal(float("inf"))),
        )

    def __eq__(self, rhs: Any) -> "StandaloneConstraint":  # type: ignore
        return StandaloneConstraint(
            expression=self - rhs,
            lower_bound=wrap_in_linear_expr(literal(0)),
            upper_bound=wrap_in_linear_expr(literal(0)),
        )

    def __iadd__(
        self, rhs: Union["LinearExpressionEfficient", int, float]
    ) -> "LinearExpressionEfficient":
        rhs = wrap_in_linear_expr(rhs)
        self.constant += rhs.constant

        aggregated_terms = _merge_dicts(self.terms, rhs.terms, _add_terms, 0)
        self.terms = aggregated_terms

        aggregated_port_terms = _merge_dicts(
            self.port_field_terms, rhs.port_field_terms, _add_terms, 0
        )
        self.port_field_terms = aggregated_port_terms

        self.remove_zeros_from_terms()
        return self

    def __add__(
        self, rhs: Union["LinearExpressionEfficient", int, float]
    ) -> "LinearExpressionEfficient":
        result = LinearExpressionEfficient()
        result += self
        result += rhs
        return result

    def __radd__(self, rhs: int) -> "LinearExpressionEfficient":
        return self.__add__(rhs)

    def __isub__(
        self, rhs: Union["LinearExpressionEfficient", int, float]
    ) -> "LinearExpressionEfficient":
        rhs = wrap_in_linear_expr(rhs)
        self.constant -= rhs.constant

        aggregated_terms = _merge_dicts(self.terms, rhs.terms, _substract_terms, 0)
        self.terms = aggregated_terms

        aggregated_port_terms = _merge_dicts(
            self.port_field_terms, rhs.port_field_terms, _substract_terms, 0
        )
        self.port_field_terms = aggregated_port_terms

        self.remove_zeros_from_terms()
        return self

    def __sub__(
        self, rhs: Union["LinearExpressionEfficient", int, float]
    ) -> "LinearExpressionEfficient":
        result = LinearExpressionEfficient()
        result += self
        result -= rhs
        return result

    def __rsub__(self, rhs: int) -> "LinearExpressionEfficient":
        return -self + rhs

    def __neg__(self) -> "LinearExpressionEfficient":
        result = LinearExpressionEfficient()
        result -= self
        return result

    def __imul__(
        self, rhs: Union["LinearExpressionEfficient", int, float]
    ) -> "LinearExpressionEfficient":
        rhs = wrap_in_linear_expr(rhs)

        if not (self.is_constant() or rhs.is_constant()):
            raise ValueError("Cannot multiply two non constant expression")
        else:
            if rhs.is_constant():
                left_expr = self
                const_expr = rhs
            else:  # self is constant
                left_expr = rhs
                const_expr = self
            if is_zero(const_expr.constant):
                return LinearExpressionEfficient()
            elif is_one(const_expr.constant):
                _copy_expression(left_expr, self)
            else:
                left_expr.constant *= const_expr.constant
                for term_key, term in left_expr.terms.items():
                    left_expr.terms[term_key] = dataclasses.replace(
                        term, coefficient=term.coefficient * const_expr.constant
                    )
                for port_term_key, port_term in left_expr.port_field_terms.items():
                    left_expr.port_field_terms[port_term_key] = dataclasses.replace(
                        port_term,
                        coefficient=port_term.coefficient * const_expr.constant,
                    )
                _copy_expression(left_expr, self)
        return self

    def __mul__(
        self, rhs: Union["LinearExpressionEfficient", int, float]
    ) -> "LinearExpressionEfficient":
        result = LinearExpressionEfficient()
        result += self
        result *= rhs
        return result

    def __rmul__(self, rhs: int) -> "LinearExpressionEfficient":
        return self.__mul__(rhs)

    def __itruediv__(
        self, rhs: Union["LinearExpressionEfficient", int, float]
    ) -> "LinearExpressionEfficient":
        rhs = wrap_in_linear_expr(rhs)

        if not rhs.is_constant():
            raise ValueError("Cannot divide by a non constant expression")
        else:
            if is_zero(rhs.constant):
                raise ZeroDivisionError("Cannot divide expression by zero")
            elif is_one(rhs.constant):
                return self
            else:
                self.constant /= rhs.constant
                for term_key, term in self.terms.items():
                    self.terms[term_key] = dataclasses.replace(
                        term, coefficient=term.coefficient / rhs.constant
                    )
                for port_term_key, port_term in self.port_field_terms.items():
                    self.port_field_terms[port_term_key] = dataclasses.replace(
                        port_term, coefficient=port_term.coefficient / rhs.constant
                    )
        return self

    def __truediv__(
        self, rhs: Union["LinearExpressionEfficient", int, float]
    ) -> "LinearExpressionEfficient":
        result = LinearExpressionEfficient()
        result += self
        result /= rhs

        return result

    def __rtruediv__(self, rhs: Union[int, float]) -> "LinearExpressionEfficient":
        return self.__truediv__(rhs)

    def remove_zeros_from_terms(self) -> None:
        # TODO: Not optimized, checks could be done directly when doing operations on self.linear_term to avoid copies
        for term_key, term in self.terms.copy().items():
            if is_zero(term.coefficient):
                del self.terms[term_key]
        for port_term_key, port_term in self.port_field_terms.copy().items():
            if is_zero(port_term.coefficient):
                del self.port_field_terms[port_term_key]

    def evaluate(self, context: ValueProvider, time_scenario_index: RowIndex) -> float:
        return sum(
            [
                term.evaluate(context, time_scenario_index)
                for term in self.terms.values()
            ]
        ) + resolve_coefficient(self.constant, context, time_scenario_index)

    def is_constant(self) -> bool:
        # Constant expr like x-x could be seen as non constant as we do not simplify coefficient tree...
        return not self.terms and not self.port_field_terms

    def is_unbound(self) -> bool:
        return is_unbound(self.constant)

    def compute_indexation(
        self, provider: IndexingStructureProvider
    ) -> IndexingStructure:
        """
        Computes the (time, scenario) indexing of a linear expression.

        Time and scenario indexation is driven by the indexation of variables in the expression. If a single term is indexed by time (resp. scenario), then the linear expression is indexed by time (resp. scenario).
        """
        indexing = IndexingStructure(False, False)
        for term in self.terms.values():
            indexing = indexing | term.compute_indexation(provider)

        return indexing

    def sum(
        self,
        shift: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
            None,
        ] = None,
        eval: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
            None,
        ] = None,
    ) -> "LinearExpressionEfficient":
        """
        Examples:
            >>> x.sum(shift=[1, 2, 4]) represents x[t+1] + x[t+2] + x[t+4]

        No variables allowed in shift argument, but parameter trees are ok

        It is assumed that the shift operator is linear and distributes to all terms and to the constant of the linear expression on which it is applied.

        Examples:
            >>> (param("a") * var("x") + param("b")).sum(shift=[1, 2, 4]) represents a[t+1]x[t+1] + b[t+1] + a[t+2]x[t+2] + b[t+2] + a[t+4]x[t+4] + b[t+4]
        """

        if shift is not None and eval is not None:
            raise ValueError("Only shift or eval arguments should specified, not both.")

        if shift is not None:
            sum_args = {"shift": shift}

            result_constant = TimeAggregatorNode(
                TimeOperatorNode(
                    self.constant,
                    TimeOperatorName.SHIFT,
                    InstancesTimeIndex(shift),
                ),
                TimeAggregatorName.TIME_SUM,
                stay_roll=True,
            )
        elif eval is not None:
            sum_args = {"eval": eval}

            result_constant = TimeAggregatorNode(
                TimeOperatorNode(
                    self.constant,
                    TimeOperatorName.EVALUATION,
                    InstancesTimeIndex(eval),
                ),
                TimeAggregatorName.TIME_SUM,
                stay_roll=True,
            )
        else:  # x.sum() -> Sum over all time block
            sum_args = {}

            result_constant = TimeAggregatorNode(
                self.constant,
                TimeAggregatorName.TIME_SUM,
                stay_roll=False,
            )

        return LinearExpressionEfficient(
            self._apply_operator(sum_args), result_constant
        )

    def _apply_operator(
        self,
        sum_args: Dict[
            str,
            Union[
                int,
                "ExpressionNodeEfficient",
                List["ExpressionNodeEfficient"],
                "ExpressionRange",
                None,
            ],
        ],
    ) -> Dict[TermKeyEfficient, TermEfficient]:
        result_terms = {}
        for term in self.terms.values():
            term_with_operator = term.sum(**sum_args)
            result_terms[generate_key(term_with_operator)] = term_with_operator

        return result_terms

    # def sum_connections(self) -> "ExpressionNode":
    #     if isinstance(self, PortFieldNode):
    #         return PortFieldAggregatorNode(self, aggregator=PortFieldAggregatorName.PORT_SUM)
    #     raise ValueError(
    #         f"sum_connections() applies only for PortFieldNode, whereas the current node is of type {type(self)}."
    #     )

    def shift(
        self,
        expressions: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
        ],
    ) -> "LinearExpressionEfficient":
        """
        Shorthand for shift on a single time step

        To refer to x[t-1], it is more natural to write x.shift(-1) than x.sum(shift=-1).

        This function provides the shorthand x.sum(shift=expr), valid only in the case when expr refers to a single time step.

        """

        if not InstancesTimeIndex(expressions).is_simple():
            raise ValueError(
                "The shift operator can only be applied on expressions refering to a single time step. To apply a shifting sum on multiple time indices on an expression x, you should use x.sum(shift=...)"
            )

        else:
            return self.sum(shift=expressions)

    def eval(
        self,
        expressions: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
        ],
    ) -> "LinearExpressionEfficient":
        """
        Shorthand for eval on a single time step

        To refer to x[1], it is more natural to write x.eval(1) than x.sum(eval=1).

        This function provides the shorthand x.sum(eval=expr), valid only in the case when expr refers to a single time step.

        """

        if not InstancesTimeIndex(expressions).is_simple():
            raise ValueError(
                "The eval operator can only be applied on expressions refering to a single time step. To apply a evaluation sum on multiple time indices on an expression x, you should use x.sum(eval=...)"
            )

        else:
            return self.sum(eval=expressions)

    def expec(self) -> "LinearExpressionEfficient":
        """
        Expectation of linear expression. As the operator is linear, it distributes over all terms and the constant
        """

        result_terms = {}
        for term in self.terms.values():
            term_with_operator = term.expec()
            result_terms[generate_key(term_with_operator)] = term_with_operator

        result_constant = ScenarioOperatorNode(
            self.constant, ScenarioOperatorName.EXPECTATION
        )
        result_expr = LinearExpressionEfficient(result_terms, result_constant)
        return result_expr

    # def variance(self) -> "ExpressionNode":
    #     return _apply_if_node(self, lambda x: ScenarioOperatorNode(x, ScenarioOperatorName.Variance))

    def sum_connections(self) -> "LinearExpressionEfficient":
        if not self.is_zero():
            raise ValueError(
                "sum_connections only after an expression created with port_field"
            )
        port_field_terms = {}
        for port_field_key, port_field_value in self.port_field_terms.items():
            port_field_terms[port_field_key] = port_field_value.sum_connections()
        return LinearExpressionEfficient(port_field_terms=port_field_terms)

    def resolve_port(
        self,
        component_id: str,
        ports_expressions: Dict[PortFieldKey, List["LinearExpressionEfficient"]],
    ) -> "LinearExpressionEfficient":
        port_expr = LinearExpressionEfficient()
        for port_term in self.port_field_terms.values():
            expressions = ports_expressions.get(
                PortFieldKey(
                    component_id,
                    PortFieldId(port_term.port_name, port_term.field_name),
                ),
                [],
            )
            if port_term.aggregator is None:
                if len(expressions) != 1:
                    raise ValueError(
                        f"Invalid number of expression for port : {port_term.port_name}"
                    )
            else:
                if port_term.aggregator != PortSum():
                    raise NotImplementedError("Only PortSum is supported.")

            port_expr += sum_expressions(
                [port_term.coefficient * expression for expression in expressions]
            )
        return self + port_expr

    def add_component_context(self, component_id: str) -> "LinearExpressionEfficient":
        result_terms = {}
        for term in self.terms.values():
            if term.component_id:
                raise ValueError(
                    "This expression has already been associated to another component."
                )

            result_term = dataclasses.replace(
                term,
                component_id=component_id,
                coefficient=add_component_context(component_id, term.coefficient),
                time_operator=(
                    dataclasses.replace(
                        term.time_operator,
                        time_ids=_add_component_context_to_instances_index(
                            component_id, term.time_operator.time_ids
                        ),
                    )
                    if term.time_operator
                    else None
                ),
            )
            result_terms[generate_key(result_term)] = result_term
        result_constant = add_component_context(component_id, self.constant)
        return LinearExpressionEfficient(
            result_terms, result_constant, self.port_field_terms
        )


def _add_component_context_to_expression_range(
    component_id: str, expression_range: ExpressionRange
) -> ExpressionRange:
    return ExpressionRange(
        start=add_component_context(component_id, expression_range.start),
        stop=add_component_context(component_id, expression_range.stop),
        step=(
            add_component_context(component_id, expression_range.step)
            if expression_range.step is not None
            else None
        ),
    )


def _add_component_context_to_instances_index(
    component_id: str, instances_index: InstancesTimeIndex
) -> InstancesTimeIndex:
    expressions = instances_index.expressions
    if isinstance(expressions, ExpressionRange):
        return InstancesTimeIndex(
            _add_component_context_to_expression_range(component_id, expressions)
        )
    if isinstance(expressions, list):
        expressions_list = cast(List[ExpressionNodeEfficient], expressions)
        copy = [add_component_context(component_id, e) for e in expressions_list]
        return InstancesTimeIndex(copy)
    raise ValueError("Unexpected type in instances index")


def linear_expressions_equal(
    lhs: LinearExpressionEfficient, rhs: LinearExpressionEfficient
) -> bool:
    return (
        isinstance(lhs, LinearExpressionEfficient)
        and isinstance(rhs, LinearExpressionEfficient)
        and expressions_equal(lhs.constant, rhs.constant)
        and lhs.terms == rhs.terms
    )


# TODO: Is this function useful ? Could we just rely on the sum operator overloading ? Only the case with an empty list may make the function useful
def sum_expressions(
    expressions: Sequence[LinearExpressionEfficient],
) -> LinearExpressionEfficient:
    if len(expressions) == 0:
        return wrap_in_linear_expr(literal(0))
    else:
        return sum(expressions)


@dataclass
class StandaloneConstraint:
    """
    A standalone constraint, with rigid initialization.
    """

    expression: LinearExpressionEfficient
    lower_bound: LinearExpressionEfficient
    upper_bound: LinearExpressionEfficient

    def __post_init__(
        self,
    ) -> None:
        for bound in [self.lower_bound, self.upper_bound]:
            if not bound.is_constant():
                raise ValueError(
                    f"The bounds of a constraint should not contain variables, {print_expr(bound)} was given."
                )

    def __str__(self) -> str:
        return f"{str(self.lower_bound)} <= {str(self.expression)} <= {str(self.upper_bound)}"


def wrap_in_linear_expr(obj: Any) -> LinearExpressionEfficient:
    if isinstance(obj, LinearExpressionEfficient):
        return obj
    elif isinstance(obj, float) or isinstance(obj, int):
        return LinearExpressionEfficient([], LiteralNode(float(obj)))
    elif isinstance(obj, ExpressionNodeEfficient):
        return LinearExpressionEfficient([], obj)
    raise TypeError(f"Unable to wrap {obj} into a linear expression")


def wrap_in_linear_expr_if_present(obj: Any) -> Union[None, LinearExpressionEfficient]:
    if obj is None:
        return None
    else:
        return wrap_in_linear_expr(obj)


def _copy_expression(
    src: LinearExpressionEfficient, dst: LinearExpressionEfficient
) -> None:
    dst.terms = src.terms
    dst.constant = src.constant


# TODO : Define shortcuts for "x", is_one etc ....
def var(name: str) -> LinearExpressionEfficient:
    return LinearExpressionEfficient(
        [
            TermEfficient(
                coefficient=LiteralNode(1), component_id="", variable_name=name
            )
        ],
        LiteralNode(0),
    )


def comp_var(component_id: str, name: str) -> LinearExpressionEfficient:
    return LinearExpressionEfficient(
        [
            TermEfficient(
                coefficient=LiteralNode(1),
                component_id=component_id,
                variable_name=name,
            )
        ],
        LiteralNode(0),
    )


def port_field(port_name: str, field_name: str) -> LinearExpressionEfficient:
    return LinearExpressionEfficient(
        port_field_terms=[PortFieldTerm(literal(1), port_name, field_name)]
    )


def is_linear(expr: LinearExpressionEfficient) -> bool:
    return True
